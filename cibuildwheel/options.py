import os
from pathlib import Path
from typing import Dict, Mapping, Tuple

import toml

from .typing import PLATFORMS

DIR = Path(__file__).parent.resolve()

Setting = str


class ConfigOptionError(KeyError):
    pass


def _dig_first(*pairs: Tuple[Mapping[str, Setting], str]) -> Setting:
    """
    Return the first dict item that matches from pairs of dicts and keys.
    Final result is will throw a KeyError if missing.

    _dig_first((dict1, "key1"), (dict2, "key2"), ...)
    """
    (dict_like, key), *others = pairs
    return dict_like.get(key, _dig_first(*others)) if others else dict_like[key]


class ConfigOptions:
    """
    Gets options from the environment, optionally scoped by the platform.

    Example:
      ConfigOptions(package_dir, 'platform='macos')
      options('cool-color')

      This will return the value of CIBW_COOL_COLOR_MACOS if it exists, otherwise the value of
      CIBW_COOL_COLOR, otherwise 'tool.cibuildwheel.cool-color' from pyproject.toml or from
      cibuildwheel/resources/defaults.toml. An error is thrown if there are any unexpected
      keys or sections in tool.cibuildwheel.
    """

    def __init__(self, project_path: Path, *, platform: str) -> None:
        self.platform = platform
        self.global_options: Dict[str, Setting] = {}
        self.platform_options: Dict[str, Setting] = {}

        # Open defaults.toml and load tool.cibuildwheel.global, then update with tool.cibuildwheel.<platform>
        self._load_file(DIR.joinpath("resources", "defaults.toml"), check=False)

        # Open pyproject.toml if it exists and load from there
        pyproject_toml = project_path.joinpath("pyproject.toml")
        self._load_file(pyproject_toml, check=True)

        # Open cibuildwheel.toml if it exists and load from there
        cibuildwheel_toml = project_path.joinpath("cibuildwheel.toml")
        self._load_file(cibuildwheel_toml, check=True)

    def _update(
        self, old_dict: Dict[str, Setting], new_dict: Dict[str, Setting], *, check: bool
    ) -> None:
        """
        Updates a dict with a new dict - optionally checking to see if the key
        is unexpected based on the current global options - call this with
        check=False when loading the defaults.toml file, and all future files
        will be forced to have no new keys.
        """
        for key in new_dict:
            if check and key not in self.global_options:
                raise ConfigOptionError(f"Key not supported, problem in config file: {key}")

            old_dict[key] = new_dict[key]

    def _load_file(self, filename: Path, *, check: bool) -> None:
        """
        Load a toml file, global and current platform. Raise an error if any unexpected
        sections are present in tool.cibuildwheel, and pass on check to _update.
        """
        # Only load if present.
        try:
            config = toml.load(filename)
        except FileNotFoundError:
            return

        # If these sections are not present, go on.
        if not config.get("tool", {}).get("cibuildwheel"):
            return

        unsupported = set(config["tool"]["cibuildwheel"]) - (PLATFORMS | {"global"})
        if unsupported:
            raise ConfigOptionError(f"Unsupported configuration section(s): {unsupported}")

        self._update(self.global_options, config["tool"]["cibuildwheel"]["global"], check=check)
        self._update(
            self.platform_options, config["tool"]["cibuildwheel"][self.platform], check=check
        )

    def __call__(self, name: str, *, platform_variants: bool = True) -> Setting:
        """
        Get and return envvar for name or the override or the default.
        """
        if name not in self.global_options:
            raise ConfigOptionError(
                f"{name} was not loaded from the cibuildwheel/resources/defaults.toml file"
            )

        envvar = f"CIBW_{name.upper().replace('-', '_')}"

        if platform_variants:
            plat_envvar = f"{envvar}_{self.platform.upper()}"
            return _dig_first(
                (os.environ, plat_envvar),
                (self.platform_options, name),
                (os.environ, envvar),
                (self.global_options, name),
            )
        else:
            return _dig_first(
                (os.environ, envvar),
                (self.global_options, name),
            )
