import dataclasses
import shlex
import typing
from collections.abc import Sequence
from typing import Literal, Self, get_args

from .logger import log
from .util.helpers import parse_key_value_string

BuildFrontendName = Literal["pip", "build", "build[uv]"]


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

        name = typing.cast(BuildFrontendName, name)

        args = config_dict.get("args") or []
        return cls(name=name, args=args)

    def options_summary(self) -> str | dict[str, str]:
        if not self.args:
            return self.name
        else:
            return {"name": self.name, "args": repr(self.args)}


def _get_verbosity_flags(level: int, frontend: BuildFrontendName) -> list[str]:
    if level < 0:
        if frontend == "pip":
            return ["-" + -level * "q"]

        msg = f"build_verbosity {level} is not supported for {frontend} frontend. Ignoring."
        log.warning(msg)

    if level > 0:
        if frontend == "pip":
            return ["-" + level * "v"]
        if level > 1:
            return ["-" + (level - 1) * "v"]

    return []


def _split_config_settings(config_settings: str) -> list[str]:
    config_settings_list = shlex.split(config_settings)
    return [f"-C{setting}" for setting in config_settings_list]


def get_build_frontend_extra_flags(
    build_frontend: BuildFrontendConfig, verbosity_level: int, config_settings: str
) -> list[str]:
    return [
        *_split_config_settings(config_settings),
        *build_frontend.args,
        *_get_verbosity_flags(verbosity_level, build_frontend.name),
    ]
