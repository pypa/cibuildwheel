import os
import sys
import traceback
from configparser import ConfigParser
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

import tomli
from packaging.specifiers import SpecifierSet

from .architecture import Architecture
from .environment import EnvironmentParseError, ParsedEnvironment, parse_environment
from .projectfiles import get_requires_python_str
from .typing import PLATFORMS, Literal, PlatformName, TypedDict
from .util import (
    MANYLINUX_ARCHS,
    MUSLLINUX_ARCHS,
    BuildFrontend,
    BuildSelector,
    DependencyConstraints,
    TestSelector,
    resources_dir,
    selector_matches,
    strtobool,
    unwrap,
)


class CommandLineArguments:
    platform: Literal["auto", "linux", "macos", "windows"]
    archs: Optional[str]
    output_dir: Optional[str]
    config_file: str
    package_dir: str
    print_build_identifiers: bool
    allow_empty: bool
    prerelease_pythons: bool


class GlobalOptions(NamedTuple):
    package_dir: Path
    output_dir: Path
    build_selector: BuildSelector
    test_selector: TestSelector
    architectures: Set[Architecture]


class BuildOptions(NamedTuple):
    globals: GlobalOptions
    environment: ParsedEnvironment
    before_all: str
    before_build: Optional[str]
    repair_command: str
    manylinux_images: Optional[Dict[str, str]]
    musllinux_images: Optional[Dict[str, str]]
    dependency_constraints: Optional[DependencyConstraints]
    test_command: Optional[str]
    before_test: Optional[str]
    test_requires: List[str]
    test_extras: str
    build_verbosity: int
    build_frontend: BuildFrontend

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
    def architectures(self) -> Set[Architecture]:
        return self.globals.architectures


Setting = Union[Dict[str, str], List[str], str]


class Override(NamedTuple):
    select_pattern: str
    options: Dict[str, Setting]


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


class ConfigOptionError(KeyError):
    pass


def _dig_first(*pairs: Tuple[Mapping[str, Setting], str], ignore_empty: bool = False) -> Setting:
    """
    Return the first dict item that matches from pairs of dicts and keys.
    Will throw a KeyError if missing.

    _dig_first((dict1, "key1"), (dict2, "key2"), ...)
    """
    if not pairs:
        raise ValueError("pairs cannot be empty")

    for dict_like, key in pairs:
        if key in dict_like:
            value = dict_like[key]

            if ignore_empty and value == "":
                continue

            return value

    raise KeyError(key)


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
        config_file_path: Optional[Path] = None,
        *,
        platform: PlatformName,
        disallow: Optional[Dict[str, Set[str]]] = None,
    ) -> None:
        self.platform = platform
        self.disallow = disallow or {}

        # Open defaults.toml, loading both global and platform sections
        defaults_path = resources_dir / "defaults.toml"
        self.default_options, self.default_platform_options = self._load_file(defaults_path)

        # Load the project config file
        config_options: Dict[str, Any] = {}
        config_platform_options: Dict[str, Any] = {}

        if config_file_path is not None:
            config_options, config_platform_options = self._load_file(config_file_path)

        # Validate project config
        for option_name in config_options:
            if not self._is_valid_global_option(option_name):
                raise ConfigOptionError(f'Option "{option_name}" not supported in a config file')

        for option_name in config_platform_options:
            if not self._is_valid_platform_option(option_name):
                raise ConfigOptionError(
                    f'Option "{option_name}" not supported in the "{self.platform}" section'
                )

        self.config_options = config_options
        self.config_platform_options = config_platform_options

        self.overrides: List[Override] = []
        self.current_identifier: Optional[str] = None

        config_overrides = self.config_options.get("overrides")

        if config_overrides is not None:
            if not isinstance(config_overrides, list):
                raise ConfigOptionError('"tool.cibuildwheel.overrides" must be a list')

            for config_override in config_overrides:
                select = config_override.pop("select", None)

                if not select:
                    raise ConfigOptionError('"select" must be set in an override')

                if isinstance(select, list):
                    select = " ".join(select)

                self.overrides.append(Override(select, config_override))

    def _is_valid_global_option(self, name: str) -> bool:
        """
        Returns True if an option with this name is allowed in the
        [tool.cibuildwheel] section of a config file.
        """
        allowed_option_names = self.default_options.keys() | PLATFORMS | {"overrides"}

        return name in allowed_option_names

    def _is_valid_platform_option(self, name: str) -> bool:
        """
        Returns True if an option with this name is allowed in the
        [tool.cibuildwheel.<current-platform>] section of a config file.
        """
        disallowed_platform_options = self.disallow.get(self.platform, set())
        if name in disallowed_platform_options:
            return False

        allowed_option_names = self.default_options.keys() | self.default_platform_options.keys()

        return name in allowed_option_names

    def _load_file(self, filename: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Load a toml file, returns global and platform as separate dicts.
        """
        with filename.open("rb") as f:
            config = tomli.load(f)

        global_options = config.get("tool", {}).get("cibuildwheel", {})
        platform_options = global_options.get(self.platform, {})

        return global_options, platform_options

    @property
    def active_config_overrides(self) -> List[Override]:
        if self.current_identifier is None:
            return []
        return [
            o for o in self.overrides if selector_matches(o.select_pattern, self.current_identifier)
        ]

    @contextmanager
    def identifier(self, identifier: Optional[str]) -> Iterator[None]:
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
        sep: Optional[str] = None,
        table: Optional[TableFmt] = None,
        ignore_empty: bool = False,
    ) -> str:
        """
        Get and return the value for the named option from environment,
        configuration file, or the default. If env_plat is False, then don't
        accept platform versions of the environment variable. If this is an
        array it will be merged with "sep" before returning. If it is a table,
        it will be formatted with "table['item']" using {k} and {v} and merged
        with "table['sep']". Empty variables will not override if ignore_empty
        is True.
        """

        if name not in self.default_options and name not in self.default_platform_options:
            raise ConfigOptionError(f"{name} must be in cibuildwheel/resources/defaults.toml file")

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
                raise ConfigOptionError(f"{name} does not accept a table")
            return table["sep"].join(table["item"].format(k=k, v=v) for k, v in result.items())
        elif isinstance(result, list):
            if sep is None:
                raise ConfigOptionError(f"{name} does not accept a list")
            return sep.join(result)
        elif isinstance(result, int):
            return str(result)
        else:
            return result


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
    def config_file_path(self) -> Optional[Path]:
        args = self.command_line_arguments

        if args.config_file:
            return Path(args.config_file.format(package=args.package_dir))

        # return pyproject.toml, if it's available
        pyproject_toml_path = Path(args.package_dir) / "pyproject.toml"
        if pyproject_toml_path.exists():
            return pyproject_toml_path

        return None

    @property
    def package_requires_python_str(self) -> Optional[str]:
        if not hasattr(self, "_package_requires_python_str"):
            args = self.command_line_arguments
            self._package_requires_python_str = get_requires_python_str(Path(args.package_dir))
        return self._package_requires_python_str

    @property
    def globals(self) -> GlobalOptions:
        args = self.command_line_arguments
        package_dir = Path(args.package_dir)
        output_dir = Path(
            args.output_dir
            if args.output_dir is not None
            else os.environ.get("CIBW_OUTPUT_DIR", "wheelhouse")
        )

        build_config = self.reader.get("build", env_plat=False, sep=" ") or "*"
        skip_config = self.reader.get("skip", env_plat=False, sep=" ")
        test_skip = self.reader.get("test-skip", env_plat=False, sep=" ")

        prerelease_pythons = args.prerelease_pythons or strtobool(
            os.environ.get("CIBW_PRERELEASE_PYTHONS", "0")
        )

        # This is not supported in tool.cibuildwheel, as it comes from a standard location.
        # Passing this in as an environment variable will override pyproject.toml, setup.cfg, or setup.py
        requires_python_str: Optional[str] = (
            os.environ.get("CIBW_PROJECT_REQUIRES_PYTHON") or self.package_requires_python_str
        )
        requires_python = None if requires_python_str is None else SpecifierSet(requires_python_str)

        build_selector = BuildSelector(
            build_config=build_config,
            skip_config=skip_config,
            requires_python=requires_python,
            prerelease_pythons=prerelease_pythons,
        )
        test_selector = TestSelector(skip_config=test_skip)

        archs_config_str = args.archs or self.reader.get("archs", sep=" ")
        architectures = Architecture.parse_config(archs_config_str, platform=self.platform)

        return GlobalOptions(
            package_dir=package_dir,
            output_dir=output_dir,
            build_selector=build_selector,
            test_selector=test_selector,
            architectures=architectures,
        )

    def build_options(self, identifier: Optional[str]) -> BuildOptions:
        """
        Compute BuildOptions for a single run configuration.
        """

        with self.reader.identifier(identifier):
            before_all = self.reader.get("before-all", sep=" && ")

            build_frontend_str = self.reader.get("build-frontend", env_plat=False)
            environment_config = self.reader.get(
                "environment", table={"item": '{k}="{v}"', "sep": " "}
            )
            before_build = self.reader.get("before-build", sep=" && ")
            repair_command = self.reader.get("repair-wheel-command", sep=" && ")

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
                msg = f"cibuildwheel: Unrecognised build frontend '{build_frontend_str}', only 'pip' and 'build' are supported"
                print(msg, file=sys.stderr)
                sys.exit(2)

            try:
                environment = parse_environment(environment_config)
            except (EnvironmentParseError, ValueError):
                print(
                    f'cibuildwheel: Malformed environment option "{environment_config}"',
                    file=sys.stderr,
                )
                traceback.print_exc(None, sys.stderr)
                sys.exit(2)

            if dependency_versions == "pinned":
                dependency_constraints: Optional[
                    DependencyConstraints
                ] = DependencyConstraints.with_defaults()
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

            manylinux_images: Dict[str, str] = {}
            musllinux_images: Dict[str, str] = {}
            if self.platform == "linux":
                all_pinned_docker_images = _get_pinned_docker_images()

                for build_platform in MANYLINUX_ARCHS:
                    pinned_images = all_pinned_docker_images[build_platform]

                    config_value = self.reader.get(
                        f"manylinux-{build_platform}-image", ignore_empty=True
                    )

                    if not config_value:
                        # default to manylinux2014
                        image = pinned_images.get("manylinux2014")
                    elif config_value in pinned_images:
                        image = pinned_images[config_value]
                    else:
                        image = config_value

                    assert image is not None
                    manylinux_images[build_platform] = image

                for build_platform in MUSLLINUX_ARCHS:
                    pinned_images = all_pinned_docker_images[build_platform]

                    config_value = self.reader.get(f"musllinux-{build_platform}-image")

                    if config_value is None:
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
            )

    def check_for_invalid_configuration(self, identifiers: List[str]) -> None:
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

    def summary(self, identifiers: List[str]) -> str:
        lines = [
            f"{option_name}: {option_value!r}"
            for option_name, option_value in sorted(self.globals._asdict().items())
        ]

        build_option_defaults = self.build_options(identifier=None)

        for option_name, default_value in sorted(build_option_defaults._asdict().items()):
            if option_name == "globals":
                continue

            lines.append(f"{option_name}: {default_value!r}")

            # if any identifiers have an overridden value, print that too
            for identifier in identifiers:
                option_value = self.build_options(identifier=identifier)._asdict()[option_name]
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


_all_pinned_docker_images: Optional[ConfigParser] = None


def _get_pinned_docker_images() -> Mapping[str, Mapping[str, str]]:
    """
    This looks like a dict of dicts, e.g.
    { 'x86_64': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
      'i686': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
      'pypy_x86_64': {'manylinux2010': '...' }
      ... }
    """
    global _all_pinned_docker_images

    if _all_pinned_docker_images is None:
        pinned_docker_images_file = resources_dir / "pinned_docker_images.cfg"
        _all_pinned_docker_images = ConfigParser()
        _all_pinned_docker_images.read(pinned_docker_images_file)
    return _all_pinned_docker_images


def deprecated_selectors(name: str, selector: str, *, error: bool = False) -> None:
    if "p2" in selector or "p35" in selector:
        msg = f"cibuildwheel 2.x no longer supports Python < 3.6. Please use the 1.x series or update {name}"
        print(msg, file=sys.stderr)
        if error:
            sys.exit(4)
