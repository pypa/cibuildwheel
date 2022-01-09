import sys
from pathlib import Path, PurePath
from typing import Dict, Optional, Sequence

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


def _virtualenv(
    platform: PlatformBackend,
    arch_prefix: Sequence[str],
    python: PurePath,
    venv_path: PurePath,
    constraints: Dict[str, str],
) -> Dict[str, str]:

    additional_flags = [f"--{package}={version}" for package, version in constraints.items()]

    # Using symlinks to pre-installed seed packages is really the fastest way to get a virtual
    # environment. The initial cost is a bit higher but reusing is much faster.
    # Windows does not always allow symlinks so just disabling for now.
    # Requires pip>=19.3 so disabling for "embed" because this means we don't know what's the
    # version of pip that will end-up installed.
    # c.f. https://virtualenv.pypa.io/en/latest/cli_interface.html#section-seeder
    if (
        platform.name != "windows"
        and constraints["pip"] != "embed"
        and Version(constraints["pip"]) >= Version("19.3")
    ):
        additional_flags.append("--symlink-app-data")

    platform.call(
        *arch_prefix,
        python,
        "-sS",  # just the stdlib, https://github.com/pypa/virtualenv/issues/2133#issuecomment-1003710125
        platform.virtualenv_path,
        "--activators=",
        "--no-periodic-update",
        *additional_flags,
        venv_path,
    )
    if platform.name == "windows":
        paths = [str(venv_path), str(venv_path / "Scripts")]
    else:
        paths = [str(venv_path / "bin")]
    env = platform.env.copy()
    env["PATH"] = platform.pathsep.join(paths + [env["PATH"]])
    # we version pip ourselves, so we don't care about pip version checking
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return env


class VirtualEnvBase:
    def __init__(self, platform: PlatformBackend, venv_path: PurePath, arch: Optional[str] = None):
        self.base = platform
        self.env = platform.env.copy()
        self.venv_path = venv_path
        if platform.name == "windows":
            self.script_dir = self.venv_path / "Scripts"
        else:
            self.script_dir = self.venv_path / "bin"
        self.arch = arch
        self.arch_prefix = ("arch", f"-{arch}") if arch else tuple()
        self.arch_prefix_shell = (" ".join(self.arch_prefix) + " ").strip()
        self.constraints_path: Optional[PurePath] = None

    def call(
        self,
        *args: PathOrStr,
        env: Optional[Dict[str, str]] = None,
        capture_stdout: Literal[False, True] = False,
    ) -> str:
        if env is None:
            env = self.env
        return self.base.call(*self.arch_prefix, *args, env=env, capture_stdout=capture_stdout)

    def shell(self, command: str, cwd: Optional[PathOrStr] = None) -> None:
        self.base.shell(self.arch_prefix_shell + command, cwd=cwd, env=self.env)

    def install(self, *args: PathOrStr) -> None:
        self.call("python", "-m", "pip", "install", *args)

    def which(self, cmd: str) -> PurePath:
        return self.base.which(cmd, env=self.env)

    def sanity_check(self) -> None:
        ext = ".exe" if self.base.name == "windows" else ""

        def _check(tool: str) -> None:
            expected_path = self.script_dir / f"{tool}{ext}"
            assert self.base.exists(expected_path)
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
        self.call("python", "-c", "\"import struct; print(struct.calcsize('P') * 8)\"")

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


class VirtualEnv(VirtualEnvBase):
    def __init__(
        self,
        platform: PlatformBackend,
        python: PurePath,
        venv_path: PurePath,
        constraints_path: Optional[Path] = None,
        constraints_dict: Optional[Dict[str, str]] = None,
        arch: Optional[str] = None,
    ):
        if constraints_dict is None:
            constraints = _parse_constraints_for_virtualenv(constraints_path)
        else:
            assert set(constraints_dict.keys()) == set(_SEED_PACKAGES)
            constraints = constraints_dict
        self.base = platform
        super().__init__(platform, venv_path, arch)
        self.env = _virtualenv(platform, self.arch_prefix, python, venv_path, constraints)
        self.constraints_path = None
        if constraints_path is not None:
            self.constraints_path = venv_path / "constraints.txt"
            platform.copy_into(constraints_path, self.constraints_path)


class FakeVirtualEnv(VirtualEnvBase):
    def __init__(
        self,
        platform: PlatformBackend,
        python: PurePath,
        venv_path: PurePath,
        constraints_path: Optional[Path] = None,
        constraints_dict: Optional[Dict[str, str]] = None,
        arch: Optional[str] = None,
    ):
        assert platform.name == "linux"
        assert python == venv_path / "bin" / "python"
        if constraints_path is not None:
            pass  # should we warn ? might be too verbose.
        if constraints_dict is not None:
            pass  # should we warn ? might be too verbose.
        self.base = platform
        super().__init__(platform, venv_path, arch)
        self.env["PATH"] = f'{venv_path / "bin"}:{self.env["PATH"]}'
