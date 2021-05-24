import enum
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

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


class ConfigNamespace(enum.Enum):
    PLATFORM = enum.auto()  # Available in "global" and plat-specific namespace
    MAIN = enum.auto()  # Available without a namespace
    MANYLINUX = enum.auto()  # Only in the manylinux namespace


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
        self.config: Dict[str, Any] = {}

        # Open defaults.toml and load tool.cibuildwheel.global, then update with tool.cibuildwheel.<platform>
        self._load_file(DIR.joinpath("resources", "defaults.toml"), update=False)

        # Open pyproject.toml if it exists and load from there
        pyproject_toml = project_path.joinpath("pyproject.toml")
        self._load_file(pyproject_toml, update=True)

    def _update(
        self,
        old_dict: Dict[str, Any],
        new_dict: Dict[str, Any],
        *,
        update: bool,
        path: str = "",
    ) -> None:
        """
        Updates a dict with a new dict - optionally checking to see if the key
        is unexpected based on the current global options - call this with
        check=False when loading the defaults.toml file, and all future files
        will be forced to have no new keys.
        """

        for key in new_dict:
            # Check to see if key is already present (in global too if a platform)
            if update:
                options = set(self.config[path] if path else self.config)
                if path in PLATFORMS:
                    options |= set(self.config["global"])

                if key not in options:
                    raise ConfigOptionError(
                        f"Key not supported, problem in config file: {path} {key}"
                    )

            # This is recursive; update dicts (subsections) if needed. Only handles one level.
            if isinstance(new_dict[key], dict):
                if path:
                    raise ConfigOptionError(
                        f"Nested keys not supported, {key} should not be in {path}"
                    )

                if key not in old_dict:
                    old_dict[key] = {}

                self._update(old_dict[key], new_dict[key], update=update, path=key)
            else:
                old_dict[key] = new_dict[key]

    def _load_file(self, filename: Path, *, update: bool) -> None:
        """
        Load a toml file, global and current platform. Raise an error if any
        unexpected sections are present in tool.cibuildwheel if updating, and
        raise if any are missing if not.
        """
        # Only load if present.
        try:
            config = toml.load(filename)
        except FileNotFoundError:
            assert update, "Missing default.toml, this should not happen!"
            return

        # If these sections are not present, go on.
        tool_cibuildwheel = config.get("tool", {}).get("cibuildwheel")
        if not tool_cibuildwheel:
            assert update, "Malformed internal default.toml, this should not happen!"
            return

        self._update(self.config, tool_cibuildwheel, update=update)

    def __call__(
        self, name: str, *, namespace: ConfigNamespace = ConfigNamespace.PLATFORM
    ) -> Setting:
        """
        Get and return envvar for name or the override or the default.
        """

        # Get config settings for the requested namespace and current platform
        if namespace == ConfigNamespace.MAIN:
            config = self.config
        elif namespace == ConfigNamespace.MANYLINUX:
            config = self.config["manylinux"]
        elif namespace == ConfigNamespace.PLATFORM:
            config = {**self.config["global"], **self.config[self.platform]}

        if name not in config:
            raise ConfigOptionError(f"{name} must be in cibuildwheel/resources/defaults.toml file")

        # Environment variable form
        if namespace == ConfigNamespace.MANYLINUX:
            envvar = f"CIBW_MANYLINUX_{name.upper().replace('-', '_')}"
        else:
            envvar = f"CIBW_{name.upper().replace('-', '_')}"

        # Let environment variable override setting in config
        if namespace == ConfigNamespace.PLATFORM:
            plat_envvar = f"{envvar}_{self.platform.upper()}"
            return _dig_first(
                (os.environ, plat_envvar),
                (os.environ, envvar),
                (config, name),
            )
        else:
            return _dig_first(
                (os.environ, envvar),
                (config, name),
            )
