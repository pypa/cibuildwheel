import sys
from abc import abstractmethod
from pathlib import Path, PurePath
from types import TracebackType
from typing import Dict, List, Optional, Type

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import Version

from cibuildwheel.platform_backend import PlatformBackend
from cibuildwheel.typing import Final, Literal, PathOrStr

_SEED_PACKAGES: Final = ["pip", "setuptools", "wheel"]


def _parse_constraints_for_virtualenv(constraints_path: Optional[Path]) -> Dict[str, str]:
    """
    Parses the constraints file referenced by `constraints_path` and returns a dict where
    the key is the package name, and the value is the constraint version.
    If a package version cannot be found, its value is "embed" meaning that virtualenv will install
    its bundled version, already available locally.
    The function does not try to be too smart and just handles basic constraints.
    If it can't get an exact version, the real constraint will be handled by the
    {macos|windows}.setup_python function.
    """
    constraints_dict = {package: "embed" for package in _SEED_PACKAGES}
    if constraints_path:
        assert constraints_path.exists()
        with constraints_path.open() as constraints_file:
            for line in constraints_file:
                line = line.strip()
                if len(line) == 0:
                    continue
                if line.startswith("#"):
                    continue
                try:
                    requirement = Requirement(line)
                    package = requirement.name
                    if (
                        package not in _SEED_PACKAGES
                        or requirement.url is not None
                        or requirement.marker is not None
                        or len(requirement.extras) != 0
                        or len(requirement.specifier) != 1
                    ):
                        continue
                    specifier = next(iter(requirement.specifier))
                    if specifier.operator != "==":
                        continue
                    constraints_dict[package] = specifier.version
                except InvalidRequirement:
                    continue
    return constraints_dict


class VirtualEnvBase:
    def __init__(self, platform: PlatformBackend, arch: Optional[str] = None):
        self._base: Optional[PlatformBackend] = platform
        self.env = platform.env.copy()
        self._venv_path: Optional[PurePath] = None
        self._arch = arch
        self._arch_prefix = ("arch", f"-{arch}") if arch else tuple()
        self._arch_prefix_shell = (" ".join(self._arch_prefix) + " ").strip()
        self._constraints_path: Optional[PurePath] = None

    @abstractmethod
    def __enter__(self) -> "VirtualEnvBase":
        ...

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        ...

    def call(
        self,
        *args: PathOrStr,
        env: Optional[Dict[str, str]] = None,
        capture_stdout: Literal[False, True] = False,
    ) -> str:
        assert self._base is not None
        if env is None:
            env = self.env
        return self._base.call(*self._arch_prefix, *args, env=env, capture_stdout=capture_stdout)

    def shell(self, command: str, cwd: Optional[PathOrStr] = None) -> None:
        assert self._base is not None
        self._base.shell(self._arch_prefix_shell + command, cwd=cwd, env=self.env)

    def install(self, *args: PathOrStr, use_constraints: bool = False) -> None:
        constraints_flags: List[PathOrStr] = []
        if use_constraints and self._constraints_path is not None:
            constraints_flags = ["-c", self._constraints_path]
        self.call("python", "-m", "pip", "install", *args, *constraints_flags)

    def which(self, cmd: str) -> PurePath:
        assert self._base is not None
        return self._base.which(cmd, env=self.env)

    def sanity_check(self) -> None:
        assert self._base is not None
        assert self._venv_path is not None
        if self._base.name == "windows":
            ext = ".exe"
            scripts_dir = self._venv_path / "Scripts"
        else:
            ext = ""
            scripts_dir = self._venv_path / "bin"

        def _check(tool: str) -> None:
            assert self._base is not None
            expected_path = scripts_dir / f"{tool}{ext}"
            assert self._base.exists(expected_path)
            which = self.which(tool)
            if which != expected_path:
                print(
                    f"cibuildwheel: {tool} available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
                    file=sys.stderr,
                )
                sys.exit(1)
            self.call(tool, "--version")

        # check what Python version we're on
        _check("python")
        self.call("python", "-c", "import struct; print(struct.calcsize('P') * 8)")

        # check what pip version we're on
        _check("pip")

    @property
    def constraints_dict(self) -> Dict[str, str]:
        pip_freeze = self.call("python", "-m", "pip", "freeze", "--all", capture_stdout=True)
        all_packages = (line.split("==") for line in pip_freeze.strip().splitlines())
        return {package: version for package, version in all_packages if package in _SEED_PACKAGES}

    @property
    def pip_version(self) -> Version:
        return Version(self.constraints_dict["pip"])

    @property
    def constraints_path(self) -> Optional[PurePath]:
        return self._constraints_path


class VirtualEnv(VirtualEnvBase):
    def __init__(
        self,
        platform: PlatformBackend,
        python: PurePath,
        constraints_path: Optional[Path] = None,
        constraints_dict: Optional[Dict[str, str]] = None,
        arch: Optional[str] = None,
    ):
        if constraints_dict is None:
            constraints = _parse_constraints_for_virtualenv(constraints_path)
        else:
            assert set(constraints_dict.keys()) == set(_SEED_PACKAGES)
            constraints = constraints_dict
        self._constraints_dict = constraints
        self._constraints_path_host = constraints_path
        self._python = python
        super().__init__(platform, arch)

    def _create(self) -> None:
        assert self._venv_path is not None
        assert self._base is not None
        constraints = self._constraints_dict
        additional_flags = [f"--{package}={version}" for package, version in constraints.items()]

        # Using symlinks to pre-installed seed packages is really the fastest way to get a virtual
        # environment. The initial cost is a bit higher but reusing is much faster.
        # Windows does not always allow symlinks so just disabling for now.
        # Requires pip>=19.3 so disabling for "embed" because this means we don't know what's the
        # version of pip that will end-up installed.
        # c.f. https://virtualenv.pypa.io/en/latest/cli_interface.html#section-seeder
        if (
            self._base.name != "windows"
            and constraints["pip"] != "embed"
            and Version(constraints["pip"]) >= Version("19.3")
        ):
            additional_flags.append("--symlink-app-data")

        # Fix issue with site.py setting the wrong `sys.prefix`, `sys.exec_prefix`,
        # `sys.path`, ... for PyPy: https://foss.heptapod.net/pypy/pypy/issues/3175
        # Also fix an issue with the shebang of installed scripts inside the
        # testing virtualenv- see https://github.com/theacodes/nox/issues/44 and
        # https://github.com/pypa/virtualenv/issues/620
        # Also see https://github.com/python/cpython/pull/9516
        self.env.pop("__PYVENV_LAUNCHER__", None)

        self._base.call(
            self._python,
            "-sS",  # just the stdlib, https://github.com/pypa/virtualenv/issues/2133#issuecomment-1003710125
            self._base.virtualenv_path,
            "--activators=",
            "--no-periodic-update",
            *additional_flags,
            self._venv_path,
            env=self.env,
        )
        if self._base.name == "windows":
            scripts_dir = str(self._venv_path / "Scripts")
        else:
            scripts_dir = str(self._venv_path / "bin")
        self.env["PATH"] = self._base.pathsep.join([scripts_dir, self.env["PATH"]])
        # we version pip ourselves, so we don't care about pip version checking
        self.env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    def _cleanup(self) -> None:
        assert self._venv_path is not None
        assert self._base is not None
        self._base.rmtree(self._venv_path)
        self._base = None
        self._venv_path = None

    def __enter__(self) -> VirtualEnvBase:
        assert self._venv_path is None
        assert self._base is not None
        self._venv_path = self._base.mkdtemp("venv")
        try:
            self._create()
            if self._constraints_path_host is not None:
                self._constraints_path = self._venv_path / "constraints.txt"
                self._base.copy_into(self._constraints_path_host, self._constraints_path)
        except Exception:
            self._cleanup()
            raise
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._cleanup()


class FakeVirtualEnv(VirtualEnvBase):
    def __init__(
        self,
        platform: PlatformBackend,
        python: PurePath,
        constraints_path: Optional[Path] = None,
        constraints_dict: Optional[Dict[str, str]] = None,
        arch: Optional[str] = None,
    ):
        assert platform.name == "linux"
        venv_path = python.parent.parent
        assert python == venv_path / "bin" / "python"
        if constraints_path is not None:
            pass  # should we warn ? might be too verbose.
        if constraints_dict is not None:
            pass  # should we warn ? might be too verbose.
        self._real_path = venv_path
        super().__init__(platform, arch)

    def __enter__(self) -> VirtualEnvBase:
        assert self._real_path is not None
        assert self._venv_path is None
        assert self._base is not None
        self._venv_path = self._real_path
        self.env["PATH"] = f'{self._venv_path / "bin"}:{self.env["PATH"]}'
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._base = None
        self._venv_path = None
