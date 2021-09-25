import os
import sys
import traceback
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, Union

import toml
from packaging.specifiers import SpecifierSet

from .architecture import Architecture
from .environment import EnvironmentParseError, parse_environment
from .projectfiles import get_requires_python_str
from .typing import PLATFORMS, PlatformName, TypedDict
from .util import (
    MANYLINUX_ARCHS,
    MUSLLINUX_ARCHS,
    BuildFrontend,
    BuildOptions,
    BuildSelector,
    DependencyConstraints,
    TestSelector,
    resources_dir,
    strtobool,
)

Setting = Union[Dict[str, str], List[str], str]


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


class ConfigOptions:
    """
    Gets options from the environment, config or defaults, optionally scoped
    by the platform.

    Example:
      >>> options = ConfigOptions(package_dir, platform='macos')
      >>> options('cool-color')

      This will return the value of CIBW_COOL_COLOR_MACOS if it exists,
      otherwise the value of CIBW_COOL_COLOR, otherwise
      'tool.cibuildwheel.macos.cool-color' or 'tool.cibuildwheel.cool-color'
      from pyproject.toml, or from cibuildwheel/resources/defaults.toml. An
      error is thrown if there are any unexpected keys or sections in
      tool.cibuildwheel.
    """

    def __init__(
        self,
        package_path: Path,
        config_file: Optional[str] = None,
        *,
        platform: str,
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

        if config_file is not None:
            config_path = Path(config_file.format(package=package_path))
            config_options, config_platform_options = self._load_file(config_path)
        else:
            # load pyproject.toml, if it's available
            pyproject_toml_path = package_path / "pyproject.toml"
            if pyproject_toml_path.exists():
                config_options, config_platform_options = self._load_file(pyproject_toml_path)

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

    def _is_valid_global_option(self, name: str) -> bool:
        """
        Returns True if an option with this name is allowed in the
        [tool.cibuildwheel] section of a config file.
        """
        allowed_option_names = self.default_options.keys() | PLATFORMS

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
        config = toml.load(filename)

        global_options = config.get("tool", {}).get("cibuildwheel", {})
        platform_options = global_options.get(self.platform, {})

        return global_options, platform_options

    def __call__(
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

        # get the option from the environment, then the config file, then finally the default.
        # platform-specific options are preferred, if they're allowed.
        result = _dig_first(
            (os.environ if env_plat else {}, plat_envvar),  # type: ignore
            (os.environ, envvar),
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


def compute_options(
    platform: PlatformName,
    package_dir: Path,
    output_dir: Path,
    config_file: Optional[str],
    args_archs: Optional[str],
    prerelease_pythons: bool,
) -> BuildOptions:
    """
    Compute the options from the environment and configuration file.
    """

    manylinux_identifiers = {
        f"manylinux-{build_platform}-image" for build_platform in MANYLINUX_ARCHS
    }
    musllinux_identifiers = {
        f"musllinux-{build_platform}-image" for build_platform in MUSLLINUX_ARCHS
    }
    disallow = {
        "linux": {"dependency-versions"},
        "macos": manylinux_identifiers | musllinux_identifiers,
        "windows": manylinux_identifiers | musllinux_identifiers,
    }
    options = ConfigOptions(package_dir, config_file, platform=platform, disallow=disallow)

    build_config = options("build", env_plat=False, sep=" ") or "*"
    skip_config = options("skip", env_plat=False, sep=" ")
    test_skip = options("test-skip", env_plat=False, sep=" ")

    prerelease_pythons = prerelease_pythons or strtobool(
        os.environ.get("CIBW_PRERELEASE_PYTHONS", "0")
    )

    deprecated_selectors("CIBW_BUILD", build_config, error=True)
    deprecated_selectors("CIBW_SKIP", skip_config)
    deprecated_selectors("CIBW_TEST_SKIP", test_skip)

    package_files = {"setup.py", "setup.cfg", "pyproject.toml"}

    if not any(package_dir.joinpath(name).exists() for name in package_files):
        names = ", ".join(sorted(package_files, reverse=True))
        msg = f"cibuildwheel: Could not find any of {{{names}}} at root of package"
        print(msg, file=sys.stderr)
        sys.exit(2)

    # This is not supported in tool.cibuildwheel, as it comes from a standard location.
    # Passing this in as an environment variable will override pyproject.toml, setup.cfg, or setup.py
    requires_python_str: Optional[str] = os.environ.get(
        "CIBW_PROJECT_REQUIRES_PYTHON"
    ) or get_requires_python_str(package_dir)
    requires_python = None if requires_python_str is None else SpecifierSet(requires_python_str)

    build_selector = BuildSelector(
        build_config=build_config,
        skip_config=skip_config,
        requires_python=requires_python,
        prerelease_pythons=prerelease_pythons,
    )
    test_selector = TestSelector(skip_config=test_skip)

    return _compute_single_options(
        options, args_archs, build_selector, test_selector, platform, package_dir, output_dir
    )


def _compute_single_options(
    options: ConfigOptions,
    args_archs: Optional[str],
    build_selector: BuildSelector,
    test_selector: TestSelector,
    platform: PlatformName,
    package_dir: Path,
    output_dir: Path,
) -> BuildOptions:
    """
    Compute BuildOptions for a single run configuration.
    """
    # Can't be configured per selector
    before_all = options("before-all", sep=" && ")

    archs_config_str = args_archs or options("archs", sep=" ")

    build_frontend_str = options("build-frontend", env_plat=False)
    environment_config = options("environment", table={"item": '{k}="{v}"', "sep": " "})
    before_build = options("before-build", sep=" && ")
    repair_command = options("repair-wheel-command", sep=" && ")

    dependency_versions = options("dependency-versions")
    test_command = options("test-command", sep=" && ")
    before_test = options("before-test", sep=" && ")
    test_requires = options("test-requires", sep=" ").split()
    test_extras = options("test-extras", sep=",")
    build_verbosity_str = options("build-verbosity")

    build_frontend: BuildFrontend
    if build_frontend_str == "build":
        build_frontend = "build"
    elif build_frontend_str == "pip":
        build_frontend = "pip"
    else:
        msg = f"cibuildwheel: Unrecognised build frontend '{build_frontend}', only 'pip' and 'build' are supported"
        print(msg, file=sys.stderr)
        sys.exit(2)

    try:
        environment = parse_environment(environment_config)
    except (EnvironmentParseError, ValueError):
        print(f'cibuildwheel: Malformed environment option "{environment_config}"', file=sys.stderr)
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

    archs = Architecture.parse_config(archs_config_str, platform=platform)

    manylinux_images: Dict[str, str] = {}
    musllinux_images: Dict[str, str] = {}
    if platform == "linux":
        pinned_docker_images_file = resources_dir / "pinned_docker_images.cfg"
        all_pinned_docker_images = ConfigParser()
        all_pinned_docker_images.read(pinned_docker_images_file)
        # all_pinned_docker_images looks like a dict of dicts, e.g.
        # { 'x86_64': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
        #   'i686': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
        #   'pypy_x86_64': {'manylinux2010': '...' }
        #   ... }

        for build_platform in MANYLINUX_ARCHS:
            pinned_images = all_pinned_docker_images[build_platform]

            config_value = options(f"manylinux-{build_platform}-image", ignore_empty=True)

            if not config_value:
                # default to manylinux2010 if it's available, otherwise manylinux2014
                image = pinned_images.get("manylinux2010") or pinned_images.get("manylinux2014")
            elif config_value in pinned_images:
                image = pinned_images[config_value]
            else:
                image = config_value

            manylinux_images[build_platform] = image

        for build_platform in MUSLLINUX_ARCHS:
            pinned_images = all_pinned_docker_images[build_platform]

            config_value = options(f"musllinux-{build_platform}-image")

            if config_value is None:
                image = pinned_images.get("musllinux_1_1")
            elif config_value in pinned_images:
                image = pinned_images[config_value]
            else:
                image = config_value

            musllinux_images[build_platform] = image

    return BuildOptions(
        architectures=archs,
        package_dir=package_dir,
        output_dir=output_dir,
        test_command=test_command,
        test_requires=test_requires,
        test_extras=test_extras,
        before_test=before_test,
        before_build=before_build,
        before_all=before_all,
        build_verbosity=build_verbosity,
        build_selector=build_selector,
        test_selector=test_selector,
        repair_command=repair_command,
        environment=environment,
        dependency_constraints=dependency_constraints,
        manylinux_images=manylinux_images or None,
        musllinux_images=musllinux_images or None,
        build_frontend=build_frontend,
    )


def deprecated_selectors(name: str, selector: str, *, error: bool = False) -> None:
    if "p2" in selector or "p35" in selector:
        msg = f"cibuildwheel 2.x no longer supports Python < 3.6. Please use the 1.x series or update {name}"
        print(msg, file=sys.stderr)
        if error:
            sys.exit(4)
