from __future__ import annotations

import collections
import configparser
import contextlib
import dataclasses
import difflib
import enum
import functools
import shlex
import textwrap
from collections.abc import Generator, Iterable, Set
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence, Union  # noqa: TID251

from packaging.specifiers import SpecifierSet

from . import errors
from ._compat import tomllib
from ._compat.typing import assert_never
from .architecture import Architecture
from .environment import EnvironmentParseError, ParsedEnvironment, parse_environment
from .logger import log
from .oci_container import OCIContainerEngineConfig
from .projectfiles import get_requires_python_str, resolve_dependency_groups
from .typing import PLATFORMS, PlatformName
from .util import (
    MANYLINUX_ARCHS,
    MUSLLINUX_ARCHS,
    BuildFrontendConfig,
    BuildSelector,
    DependencyConstraints,
    EnableGroups,
    TestSelector,
    format_safe,
    read_python_configs,
    resources_dir,
    selector_matches,
    strtobool,
    unwrap,
)


@dataclasses.dataclass
class CommandLineArguments:
    platform: Literal["auto", "linux", "macos", "windows"] | None
    archs: str | None
    output_dir: Path
    only: str | None
    config_file: str
    package_dir: Path
    print_build_identifiers: bool
    allow_empty: bool
    prerelease_pythons: bool
    debug_traceback: bool

    @staticmethod
    def defaults() -> CommandLineArguments:
        return CommandLineArguments(
            platform="auto",
            allow_empty=False,
            archs=None,
            only=None,
            config_file="",
            output_dir=Path("wheelhouse"),
            package_dir=Path("."),
            prerelease_pythons=False,
            print_build_identifiers=False,
            debug_traceback=False,
        )


@dataclasses.dataclass(frozen=True)
class GlobalOptions:
    package_dir: Path
    output_dir: Path
    build_selector: BuildSelector
    test_selector: TestSelector
    architectures: set[Architecture]
    allow_empty: bool


@dataclasses.dataclass(frozen=True)
class BuildOptions:
    globals: GlobalOptions
    environment: ParsedEnvironment
    before_all: str
    before_build: str | None
    repair_command: str
    manylinux_images: dict[str, str] | None
    musllinux_images: dict[str, str] | None
    dependency_constraints: DependencyConstraints | None
    test_command: str | None
    before_test: str | None
    test_requires: list[str]
    test_extras: str
    test_groups: list[str]
    build_verbosity: int
    build_frontend: BuildFrontendConfig | None
    config_settings: str
    container_engine: OCIContainerEngineConfig

    @property
    def package_dir(self) -> Path:
        return self.globals.package_dir

    @property
    def output_dir(self) -> Path:
        return self.globals.output_dir

    @property
    def build_selector(self) -> BuildSelector:
        return self.globals.build_selector

    @property
    def test_selector(self) -> TestSelector:
        return self.globals.test_selector

    @property
    def architectures(self) -> set[Architecture]:
        return self.globals.architectures


SettingLeaf = Union[str, int, bool]
SettingList = Sequence[SettingLeaf]
SettingTable = Mapping[str, Union[SettingLeaf, SettingList]]
SettingValue = Union[SettingTable, SettingList, SettingLeaf]


@dataclasses.dataclass(frozen=True)
class Override:
    select_pattern: str
    options: dict[str, SettingValue]
    inherit: dict[str, InheritRule]


MANYLINUX_OPTIONS = {f"manylinux-{build_platform}-image" for build_platform in MANYLINUX_ARCHS}
MUSLLINUX_OPTIONS = {f"musllinux-{build_platform}-image" for build_platform in MUSLLINUX_ARCHS}
DISALLOWED_OPTIONS = {
    "linux": {"dependency-versions"},
    "macos": MANYLINUX_OPTIONS | MUSLLINUX_OPTIONS,
    "windows": MANYLINUX_OPTIONS | MUSLLINUX_OPTIONS,
}


class OptionsReaderError(errors.ConfigurationError):
    pass


class OptionFormat:
    """
    Base class for option format specifiers. These objects describe how values
    can be parsed from rich TOML values and how they're merged together.
    """

    class NotSupported(Exception):
        pass

    def format_list(self, value: SettingList) -> str:  # noqa: ARG002
        raise OptionFormat.NotSupported

    def format_table(self, table: SettingTable) -> str:  # noqa: ARG002
        raise OptionFormat.NotSupported

    def merge_values(self, before: str, after: str) -> str:  # noqa: ARG002
        raise OptionFormat.NotSupported


class ListFormat(OptionFormat):
    """
    A format that joins lists with a separator.
    """

    def __init__(self, sep: str) -> None:
        self.sep = sep

    def format_list(self, value: SettingList) -> str:
        return self.sep.join(str(v) for v in value)

    def merge_values(self, before: str, after: str) -> str:
        return f"{before}{self.sep}{after}"


class ShlexTableFormat(OptionFormat):
    """
    The standard table format uses shlex.quote to quote values and shlex.split
    to unquote and split them. When merging values, keys in before are
    replaced by keys in after.
    """

    def __init__(self, sep: str = " ", pair_sep: str = "=", allow_merge: bool = True) -> None:
        self.sep = sep
        self.pair_sep = pair_sep
        self.allow_merge = allow_merge

    def format_table(self, table: SettingTable) -> str:
        assignments: list[tuple[str, str]] = []

        for k, v in table.items():
            if shlex.split(k) != [k]:
                msg = f"Invalid table key: {k}"
                raise OptionsReaderError(msg)

            if isinstance(v, str):
                assignments.append((k, v))
            elif isinstance(v, Sequence):
                for inner_v in v:
                    assignments.append((k, str(inner_v)))
            else:
                assignments.append((k, str(v)))

        return self.sep.join(f"{k}{self.pair_sep}{shlex.quote(v)}" for k, v in assignments)

    def merge_values(self, before: str, after: str) -> str:
        if not self.allow_merge:
            raise OptionFormat.NotSupported

        before_dict = self.parse_table(before)
        after_dict = self.parse_table(after)

        return self.format_table({**before_dict, **after_dict})

    def parse_table(self, table: str) -> Mapping[str, str | Sequence[str]]:
        assignments: list[tuple[str, str]] = []

        for assignment_str in shlex.split(table):
            key, sep, value = assignment_str.partition(self.pair_sep)

            if not sep:
                msg = f"malformed option with value {assignment_str!r}"
                raise OptionsReaderError(msg)

            assignments.append((key, value))

        result: dict[str, str | list[str]] = {}

        for key, value in assignments:
            if key in result:
                existing_value = result[key]
                if isinstance(existing_value, list):
                    result[key] = [*existing_value, value]
                else:
                    result[key] = [existing_value, value]
            else:
                result[key] = value

        return result


class EnvironmentFormat(OptionFormat):
    """
    The environment format accepts a table of environment variables, where the
    values may contain variables or command substitutions.
    """

    def format_table(self, table: SettingTable) -> str:
        return " ".join(f'{k}="{v}"' for k, v in table.items())

    def merge_values(self, before: str, after: str) -> str:
        return f"{before} {after}"


class InheritRule(enum.Enum):
    NONE = enum.auto()
    APPEND = enum.auto()
    PREPEND = enum.auto()


def _resolve_cascade(
    *pairs: tuple[SettingValue | None, InheritRule],
    ignore_empty: bool = False,
    option_format: OptionFormat | None = None,
) -> str:
    """
    Given a cascade of values with inherit rules, resolve them into a single
    value.

    'None' values mean that the option was not set at that level, and are
    ignored. If `ignore_empty` is True, empty values are ignored too.

    Values start with defaults, followed by more specific rules. If rules are
    NONE, the last non-null value is returned. If a rule is APPEND or PREPEND,
    the value is concatenated with the previous value.

    The following idiom can be used to get the first matching value:

        _resolve_cascade(("value1", Inherit.NONE), ("value2", Inherit.NONE), ...)))
    """
    if not pairs:
        msg = "pairs cannot be empty"
        raise ValueError(msg)

    result: str | None = None

    for value, rule in pairs:
        if value is None:
            continue

        if ignore_empty and not value and value is not False:
            continue

        value_string = _stringify_setting(value, option_format=option_format)

        result = _apply_inherit_rule(result, value_string, rule=rule, option_format=option_format)

    if result is None:
        msg = "a setting should at least have a default value"
        raise ValueError(msg)

    return result


def _apply_inherit_rule(
    before: str | None, after: str, rule: InheritRule, option_format: OptionFormat | None
) -> str:
    if rule == InheritRule.NONE:
        return after

    if not before:
        # if before is None, we can just return after
        # if before is an empty string, we shouldn't add any separator
        return after

    if not after:
        # if after is an empty string, we shouldn't add any separator
        return before

    if not option_format:
        msg = f"Don't know how to merge {before!r} and {after!r} with {rule}"
        raise OptionsReaderError(msg)

    if rule == InheritRule.APPEND:
        return option_format.merge_values(before, after)
    if rule == InheritRule.PREPEND:
        return option_format.merge_values(after, before)

    assert_never(rule)


def _stringify_setting(
    setting: SettingValue,
    option_format: OptionFormat | None,
) -> str:
    if isinstance(setting, Mapping):
        try:
            if option_format is None:
                raise OptionFormat.NotSupported
            return option_format.format_table(setting)
        except OptionFormat.NotSupported:
            msg = f"Error converting {setting!r} to a string: this setting doesn't accept a table"
            raise OptionsReaderError(msg) from None

    if not isinstance(setting, str) and isinstance(setting, Sequence):
        try:
            if option_format is None:
                raise OptionFormat.NotSupported
            return option_format.format_list(setting)
        except OptionFormat.NotSupported:
            msg = f"Error converting {setting!r} to a string: this setting doesn't accept a list"
            raise OptionsReaderError(msg) from None

    if isinstance(setting, (bool, int)):
        return str(setting)

    return setting


class OptionsReader:
    """
    Gets options from the environment, config or defaults, optionally scoped
    by the platform.

    Example:
      >>> options_reader = OptionsReader(config_file, platform='macos')
      >>> options_reader.get('cool-color')

      This will return the value of CIBW_COOL_COLOR_MACOS if it exists,
      otherwise the value of CIBW_COOL_COLOR, otherwise
      'tool.cibuildwheel.macos.cool-color' or 'tool.cibuildwheel.cool-color'
      from `config_file`, or from cibuildwheel/resources/defaults.toml. An
      error is thrown if there are any unexpected keys or sections in
      tool.cibuildwheel.
    """

    def __init__(
        self,
        config_file_path: Path | None = None,
        *,
        platform: PlatformName,
        env: Mapping[str, str],
        disallow: Mapping[str, Set[str]] | None = None,
    ) -> None:
        self.platform = platform
        self.env = env
        self.disallow = disallow or {}

        # Open defaults.toml, loading both global and platform sections
        defaults_path = resources_dir / "defaults.toml"
        self.default_options, self.default_platform_options = self._load_file(defaults_path)

        # Load the project config file
        config_options: dict[str, Any] = {}
        config_platform_options: dict[str, Any] = {}

        if config_file_path is not None:
            config_options, config_platform_options = self._load_file(config_file_path)

        # Validate project config
        for option_name in config_options:
            self._validate_global_option(option_name)

        for option_name in config_platform_options:
            self._validate_platform_option(option_name)

        self.config_options = config_options
        self.config_platform_options = config_platform_options

        self.overrides: list[Override] = []
        self.current_identifier: str | None = None

        config_overrides = self.config_options.get("overrides")

        if config_overrides is not None:
            if not isinstance(config_overrides, list):
                msg = "'tool.cibuildwheel.overrides' must be a list"
                raise OptionsReaderError(msg)

            for config_override in config_overrides:
                select = config_override.pop("select", None)

                if not select:
                    msg = "'select' must be set in an override"
                    raise OptionsReaderError(msg)

                if isinstance(select, list):
                    select = " ".join(select)

                inherit = config_override.pop("inherit", {})
                if not isinstance(inherit, dict) or not all(
                    i in {"none", "append", "prepend"} for i in inherit.values()
                ):
                    msg = "'inherit' must be a dict containing only {'none', 'append', 'prepend'} values"
                    raise OptionsReaderError(msg)

                inherit_enum = {k: InheritRule[v.upper()] for k, v in inherit.items()}

                self.overrides.append(Override(select, config_override, inherit_enum))

    def _validate_global_option(self, name: str) -> None:
        """
        Raises an error if an option with this name is not allowed in the
        [tool.cibuildwheel] section of a config file.
        """
        allowed_option_names = self.default_options.keys() | PLATFORMS | {"overrides"}

        if name not in allowed_option_names:
            msg = f"Option {name!r} not supported in a config file."
            matches = difflib.get_close_matches(name, allowed_option_names, 1, 0.7)
            if matches:
                msg += f" Perhaps you meant {matches[0]!r}?"
            raise OptionsReaderError(msg)

    def _validate_platform_option(self, name: str) -> None:
        """
        Raises an error if an option with this name is not allowed in the
        [tool.cibuildwheel.<current-platform>] section of a config file.
        """
        disallowed_platform_options = self.disallow.get(self.platform, set())
        if name in disallowed_platform_options:
            msg = f"{name!r} is not allowed in {disallowed_platform_options}"
            raise OptionsReaderError(msg)

        allowed_option_names = self.default_options.keys() | self.default_platform_options.keys()

        if name not in allowed_option_names:
            msg = f"Option {name!r} not supported in the {self.platform!r} section"
            matches = difflib.get_close_matches(name, allowed_option_names, 1, 0.7)
            if matches:
                msg += f" Perhaps you meant {matches[0]!r}?"
            raise OptionsReaderError(msg)

    def _load_file(self, filename: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Load a toml file, returns global and platform as separate dicts.
        """
        with filename.open("rb") as f:
            config = tomllib.load(f)

        global_options = config.get("tool", {}).get("cibuildwheel", {})
        platform_options = global_options.get(self.platform, {})

        return global_options, platform_options

    @property
    def active_config_overrides(self) -> list[Override]:
        if self.current_identifier is None:
            return []
        return [
            o for o in self.overrides if selector_matches(o.select_pattern, self.current_identifier)
        ]

    @contextlib.contextmanager
    def identifier(self, identifier: str | None) -> Generator[None, None, None]:
        self.current_identifier = identifier
        try:
            yield
        finally:
            self.current_identifier = None

    def get(
        self,
        name: str,
        *,
        env_plat: bool = True,
        option_format: OptionFormat | None = None,
        ignore_empty: bool = False,
        env_rule: InheritRule = InheritRule.NONE,
    ) -> str:
        """
        Get and return the value for the named option from environment,
        configuration file, or the default. If env_plat is False, then don't
        accept platform versions of the environment variable. If this is an
        array it will be merged with "sep" before returning. If it is a table,
        it will be formatted with "table['item']" using {k} and {v} and merged
        with "table['sep']". If sep is also given, it will be used for arrays
        inside the table (must match table['sep']). Empty variables will not
        override if ignore_empty is True.
        """

        if name not in self.default_options and name not in self.default_platform_options:
            msg = f"{name!r} must be in cibuildwheel/resources/defaults.toml file to be accessed."
            raise OptionsReaderError(msg)

        # Environment variable form
        envvar = f"CIBW_{name.upper().replace('-', '_')}"
        plat_envvar = f"{envvar}_{self.platform.upper()}"

        # get the option from the default, then the config file, then finally the environment.
        # platform-specific options are preferred, if they're allowed.
        return _resolve_cascade(
            (self.default_options.get(name), InheritRule.NONE),
            (self.default_platform_options.get(name), InheritRule.NONE),
            (self.config_options.get(name), InheritRule.NONE),
            (self.config_platform_options.get(name), InheritRule.NONE),
            *[
                (o.options.get(name), o.inherit.get(name, InheritRule.NONE))
                for o in self.active_config_overrides
            ],
            (self.env.get(envvar), env_rule),
            (self.env.get(plat_envvar) if env_plat else None, env_rule),
            ignore_empty=ignore_empty,
            option_format=option_format,
        )


class Options:
    pyproject_toml: dict[str, Any] | None

    def __init__(
        self,
        platform: PlatformName,
        command_line_arguments: CommandLineArguments,
        env: Mapping[str, str],
        defaults: bool = False,
    ):
        self.platform = platform
        self.command_line_arguments = command_line_arguments
        self.env = env
        self._defaults = defaults

        self.reader = OptionsReader(
            None if defaults else self.config_file_path,
            platform=platform,
            env=env,
            disallow=DISALLOWED_OPTIONS,
        )

        self.package_dir = Path(command_line_arguments.package_dir)
        try:
            with self.package_dir.joinpath("pyproject.toml").open("rb") as f:
                self.pyproject_toml = tomllib.load(f)
        except FileNotFoundError:
            self.pyproject_toml = None

    @functools.cached_property
    def config_file_path(self) -> Path | None:
        args = self.command_line_arguments

        if args.config_file:
            return Path(format_safe(args.config_file, package=args.package_dir))

        # return pyproject.toml, if it's available
        pyproject_toml_path = Path(args.package_dir) / "pyproject.toml"
        if pyproject_toml_path.exists():
            return pyproject_toml_path

        return None

    @functools.cached_property
    def package_requires_python_str(self) -> str | None:
        return get_requires_python_str(self.package_dir, self.pyproject_toml)

    @functools.cached_property
    def globals(self) -> GlobalOptions:
        args = self.command_line_arguments
        package_dir = args.package_dir
        output_dir = args.output_dir

        build_config = (
            self.reader.get("build", env_plat=False, option_format=ListFormat(sep=" ")) or "*"
        )
        skip_config = self.reader.get("skip", env_plat=False, option_format=ListFormat(sep=" "))
        test_skip = self.reader.get("test-skip", env_plat=False, option_format=ListFormat(sep=" "))

        allow_empty = args.allow_empty or strtobool(self.env.get("CIBW_ALLOW_EMPTY", "0"))

        enable_groups = self.reader.get(
            "enable", env_plat=False, option_format=ListFormat(sep=" "), env_rule=InheritRule.APPEND
        )
        enable = {EnableGroups(group) for group in enable_groups.split()}

        free_threaded_support = strtobool(
            self.reader.get("free-threaded-support", env_plat=False, ignore_empty=True)
        )

        prerelease_pythons = args.prerelease_pythons or strtobool(
            self.env.get("CIBW_PRERELEASE_PYTHONS", "0")
        )

        if free_threaded_support or prerelease_pythons:
            msg = (
                "free-threaded-support and prerelease-pythons should be specified by enable instead"
            )
            if enable:
                raise OptionsReaderError(msg)
            log.warning(msg)

        if free_threaded_support:
            enable.add(EnableGroups.CPythonFreeThreading)
        if prerelease_pythons:
            enable.add(EnableGroups.CPythonPrerelease)

        # This is not supported in tool.cibuildwheel, as it comes from a standard location.
        # Passing this in as an environment variable will override pyproject.toml, setup.cfg, or setup.py
        requires_python_str: str | None = (
            self.env.get("CIBW_PROJECT_REQUIRES_PYTHON") or self.package_requires_python_str
        )
        requires_python = None if requires_python_str is None else SpecifierSet(requires_python_str)

        archs_config_str = args.archs or self.reader.get("archs", option_format=ListFormat(sep=" "))
        architectures = Architecture.parse_config(archs_config_str, platform=self.platform)

        # Process `--only`
        if args.only:
            build_config = args.only
            skip_config = ""
            architectures = Architecture.all_archs(self.platform)
            enable = set(EnableGroups)

        build_selector = BuildSelector(
            build_config=build_config,
            skip_config=skip_config,
            requires_python=requires_python,
            enable=frozenset(
                enable | {EnableGroups.PyPy}
            ),  # For backwards compatibility, we are adding PyPy for now
        )
        test_selector = TestSelector(skip_config=test_skip)

        all_configs = read_python_configs(self.platform)
        all_pypy_ids = {
            config["identifier"] for config in all_configs if config["identifier"].startswith("pp")
        }
        if (
            not self._defaults
            and EnableGroups.PyPy not in enable
            and any(build_selector(build_id) for build_id in all_pypy_ids)
        ):
            msg = "PyPy builds will be disabled by default in version 3. Enabling PyPy builds should be specified by enable"
            log.warning(msg)

        return GlobalOptions(
            package_dir=package_dir,
            output_dir=output_dir,
            build_selector=build_selector,
            test_selector=test_selector,
            architectures=architectures,
            allow_empty=allow_empty,
        )

    def build_options(self, identifier: str | None) -> BuildOptions:
        """
        Compute BuildOptions for a single run configuration.
        """

        with self.reader.identifier(identifier):
            before_all = self.reader.get("before-all", option_format=ListFormat(sep=" && "))

            environment_config = self.reader.get("environment", option_format=EnvironmentFormat())
            environment_pass = self.reader.get(
                "environment-pass", option_format=ListFormat(sep=" ")
            ).split()
            before_build = self.reader.get("before-build", option_format=ListFormat(sep=" && "))
            repair_command = self.reader.get(
                "repair-wheel-command", option_format=ListFormat(sep=" && ")
            )
            config_settings = self.reader.get(
                "config-settings", option_format=ShlexTableFormat(sep=" ", pair_sep="=")
            )

            dependency_versions = self.reader.get("dependency-versions")
            test_command = self.reader.get("test-command", option_format=ListFormat(sep=" && "))
            before_test = self.reader.get("before-test", option_format=ListFormat(sep=" && "))
            test_requires = self.reader.get(
                "test-requires", option_format=ListFormat(sep=" ")
            ).split()
            test_extras = self.reader.get("test-extras", option_format=ListFormat(sep=","))
            test_groups_str = self.reader.get("test-groups", option_format=ListFormat(sep=" "))
            test_groups = [x for x in test_groups_str.split() if x]
            test_requirements_from_groups = resolve_dependency_groups(
                self.pyproject_toml, *test_groups
            )
            build_verbosity_str = self.reader.get("build-verbosity")

            build_frontend_str = self.reader.get(
                "build-frontend",
                env_plat=False,
                option_format=ShlexTableFormat(sep="; ", pair_sep=":", allow_merge=False),
            )
            build_frontend: BuildFrontendConfig | None
            if not build_frontend_str or build_frontend_str == "default":
                build_frontend = None
            else:
                try:
                    build_frontend = BuildFrontendConfig.from_config_string(build_frontend_str)
                except ValueError as e:
                    msg = f"Failed to parse build frontend. {e}"
                    raise errors.ConfigurationError(msg) from e

            try:
                environment = parse_environment(environment_config)
            except (EnvironmentParseError, ValueError) as e:
                msg = f"Malformed environment option {environment_config!r}"
                raise errors.ConfigurationError(msg) from e

            # Pass through environment variables
            if self.platform == "linux":
                for env_var_name in reversed(environment_pass):
                    with contextlib.suppress(KeyError):
                        environment.add(env_var_name, self.env[env_var_name], prepend=True)

            if dependency_versions == "pinned":
                dependency_constraints: None | (
                    DependencyConstraints
                ) = DependencyConstraints.with_defaults()
            elif dependency_versions == "latest":
                dependency_constraints = None
            else:
                dependency_versions_path = Path(dependency_versions)
                dependency_constraints = DependencyConstraints(dependency_versions_path)

            if test_extras:
                test_extras = f"[{test_extras}]"

            try:
                build_verbosity = min(3, max(-3, int(build_verbosity_str)))
            except ValueError:
                build_verbosity = 0

            manylinux_images: dict[str, str] = {}
            musllinux_images: dict[str, str] = {}
            container_engine: OCIContainerEngineConfig | None = None

            if self.platform == "linux":
                all_pinned_container_images = _get_pinned_container_images()

                for build_platform in MANYLINUX_ARCHS:
                    pinned_images = all_pinned_container_images[build_platform]

                    config_value = self.reader.get(
                        f"manylinux-{build_platform}-image", ignore_empty=True
                    )

                    if not config_value:
                        # default to manylinux2014
                        image = pinned_images["manylinux2014"]
                    elif config_value in pinned_images:
                        image = pinned_images[config_value]
                    else:
                        image = config_value

                    manylinux_images[build_platform] = image

                for build_platform in MUSLLINUX_ARCHS:
                    pinned_images = all_pinned_container_images[build_platform]

                    config_value = self.reader.get(f"musllinux-{build_platform}-image")

                    if not config_value:
                        image = pinned_images["musllinux_1_2"]
                    elif config_value in pinned_images:
                        image = pinned_images[config_value]
                    else:
                        image = config_value

                    musllinux_images[build_platform] = image

            container_engine_str = self.reader.get(
                "container-engine",
                option_format=ShlexTableFormat(sep="; ", pair_sep=":", allow_merge=False),
            )

            try:
                container_engine = OCIContainerEngineConfig.from_config_string(container_engine_str)
            except ValueError as e:
                msg = f"Failed to parse container config. {e}"
                raise errors.ConfigurationError(msg) from e

            return BuildOptions(
                globals=self.globals,
                test_command=test_command,
                test_requires=[*test_requires, *test_requirements_from_groups],
                test_extras=test_extras,
                test_groups=test_groups,
                before_test=before_test,
                before_build=before_build,
                before_all=before_all,
                build_verbosity=build_verbosity,
                repair_command=repair_command,
                environment=environment,
                dependency_constraints=dependency_constraints,
                manylinux_images=manylinux_images or None,
                musllinux_images=musllinux_images or None,
                build_frontend=build_frontend,
                config_settings=config_settings,
                container_engine=container_engine,
            )

    def check_for_invalid_configuration(self, identifiers: Iterable[str]) -> None:
        if self.platform in {"macos", "windows"}:
            before_all_values = {self.build_options(i).before_all for i in identifiers}

            if len(before_all_values) > 1:
                raise ValueError(
                    unwrap(
                        f"""
                        before_all cannot be set to multiple values. On macOS and Windows,
                        before_all is only run once, at the start of the build. before_all values
                        are: {before_all_values!r}
                        """
                    )
                )

    def check_for_deprecated_options(self) -> None:
        build_selector = self.globals.build_selector
        test_selector = self.globals.test_selector

        deprecated_selectors("CIBW_BUILD", build_selector.build_config, error=True)
        deprecated_selectors("CIBW_SKIP", build_selector.skip_config)
        deprecated_selectors("CIBW_TEST_SKIP", test_selector.skip_config)

    @functools.cached_property
    def defaults(self) -> Options:
        return Options(
            platform=self.platform,
            command_line_arguments=CommandLineArguments.defaults(),
            env={},
            defaults=True,
        )

    def summary(self, identifiers: Iterable[str]) -> str:
        lines = []
        global_option_names = sorted(f.name for f in dataclasses.fields(self.globals))

        for option_name in global_option_names:
            option_value = getattr(self.globals, option_name)
            default_value = getattr(self.defaults.globals, option_name)
            lines.append(self.option_summary(option_name, option_value, default_value))

        build_options = self.build_options(identifier=None)
        build_options_defaults = self.defaults.build_options(identifier=None)
        build_options_for_identifier = {
            identifier: self.build_options(identifier) for identifier in identifiers
        }

        build_option_names = sorted(f.name for f in dataclasses.fields(build_options))

        for option_name in build_option_names:
            if option_name == "globals":
                continue

            option_value = getattr(build_options, option_name)
            default_value = getattr(build_options_defaults, option_name)
            overrides = {
                i: getattr(build_options_for_identifier[i], option_name) for i in identifiers
            }

            lines.append(
                self.option_summary(option_name, option_value, default_value, overrides=overrides)
            )

        return "\n".join(lines)

    def option_summary(
        self,
        option_name: str,
        option_value: Any,
        default_value: Any,
        overrides: Mapping[str, Any] | None = None,
    ) -> str:
        """
        Return a summary of the option value, including any overrides, with
        ANSI 'dim' color if it's the default.
        """
        value_str = self.option_summary_value(option_value)
        default_value_str = self.option_summary_value(default_value)
        overrides_value_strs = {
            k: self.option_summary_value(v) for k, v in (overrides or {}).items()
        }
        # if the override value is the same as the non-overridden value, don't print it
        overrides_value_strs = {k: v for k, v in overrides_value_strs.items() if v != value_str}

        has_been_set = (value_str != default_value_str) or overrides_value_strs
        c = log.colors

        result = c.gray if not has_been_set else ""
        result += f"{option_name}: "

        if overrides_value_strs:
            overrides_groups = collections.defaultdict(list)
            for k, v in overrides_value_strs.items():
                overrides_groups[v].append(k)

            result += "\n  *: "
            result += self.indent_if_multiline(value_str, "    ")

            for override_value_str, identifiers in overrides_groups.items():
                result += f"\n  {', '.join(identifiers)}: "
                result += self.indent_if_multiline(override_value_str, "    ")
        else:
            result += self.indent_if_multiline(value_str, "  ")

        result += c.end

        return result

    def indent_if_multiline(self, value: str, indent: str) -> str:
        if "\n" in value:
            return "\n" + textwrap.indent(value.strip(), indent)
        else:
            return value

    def option_summary_value(self, option_value: Any) -> str:
        if hasattr(option_value, "options_summary"):
            option_value = option_value.options_summary()

        if isinstance(option_value, list):
            return "".join(f"{el}\n" for el in option_value)

        if isinstance(option_value, set):
            return ", ".join(str(el) for el in sorted(option_value))

        if isinstance(option_value, dict):
            return "".join(f"{k}: {v}\n" for k, v in option_value.items())

        return str(option_value)


def compute_options(
    platform: PlatformName,
    command_line_arguments: CommandLineArguments,
    env: Mapping[str, str],
) -> Options:
    options = Options(platform=platform, command_line_arguments=command_line_arguments, env=env)
    options.check_for_deprecated_options()
    return options


@functools.lru_cache(maxsize=None)
def _get_pinned_container_images() -> Mapping[str, Mapping[str, str]]:
    """
    This looks like a dict of dicts, e.g.
    { 'x86_64': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
      'i686': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
      'pypy_x86_64': {'manylinux2010': '...' }
      ... }
    """

    pinned_images_file = resources_dir / "pinned_docker_images.cfg"
    all_pinned_images = configparser.ConfigParser()
    all_pinned_images.read(pinned_images_file)
    return all_pinned_images


def deprecated_selectors(name: str, selector: str, *, error: bool = False) -> None:
    if "p2" in selector or "p35" in selector:
        msg = f"cibuildwheel 2.x no longer supports Python < 3.6. Please use the 1.x series or update {name}"
        if error:
            raise errors.DeprecationError(msg)
        log.warning(msg)
