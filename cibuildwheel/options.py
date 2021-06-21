import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, Union

import toml

from .typing import PLATFORMS, TypedDict
from .util import resources_dir

Setting = Union[Dict[str, str], List[str], str]


class TableFmt(TypedDict):
    item: str
    sep: str


class ConfigOptionError(KeyError):
    pass


def _dig_first(*pairs: Tuple[Mapping[str, Any], str]) -> Setting:
    """
    Return the first dict item that matches from pairs of dicts and keys.
    Final result is will throw a KeyError if missing.

    _dig_first((dict1, "key1"), (dict2, "key2"), ...)
    """
    (dict_like, key), *others = pairs
    return dict_like.get(key, _dig_first(*others)) if others else dict_like[key]


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

        # load the project config file
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

        # validate project config
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
    ) -> str:
        """
        Get and return the value for the named option from environment,
        configuration file, or the default. If env_plat is False, then don't
        accept platform versions of the environment variable. If this is an
        array it will be merged with "sep" before returning. If it is a table,
        it will be formatted with "table['item']" using {k} and {v} and merged
        with "table['sep']".
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
