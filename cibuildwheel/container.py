import uuid
import json
import os
from pathlib import Path, PurePath
from typing import Optional, Protocol, Dict, List, Sequence, cast, ClassVar
from .typing import PathOrStr, Union
from abc import ABC, abstractmethod

class Container(ABC):
    UTILITY_PYTHON: ClassVar[str] = "/opt/python/cp38-cp38/bin/python"
    name: Optional[str] = None
    simulate_32_bit: bool = False
    cwd: Optional[PathOrStr] = None

    def __init__(
        self, *, docker_image: str, simulate_32_bit: bool = False, cwd: Optional[PathOrStr] = None
    ):
        if not docker_image:
            raise ValueError("Must have a non-empty docker image to run.")
        self.docker_image = docker_image
        self.simulate_32b = simulate_32_bit
        self.cwd = cwd
        self.name = None

    def __enter__(self) -> 'Container':
        self.name = f"cibuildwheel-{uuid.uuid4()}"

    def __exit__(self) -> None:
        self.name = None

    @abstractmethod
    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        raise NotImplementedError

    @abstractmethod
    def copy_out(self, from_path: PurePath, to_path: Path) -> None:
        raise NotImplementedError

    def glob(self, path: PurePath, pattern: str) -> List[PurePath]:
        glob_pattern = os.path.join(str(path), pattern)

        path_strs = json.loads(self.call([self.UTILITY_PYTHON, "-c",
            f"import sys, json, glob; json.dump(glob.glob({glob_pattern!r}), sys.stdout)",],
            capture_output=True
        ))

        return [PurePath(p) for p in path_strs]

    @abstractmethod
    def call(self, args: Sequence[PathOrStr], env: Optional[Dict[str,str]] = None,
            capture_output: bool = False, cwd: Optional[PathOrStr] = None
    ) -> Union[str, bytes]:
        raise NotImplementedError

    def get_environment(self) -> Dict[str, str]:
        env = json.loads(self.call(
            [self.UTILITY_PYTHON, "-c", "import sys, json, os; json.dump(os.environ.copy(), sys.stdout)",],
            capture_output=True,
        ))
        return cast(Dict[str, str], env)

    def environment_executor(self, command: List[str], environment: Dict[str, str]) -> str:
        return self.call(command, env=environment, capture_output=True)
