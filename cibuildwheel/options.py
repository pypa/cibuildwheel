from __future__ import annotations

import difflib
import functools
import os
import shlex
import sys
import traceback
from configparser import ConfigParser
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterator, List, Mapping, Union, cast

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from packaging.specifiers import SpecifierSet

from .architecture import Architecture
from .environment import EnvironmentParseError, ParsedEnvironment, parse_environment
from .oci_container import ContainerEngine
from .projectfiles import get_requires_python_str
from .typing import PLATFORMS, Literal, NotRequired, PlatformName, TypedDict
from .util import (
    MANYLINUX_ARCHS,
    MUSLLINUX_ARCHS,
    BuildFrontend,
    BuildSelector,
    DependencyConstraints,
    TestSelector,
    cached_property,
    format_safe,
    resources_dir,
    selector_matches,
    strtobool,
    unwrap,
)


@dataclass
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


@dataclass(frozen=True)
class GlobalOptions:
    package_dir: Path
    output_dir: Path
    build_selector: BuildSelector
    test_selector: TestSelector
    architectures: set[Architecture]
    container_engine: ContainerEngine


@dataclass(frozen=True)
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
    build_verbosity: int
    build_frontend: BuildFrontend
    config_settings: str

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


Setting = Union[Dict[str, str], List[str], str, int]


@dataclass(frozen=True)
class Override:
    select_pattern: str
    options: dict[str, Setting]


MANYLINUX_OPTIONS = {f"manylinux-{build_platform}-image" for build_platform in MANYLINUX_ARCHS}
MUSLLINUX_OPTIONS = {f"musllinux-{build_platform}-image" for build_platform in MUSLLINUX_ARCHS}
DISALLOWED_OPTIONS = {
    "linux": {"dependency-versions"},
    "macos": MANYLINUX_OPTIONS | MUSLLINUX_OPTIONS,
    "windows": MANYLINUX_OPTIONS | MUSLLINUX_OPTIONS,
}


class TableFmt(TypedDict):
    item: str
    sep: str
    quote: NotRequired[Callable[[str], str]]


class ConfigOptionError(KeyError):
    pass


def _dig_first(*pairs: tuple[Mapping[str, Setting], str], ignore_empty: bool = False) -> Setting:
    """
    Return the first dict item that matches from pairs of dicts and keys.
    Will throw a KeyError if missing.

    _dig_first((dict1, "key1"), (dict2, "key2"), ...)
    """
    if not pairs:
        msg = "pairs cannot be empty"
        raise ValueError(msg)

    for dict_like, key in pairs:
        if key in dict_like:
            value = dict_like[key]

            if ignore_empty and value == "":
                continue

            return value

    last_key = pairs[-1][1]
    raise KeyError(last_key)


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
        disallow: dict[str, set[str]] | None = None,
    ) -> None:
        self.platform = platform
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
                raise ConfigOptionError(msg)

            for config_override in config_overrides:
                select = config_override.pop("select", None)

                if not select:
                    msg = "'select' must be set in an override"
                    raise ConfigOptionError(msg)

                if isinstance(select, list):
                    select = " ".join(select)

                self.overrides.append(Override(select, config_override))

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
            raise ConfigOptionError(msg)

    def _validate_platform_option(self, name: str) -> None:
        """
        Raises an error if an option with this name is not allowed in the
        [tool.cibuildwheel.<current-platform>] section of a config file.
        """
        disallowed_platform_options = self.disallow.get(self.platform, set())
        if name in disallowed_platform_options:
            msg = f"{name!r} is not allowed in {disallowed_platform_options}"
            raise ConfigOptionError(msg)

        allowed_option_names = self.default_options.keys() | self.default_platform_options.keys()

        if name not in allowed_option_names:
            msg = f"Option {name!r} not supported in the {self.platform!r} section"
            matches = difflib.get_close_matches(name, allowed_option_names, 1, 0.7)
            if matches:
                msg += f" Perhaps you meant {matches[0]!r}?"
            raise ConfigOptionError(msg)

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

    @contextmanager
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
        sep: str | None = None,
        table: TableFmt | None = None,
        ignore_empty: bool = False,
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
            raise ConfigOptionError(msg)

        # Environment variable form
        envvar = f"CIBW_{name.upper().replace('-', '_')}"
        plat_envvar = f"{envvar}_{self.platform.upper()}"

        # later overrides take precedence over earlier ones, so reverse the list
        active_config_overrides = reversed(self.active_config_overrides)

        # get the option from the environment, then the config file, then finally the default.
        # platform-specific options are preferred, if they're allowed.
        result = _dig_first(
            (os.environ if env_plat else {}, plat_envvar),  # type: ignore[arg-type]
            (os.environ, envvar),
            *[(o.options, name) for o in active_config_overrides],
            (self.config_platform_options, name),
            (self.config_options, name),
            (self.default_platform_options, name),
            (self.default_options, name),
            ignore_empty=ignore_empty,
        )

        if isinstance(result, dict):
            if table is None:
                msg = f"{name!r} does not accept a table"
                raise ConfigOptionError(msg)
            return table["sep"].join(
                item for k, v in result.items() for item in _inner_fmt(k, v, table)
            )

        if isinstance(result, list):
            if sep is None:
                msg = f"{name!r} does not accept a list"
                raise ConfigOptionError(msg)
            return sep.join(result)

        if isinstance(result, int):
            return str(result)

        return result


def _inner_fmt(k: str, v: Any, table: TableFmt) -> Iterator[str]:
    quote_function = table.get("quote", lambda a: a)

    if isinstance(v, list):
        for inner_v in v:
            qv = quote_function(inner_v)
            yield table["item"].format(k=k, v=qv)
    else:
        qv = quote_function(v)
        yield table["item"].format(k=k, v=qv)


class Options:
    def __init__(self, platform: PlatformName, command_line_arguments: CommandLineArguments):
        self.platform = platform
        self.command_line_arguments = command_line_arguments

        self.reader = OptionsReader(
            self.config_file_path,
            platform=platform,
            disallow=DISALLOWED_OPTIONS,
        )

    @property
    def config_file_path(self) -> Path | None:
        args = self.command_line_arguments

        if args.config_file:
            return Path(format_safe(args.config_file, package=args.package_dir))

        # return pyproject.toml, if it's available
        pyproject_toml_path = Path(args.package_dir) / "pyproject.toml"
        if pyproject_toml_path.exists():
            return pyproject_toml_path

        return None

    @cached_property
    def package_requires_python_str(self) -> str | None:
        args = self.command_line_arguments
        return get_requires_python_str(Path(args.package_dir))

    @property
    def globals(self) -> GlobalOptions:
        args = self.command_line_arguments
        package_dir = args.package_dir
        output_dir = args.output_dir

        build_config = self.reader.get("build", env_plat=False, sep=" ") or "*"
        skip_config = self.reader.get("skip", env_plat=False, sep=" ")
        test_skip = self.reader.get("test-skip", env_plat=False, sep=" ")

        prerelease_pythons = args.prerelease_pythons or strtobool(
            os.environ.get("CIBW_PRERELEASE_PYTHONS", "0")
        )

        # This is not supported in tool.cibuildwheel, as it comes from a standard location.
        # Passing this in as an environment variable will override pyproject.toml, setup.cfg, or setup.py
        requires_python_str: str | None = (
            os.environ.get("CIBW_PROJECT_REQUIRES_PYTHON") or self.package_requires_python_str
        )
        requires_python = None if requires_python_str is None else SpecifierSet(requires_python_str)

        archs_config_str = args.archs or self.reader.get("archs", sep=" ")
        architectures = Architecture.parse_config(archs_config_str, platform=self.platform)

        # Process `--only`
        if args.only:
            build_config = args.only
            skip_config = ""
            architectures = Architecture.all_archs(self.platform)

        build_selector = BuildSelector(
            build_config=build_config,
            skip_config=skip_config,
            requires_python=requires_python,
            prerelease_pythons=prerelease_pythons,
        )
        test_selector = TestSelector(skip_config=test_skip)

        container_engine_str = self.reader.get("container-engine")

        if container_engine_str not in ["docker", "podman"]:
            msg = f"cibuildwheel: Unrecognised container_engine {container_engine_str!r}, only 'docker' and 'podman' are supported"
            print(msg, file=sys.stderr)
            sys.exit(2)

        container_engine = cast(ContainerEngine, container_engine_str)

        return GlobalOptions(
            package_dir=package_dir,
            output_dir=output_dir,
            build_selector=build_selector,
            test_selector=test_selector,
            architectures=architectures,
            container_engine=container_engine,
        )

    def build_options(self, identifier: str | None) -> BuildOptions:
        """
        Compute BuildOptions for a single run configuration.
        """

        with self.reader.identifier(identifier):
            before_all = self.reader.get("before-all", sep=" && ")

            build_frontend_str = self.reader.get("build-frontend", env_plat=False)
            environment_config = self.reader.get(
                "environment", table={"item": '{k}="{v}"', "sep": " "}
            )
            environment_pass = self.reader.get("environment-pass", sep=" ").split()
            before_build = self.reader.get("before-build", sep=" && ")
            repair_command = self.reader.get("repair-wheel-command", sep=" && ")
            config_settings = self.reader.get(
                "config-settings", table={"item": "{k}={v}", "sep": " ", "quote": shlex.quote}
            )

            dependency_versions = self.reader.get("dependency-versions")
            test_command = self.reader.get("test-command", sep=" && ")
            before_test = self.reader.get("before-test", sep=" && ")
            test_requires = self.reader.get("test-requires", sep=" ").split()
            test_extras = self.reader.get("test-extras", sep=",")
            build_verbosity_str = self.reader.get("build-verbosity")

            build_frontend: BuildFrontend
            if build_frontend_str == "build":
                build_frontend = "build"
            elif build_frontend_str == "pip":
                build_frontend = "pip"
            else:
                msg = f"cibuildwheel: Unrecognised build frontend {build_frontend_str!r}, only 'pip' and 'build' are supported"
                print(msg, file=sys.stderr)
                sys.exit(2)

            try:
                environment = parse_environment(environment_config)
            except (EnvironmentParseError, ValueError):
                print(
                    f"cibuildwheel: Malformed environment option {environment_config!r}",
                    file=sys.stderr,
                )
                traceback.print_exc(None, sys.stderr)
                sys.exit(2)

            # Pass through environment variables
            if self.platform == "linux":
                for env_var_name in environment_pass:
                    try:
                        environment.add(env_var_name, os.environ[env_var_name])
                    except KeyError:
                        pass

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
                        image = pinned_images["musllinux_1_1"]
                    elif config_value in pinned_images:
                        image = pinned_images[config_value]
                    else:
                        image = config_value

                    musllinux_images[build_platform] = image

            return BuildOptions(
                globals=self.globals,
                test_command=test_command,
                test_requires=test_requires,
                test_extras=test_extras,
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
            )

    def check_for_invalid_configuration(self, identifiers: list[str]) -> None:
        if self.platform in ["macos", "windows"]:
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

    def summary(self, identifiers: list[str]) -> str:
        lines = [
            f"{option_name}: {option_value!r}"
            for option_name, option_value in sorted(asdict(self.globals).items())
        ]

        build_option_defaults = self.build_options(identifier=None)
        build_options_for_identifier = {
            identifier: self.build_options(identifier) for identifier in identifiers
        }

        for option_name, default_value in sorted(asdict(build_option_defaults).items()):
            if option_name == "globals":
                continue

            lines.append(f"{option_name}: {default_value!r}")

            # if any identifiers have an overridden value, print that too
            for identifier in identifiers:
                option_value = getattr(build_options_for_identifier[identifier], option_name)
                if option_value != default_value:
                    lines.append(f"  {identifier}: {option_value!r}")

        return "\n".join(lines)


def compute_options(
    platform: PlatformName,
    command_line_arguments: CommandLineArguments,
) -> Options:
    options = Options(platform=platform, command_line_arguments=command_line_arguments)
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
    all_pinned_images = ConfigParser()
    all_pinned_images.read(pinned_images_file)
    return all_pinned_images


def deprecated_selectors(name: str, selector: str, *, error: bool = False) -> None:
    if "p2" in selector or "p35" in selector:
        msg = f"cibuildwheel 2.x no longer supports Python < 3.6. Please use the 1.x series or update {name}"
        print(msg, file=sys.stderr)
        if error:
            sys.exit(4)
