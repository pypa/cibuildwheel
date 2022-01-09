import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path, PurePath
from typing import Dict, Iterator, Optional

from cibuildwheel.typing import Final, Literal, PathOrStr, PlatformName
from cibuildwheel.util import call, ensure_virtualenv, shell


class PlatformBackend:
    def __init__(self, platform: PlatformName, tmp_dir: PurePath):
        self._platform: Final = platform
        self._tmp_base_dir = tmp_dir
        self._tmp_counter = 0

    def call(
        self,
        *args: PathOrStr,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[PathOrStr] = None,
        capture_stdout: bool = False,
    ) -> str:
        raise NotImplementedError()

    def shell(
        self, command: str, env: Optional[Dict[str, str]] = None, cwd: Optional[PathOrStr] = None
    ) -> None:
        raise NotImplementedError()

    def mkdir(self, path: PurePath, parents: bool = False, exist_ok: bool = False) -> None:
        raise NotImplementedError()

    def rmtree(self, path: PurePath) -> None:
        raise NotImplementedError()

    def glob(self, path: PurePath, pattern: str) -> Iterator[PurePath]:
        raise NotImplementedError()

    @property
    def name(self) -> PlatformName:
        return self._platform

    @property
    def pathsep(self) -> str:
        raise NotImplementedError()

    @property
    def env(self) -> Dict[str, str]:
        raise NotImplementedError()

    @property
    def virtualenv_path(self) -> PurePath:
        raise NotImplementedError()

    @contextmanager
    def tmp_dir(self, name: str) -> Iterator[PurePath]:
        assert len(name) > 0
        name = name + "-" + str(self._tmp_counter)
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

    @property
    def pathsep(self) -> str:
        return os.pathsep

    @property
    def env(self) -> Dict[str, str]:
        return self._env

    @property
    def virtualenv_path(self) -> PurePath:
        return ensure_virtualenv()
