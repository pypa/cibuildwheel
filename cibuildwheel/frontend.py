from __future__ import annotations

__lazy_modules__ = {"cibuildwheel.util.helpers", "shlex"}

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

BuildFrontendName = Literal["pip", "build", "build[uv]", "uv", "pyodide-build"]
ConfigSettings = dict[str, str | list[str]]


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
    if frontend == "pyodide-build":
        if level > 0:
            return ["-" + min(level, 2) * "v"]
        return []

    if level < 0:
        return ["-" + -level * "q"]

    if level > 0:
        if frontend == "pip":
            return ["-" + level * "v"]
        if level > 1:
            return ["-" + (level - 1) * "v"]

    return []


def _get_config_settings_flags(config_settings: ConfigSettings) -> list[str]:
    flags: list[str] = []
    for key, value in config_settings.items():
        values = [value] if isinstance(value, str) else value
        for item in values:
            if key:
                flags.append(f"-C{key}={item}")
            else:
                flags.extend(["-C", f"={item}"])
    return flags


def prepare_config_settings(
    config_settings: ConfigSettings, *, project: PathOrStr, package: PathOrStr
) -> ConfigSettings:
    prepared: ConfigSettings = {}
    for key, value in config_settings.items():
        if isinstance(value, str):
            prepared[key] = prepare_command(value, project=project, package=package)
        else:
            prepared[key] = [
                prepare_command(item, project=project, package=package) for item in value
            ]
    return prepared


def parse_config_settings(config_settings_str: str) -> ConfigSettings:
    config_settings: ConfigSettings = {}
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
    build_frontend: BuildFrontendConfig,
    verbosity_level: int,
    config_settings: ConfigSettings,
) -> list[str]:
    return [
        *_get_config_settings_flags(config_settings),
        *build_frontend.args,
        *_get_verbosity_flags(verbosity_level, build_frontend.name),
    ]
