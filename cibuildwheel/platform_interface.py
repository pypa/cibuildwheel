from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence, Set
from pathlib import Path

from .architecture import Architecture
from .options import Options
from .typing import GenericPythonConfiguration
from .util import BuildSelector


# Can't make it frozen because we monkeypatch "build" in unit tests
@dataclasses.dataclass()
class PlatformInterface:
    get_python_configurations: Callable[
        [BuildSelector, Set[Architecture]], Sequence[GenericPythonConfiguration]
    ]
    build: Callable[[Options, Path], None]
