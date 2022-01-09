import os
import sys
from pathlib import Path
from typing import Dict, Optional

from cibuildwheel.typing import Final, Literal, PathOrStr, PlatformName
from cibuildwheel.util import call, ensure_virtualenv, shell


class PlatformBackend:
    def __init__(self, platform: PlatformName):
        self._platform: Final = platform

    def call(
        self,
        *args: PathOrStr,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[PathOrStr] = None,
        capture_stdout: Literal[False, True] = False,
    ) -> Optional[str]:
        raise NotImplementedError()

    def shell(
        self, command: str, env: Optional[Dict[str, str]] = None, cwd: Optional[PathOrStr] = None
    ) -> None:
        raise NotImplementedError()

    @property
    def name(self) -> PlatformName:
        return self._platform

    @property
    def pathsep(self) -> str:
        raise NotImplementedError

    @property
    def env(self) -> Dict[str, str]:
        raise NotImplementedError

    @property
    def virtualenv_path(self) -> Path:
        raise NotImplementedError


class NativePlatformBackend(PlatformBackend):
    def __init__(self) -> None:
        if sys.platform.startswith("linux"):
            platform: PlatformName = "linux"
        elif sys.platform == "darwin":
            platform: PlatformName = "macos"
        elif sys.platform == "win32":
            platform: PlatformName = "windows"
        else:
            raise NotImplementedError()
        self._env = os.environ.copy()
        super().__init__(platform)

    def call(
        self,
        *args: PathOrStr,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[PathOrStr] = None,
        capture_stdout: Literal[False, True] = False,
    ) -> Optional[str]:
        return call(*args, env=env, cwd=cwd, capture_stdout=capture_stdout)

    def shell(
        self, command: str, env: Optional[Dict[str, str]] = None, cwd: Optional[PathOrStr] = None
    ) -> None:
        return shell(command, env=env, cwd=cwd)

    @property
    def pathsep(self) -> str:
        return os.pathsep

    @property
    def env(self) -> Dict[str, str]:
        return self._env

    @property
    def virtualenv_path(self) -> Path:
        return ensure_virtualenv()
