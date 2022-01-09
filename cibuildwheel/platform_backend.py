import os
import shutil
import sys
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path, PurePath
from typing import Dict, Iterator, List, Optional

from cibuildwheel.bashlex_eval import local_environment_executor
from cibuildwheel.typing import Final, Literal, PathOrStr, PlatformName
from cibuildwheel.util import call, ensure_virtualenv, shell


class PlatformBackend:
    def __init__(self, platform: PlatformName, tmp_dir: PurePath):
        self._platform: Final = platform
        self._tmp_base_dir = tmp_dir
        self._tmp_counter = 0
        self._fsmap_file: Dict[Path, PurePath] = {}
        self._fsmap_dir: Dict[Path, PurePath] = {}

    @abstractmethod
    def call(
        self,
        *args: PathOrStr,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[PathOrStr] = None,
        capture_stdout: bool = False,
    ) -> str:
        ...

    @abstractmethod
    def shell(
        self, command: str, env: Optional[Dict[str, str]] = None, cwd: Optional[PathOrStr] = None
    ) -> None:
        ...

    @abstractmethod
    def mkdir(self, path: PurePath, parents: bool = False, exist_ok: bool = False) -> None:
        ...

    @abstractmethod
    def rmtree(self, path: PurePath) -> None:
        ...

    @abstractmethod
    def glob(self, path: PurePath, pattern: str) -> Iterator[PurePath]:
        ...

    @abstractmethod
    def exists(self, path: PurePath) -> bool:
        ...

    @abstractmethod
    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        ...

    def copy_into_(self, from_path: Path, to_path: PurePath) -> None:
        from_path = from_path.resolve(strict=True)
        if from_path.is_dir():
            self._fsmap_dir[from_path] = to_path
        else:
            self._fsmap_file[from_path] = to_path

    @abstractmethod
    def environment_executor(self, command: List[str], environment: Dict[str, str]) -> str:
        ...

    def get_remote_path(self, local_path: Path) -> PurePath:
        resolved_path = local_path.resolve()
        if local_path.is_file():
            if resolved_path in self._fsmap_file:
                return self._fsmap_file[resolved_path]
        for local_dir, remote_dir in self._fsmap_dir.items():
            if resolved_path == local_dir:
                return remote_dir
            try:
                return remote_dir / resolved_path.relative_to(local_dir)
            except ValueError:
                pass  # not relative to
        message = f"path '{resolved_path}' not found in:\n{self._fsmap_file}\n{self._fsmap_dir}"
        raise FileNotFoundError(message)

    def which(self, cmd: str, env: Optional[Dict[str, str]] = None) -> PurePath:
        if self.name == "windows":
            tool = "where"
        else:
            tool = "which"
        results = self.call(tool, cmd, env=env, capture_stdout=True).splitlines()
        for result in results:
            print(result.strip())
        return PurePath(results[0].strip())

    @property
    def name(self) -> PlatformName:
        return self._platform

    @property
    @abstractmethod
    def pathsep(self) -> str:
        ...

    @property
    @abstractmethod
    def env(self) -> Dict[str, str]:
        ...

    @property
    @abstractmethod
    def home(self) -> PurePath:
        ...

    @property
    @abstractmethod
    def virtualenv_path(self) -> PurePath:
        ...

    @contextmanager
    def tmp_dir(self, name: str) -> Iterator[PurePath]:
        assert len(name) > 0
        name = name + "-" + str(self._tmp_counter)
        self._tmp_counter += 1
        path = self._tmp_base_dir / name
        self.mkdir(path)
        try:
            yield path
        finally:
            self.rmtree(path)


class NativePlatformBackend(PlatformBackend):
    def __init__(self, tmp_dir: PurePath) -> None:
        if sys.platform.startswith("linux"):
            platform: PlatformName = "linux"
        elif sys.platform == "darwin":
            platform: PlatformName = "macos"
        elif sys.platform == "win32":
            platform: PlatformName = "windows"
        else:
            raise NotImplementedError()
        self._env = os.environ.copy()
        super().__init__(platform, tmp_dir)

    def call(
        self,
        *args: PathOrStr,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[PathOrStr] = None,
        capture_stdout: Literal[False, True] = False,
    ) -> str:
        return call(*args, env=env, cwd=cwd, capture_stdout=capture_stdout)

    def shell(
        self, command: str, env: Optional[Dict[str, str]] = None, cwd: Optional[PathOrStr] = None
    ) -> None:
        shell(command, env=env, cwd=cwd)

    def mkdir(self, path: PurePath, parents: bool = False, exist_ok: bool = False) -> None:
        Path(path).mkdir(parents=parents, exist_ok=exist_ok)

    def rmtree(self, path: PurePath) -> None:
        shutil.rmtree(path, ignore_errors=self.name == "windows")

    def glob(self, path: PurePath, pattern: str) -> Iterator[PurePath]:
        return Path(path).glob(pattern)

    def exists(self, path: PurePath) -> bool:
        return Path(path).exists()

    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        assert from_path.exists()
        if from_path.is_dir():
            shutil.copytree(from_path, to_path)
        else:
            shutil.copy(from_path, to_path)
        super().copy_into_(from_path, to_path)

    def environment_executor(self, command: List[str], environment: Dict[str, str]) -> str:
        return local_environment_executor(command, environment)

    def get_remote_path(self, local_path: Path) -> PurePath:
        return local_path

    @property
    def pathsep(self) -> str:
        return os.pathsep

    @property
    def env(self) -> Dict[str, str]:
        return self._env

    @property
    def home(self) -> PurePath:
        return Path.home()

    @property
    def virtualenv_path(self) -> PurePath:
        return ensure_virtualenv()
