import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple, Union

import toml

from .typing import PLATFORMS

DIR = Path(__file__).parent.resolve()

# These keys are allowed to merge; setting one will not go away if another is
# set in a overriding file. tool.cibuildwheel.manylinux.X will not remove
# tool.cibuildwheel.manylinux.Y from defaults, for example.
ALLOWED_TO_MERGE = {"manylinux"}


Setting = Union[Dict[str, str], List[str], str]


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
        _platform: bool = False,
    ) -> None:
        """
        Updates a dict with a new dict - optionally checking to see if the key
        is unexpected based on the current global options - call this with
        check=False when loading the defaults.toml file, and all future files
        will be forced to have no new keys.
        """

        # _platform will be True if this is being called on tool.cibuildwheel.<platform>
        # for the new_dict (old_dict does not have platforms in it)
        if _platform:
            normal_keys = set(new_dict)
        else:
            normal_keys = set(new_dict) - PLATFORMS

        for key in normal_keys:
            # Check to see if key is already present
            if update:
                # TODO: Also check nested items
                if key not in self.config:
                    msg = f"Key not supported, problem in config file: {key}"
                    raise ConfigOptionError(msg)

            # This is recursive; update dicts (subsections) if needed. Only handles one level.
            if key in ALLOWED_TO_MERGE and isinstance(new_dict[key], dict):
                if key not in old_dict:
                    old_dict[key] = {}

                old_dict[key].update(new_dict[key])
            else:
                old_dict[key] = new_dict[key]

        # Allow new_dict[<platform>][key] to override old_dict[key]
        if not _platform and self.platform in new_dict:
            self._update(old_dict, new_dict[self.platform], update=update, _platform=True)

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

    def __call__(self, name: str, *, env_plat: bool = True, sep: str = " ") -> str:
        """
        Get and return envvar for name or the override or the default. If env_plat is False,
        then don't accept platform versions of the environment variable. If this is an array
        or a dict, it will be merged with sep before returning.
        """
        config = self.config

        # Allow singly nested names, like manylinux.X
        if "." in name:
            parent, key = name.split(".")
            config = self.config[parent]
        else:
            key = name

        if key not in config:
            raise ConfigOptionError(f"{name} must be in cibuildwheel/resources/defaults.toml file")

        # Environment variable form
        envvar = f"CIBW_{name.upper().replace('-', '_').replace('.', '_')}"
        plat_envvar = f"{envvar}_{self.platform.upper()}"

        # Let environment variable override setting in config
        if env_plat:
            result = _dig_first(
                (os.environ, plat_envvar),
                (os.environ, envvar),
                (config, key),
            )
        else:
            result = _dig_first(
                (os.environ, envvar),
                (config, key),
            )

        if isinstance(result, dict):
            return sep.join(f'{k}="{v}"' for k, v in result.items())
        elif isinstance(result, list):
            return sep.join(result)
        else:
            return result
