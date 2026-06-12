from __future__ import annotations

import dataclasses
import shlex
import typing
from typing import Literal, get_args

from cibuildwheel.util.helpers import parse_key_value_string, prepare_command

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Self

    from cibuildwheel.typing import PathOrStr

BuildFrontendName = Literal["pip", "build", "build[uv]", "uv"]


@dataclasses.dataclass(frozen=True)
class BuildFrontendConfig:
    name: BuildFrontendName
    args: Sequence[str] = ()

    @classmethod
    def from_config_string(cls, config_string: str) -> Self:
        config_dict = parse_key_value_string(config_string, ["name"], ["args"])
        name = " ".join(config_dict["name"])
        if name not in get_args(BuildFrontendName):
            names = ", ".join(repr(n) for n in get_args(BuildFrontendName))
            msg = f"Unrecognised build frontend {name!r}, must be one of {names}"
            raise ValueError(msg)

        name = typing.cast("BuildFrontendName", name)

        args = config_dict.get("args") or []
        return cls(name=name, args=args)

    def options_summary(self) -> str | dict[str, str]:
        if not self.args:
            return self.name
        else:
            return {"name": self.name, "args": repr(self.args)}


def _get_verbosity_flags(level: int, frontend: BuildFrontendName) -> list[str]:
    if level < 0:
        return ["-" + -level * "q"]

    if level > 0:
        if frontend == "pip":
            return ["-" + level * "v"]
        if level > 1:
            return ["-" + (level - 1) * "v"]

    return []


def _split_config_settings(config_settings: str) -> list[str]:
    config_settings_list = shlex.split(config_settings)
    return [f"-C{setting}" for setting in config_settings_list]


def prepare_config_settings(config_settings: str, *, project: PathOrStr, package: PathOrStr) -> str:
    # Substitute the {project}/{package} placeholders on each already-split
    # token rather than on the raw string. A substituted path may contain
    # spaces or backslashes (e.g. a Windows `{package}` path), and the result
    # is later re-parsed with shlex.split (in _split_config_settings /
    # parse_config_settings) — substituting on the whole string would let
    # those characters be reinterpreted, splitting one setting into several or
    # eating backslashes. shlex.join re-quotes each token so the round-trip is
    # lossless.
    settings = shlex.split(config_settings)
    prepared = [prepare_command(setting, project=project, package=package) for setting in settings]
    return shlex.join(prepared)


# Based on build.__main__.main.
def parse_config_settings(config_settings_str: str) -> dict[str, str | list[str]]:
    config_settings: dict[str, str | list[str]] = {}
    for arg in shlex.split(config_settings_str):
        setting, _, value = arg.partition("=")
        existing_value = config_settings.get(setting)
        if existing_value is None:
            config_settings[setting] = value
        elif isinstance(existing_value, str):
            config_settings[setting] = [existing_value, value]
        else:
            existing_value.append(value)

    return config_settings


def get_build_frontend_extra_flags(
    build_frontend: BuildFrontendConfig, verbosity_level: int, config_settings: str
) -> list[str]:
    return [
        *_split_config_settings(config_settings),
        *build_frontend.args,
        *_get_verbosity_flags(verbosity_level, build_frontend.name),
    ]
