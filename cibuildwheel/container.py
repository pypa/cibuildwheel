import json
import os
import uuid
from sys import getfilesystemencodeerrors
from abc import abstractmethod
from contextlib import AbstractContextManager
from pathlib import Path, PurePath
from types import TracebackType
from typing import ClassVar, Optional, List, Dict, Sequence, Union, cast

from .typing import PathOrStr
from .util import CIProvider, detect_ci_provider

class Container(AbstractContextManager):
    UTILITY_PYTHON: ClassVar[PurePath] = PurePath("/opt/python/cp38-cp38/bin/python")
    name: Optional[str] = None
    simulate_32_bit: bool = False
    docker_image: str
    cwd: Optional[PathOrStr] = None
    ci_provider: CIProvider = detect_ci_provider()

    def __init__(
        self, *, docker_image: str, simulate_32_bit: bool = False, cwd: Optional[PathOrStr] = None
    ):
        if not docker_image:
            raise ValueError("Must have a non-empty docker image to run.")
        self.docker_image = docker_image
        self.simulate_32_bit = simulate_32_bit
        self.cwd = cwd
        self.name = None

    def __enter__(self) -> "Container":
        super().__enter__()
        self.name = f"cibuildwheel-{uuid.uuid4()}"
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        assert self.name is not None
        self.name = None
        super().__exit__(exc_type, exc_value, traceback)

    @abstractmethod
    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        raise NotImplementedError

    @abstractmethod
    def copy_out(self, from_path: PurePath, to_path: Path) -> None:
        raise NotImplementedError

    def glob(self, path: PurePath, pattern: str) -> List[PurePath]:
        glob_pattern = os.path.join(str(path), pattern)

        path_strs = json.loads(
            self.call(
                [
                    self.UTILITY_PYTHON,
                    "-c",
                    f"import sys, json, glob; json.dump(glob.glob({glob_pattern!r}), sys.stdout)",
                ],
                capture_output=True,
                binary_output=True,
            )
        )

        return [PurePath(p) for p in path_strs]

    @abstractmethod
    def call(
        self,
        args: Sequence[PathOrStr],
        env: Optional[Dict[str, Union[str, bytes]]] = None,
        capture_output: bool = False,
        binary_output: bool = False,
        cwd: Optional[PathOrStr] = None,
    ) -> Union[str, bytes]:
        raise NotImplementedError

    def get_environment(self) -> Dict[str, str]:
        assert self.name is not None
        env = json.loads(
            self.call(
                [
                    self.UTILITY_PYTHON,
                    "-c",
                    "import sys, json, os; json.dump(os.environ.copy(), sys.stdout)",
                ],
                binary_output=True,
            )
        )
        return cast(Dict[str, str], env)

    def environment_executor(self, command: List[str], environment: Dict[str, str]) -> str:
        return self.call(command, env=environment, capture_output=True)

    @classmethod
    #@abstractmethod
    def unicode_decode(cls, b: bytes) -> str:
        return b.decode("raw_unicode_escape", getfilesystemencodeerrors())
