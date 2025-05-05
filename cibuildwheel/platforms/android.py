import importlib.util
import os
import platform
import re
import shlex
import shutil
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from typing import Any

from build import ProjectBuilder
from filelock import FileLock

from .. import errors
from ..architecture import Architecture, arch_synonym, native_platform
from ..frontend import BuildFrontendConfig, get_build_frontend_extra_flags, parse_config_settings
from ..logger import log
from ..options import BuildOptions, Options
from ..selector import BuildSelector
from ..typing import PathOrStr
from ..util import resources
from ..util.cmd import call, shell
from ..util.file import CIBW_CACHE_PATH, copy_test_sources, download, move_file
from ..util.helpers import prepare_command
from ..util.packaging import find_compatible_wheel
from ..venv import constraint_flags, virtualenv


def android_triplet(identifier: str) -> str:
    return {
        "arm64_v8a": "aarch64-linux-android",
        "x86_64": "x86_64-linux-android",
    }[parse_identifier(identifier)[1]]


def parse_identifier(identifier: str) -> tuple[str, str]:
    match = re.fullmatch(r"cp(\d)(\d+)-android_(.+)", identifier)
    if not match:
        msg = f"invalid Android identifier: '{identifier}'"
        raise ValueError(msg)
    major, minor, arch = match.groups()
    return (f"{major}.{minor}", arch)


@dataclass(frozen=True)
class PythonConfiguration:
    version: str
    identifier: str
    url: str

    @property
    def arch(self) -> str:
        return parse_identifier(self.identifier)[1]


def all_python_configurations() -> list[PythonConfiguration]:
    return [PythonConfiguration(**item) for item in resources.read_python_configs("android")]


def get_python_configurations(
    build_selector: BuildSelector, architectures: set[Architecture]
) -> list[PythonConfiguration]:
    return [
        c
        for c in all_python_configurations()
        if c.arch in architectures and build_selector(c.identifier)
    ]


def shell_prepared(command: str, build_options: BuildOptions, env: dict[str, str]) -> None:
    shell(
        prepare_command(command, project=".", package=build_options.package_dir),
        env=env,
    )


def before_all(options: Options, python_configurations: list[PythonConfiguration]) -> None:
    before_all_options = options.build_options(python_configurations[0].identifier)
    if before_all_options.before_all:
        log.step("Running before_all...")
        shell_prepared(
            before_all_options.before_all,
            before_all_options,
            before_all_options.environment.as_dictionary(os.environ),
        )


@dataclass
class Builder:
    config: PythonConfiguration
    build_options: BuildOptions
    tmp_dir: Path
    built_wheels: list[Path]

    def build(self) -> None:
        log.build_start(self.config.identifier)
        self.tmp_dir.mkdir()
        self.setup_python()

        compatible_wheel = find_compatible_wheel(self.built_wheels, self.config.identifier)
        if compatible_wheel:
            print(
                f"\nFound previously built wheel {compatible_wheel.name} that is "
                f"compatible with {self.config.identifier}. Skipping build step..."
            )
            repaired_wheel = compatible_wheel
        else:
            self.setup_env()
            self.before_build()
            repaired_wheel = self.build_wheel()

        self.test_wheel(repaired_wheel)
        if compatible_wheel is None:
            self.built_wheels.append(
                move_file(repaired_wheel, self.build_options.output_dir / repaired_wheel.name)
            )

        shutil.rmtree(self.tmp_dir)
        log.build_end()

    def setup_python(self) -> None:
        log.step("Installing target Python...")
        python_tgz = CIBW_CACHE_PATH / self.config.url.rpartition("/")[-1]
        with FileLock(f"{python_tgz}.lock"):
            if not python_tgz.exists():
                download(self.config.url, python_tgz)

        self.python_dir = self.tmp_dir / "python"
        self.python_dir.mkdir()
        shutil.unpack_archive(python_tgz, self.python_dir)

    def setup_env(self) -> None:
        log.step("Setting up build environment...")

        python_exe_name = f"python{self.config.version}"
        python_exe = shutil.which(python_exe_name)
        if not python_exe:
            msg = f"Couldn't find {python_exe_name} on the PATH"
            raise errors.FatalError(msg)

        # Create virtual environment
        self.venv_dir = self.tmp_dir / "venv"
        dependency_constraint = self.build_options.dependency_constraints.get_for_python_version(
            version=self.config.version, tmp_dir=self.tmp_dir
        )
        self.env = virtualenv(
            self.config.version,
            Path(python_exe),
            self.venv_dir,
            dependency_constraint,
            use_uv=False,
        )

        # Apply custom environment variables, and check environment is still valid
        self.env = self.build_options.environment.as_dictionary(self.env)
        self.env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        for command in ["python", "pip"]:
            which = call("which", command, env=self.env, capture_stdout=True).strip()
            if which != f"{self.venv_dir}/bin/{command}":
                msg = (
                    f"{command} available on PATH doesn't match our installed instance. If you "
                    f"have modified PATH, ensure that you don't overwrite cibuildwheel's entry "
                    f"or insert {command} above it."
                )
                raise errors.FatalError(msg)
            call(command, "--version", env=self.env)

        # Add cross-venv files, which will be activated by simulate_android.
        self.site_packages = next(self.venv_dir.glob("lib/python*/site-packages"))
        for path in [
            resources.PATH / "_cross_venv.py",
            next(self.python_dir.glob("prefix/lib/python*/_sysconfigdata_*.py")),
        ]:
            out_path = Path(shutil.copy(path, self.site_packages))
            if "sysconfigdata" in path.name:
                self.localize_sysconfigdata(out_path)

        # Install build tools
        self.build_frontend = self.build_options.build_frontend or BuildFrontendConfig("build")
        if self.build_frontend.name != "build":
            msg = "Android requires the build frontend to be 'build'"
            raise errors.FatalError(msg)
        self.pip_install("build", *constraint_flags(dependency_constraint))

        # Install build-time requirements. These must be installed for the build platform, not for
        # Android, which is why we can't allow them to be installed by the `build` subprocess.
        pb = ProjectBuilder(
            self.build_options.package_dir, python_executable=f"{self.venv_dir}/bin/python"
        )
        self.pip_install(*pb.build_system_requires)

        # get_requires_for_build runs the package's build script, so it must be called while
        # simulating Android.
        with self.simulate_android():
            requires_for_build = pb.get_requires_for_build(
                "wheel", parse_config_settings(self.build_options.config_settings)
            )
        self.pip_install(*requires_for_build)

    def localize_sysconfigdata(self, sysconfigdata_path: Path) -> None:
        spec = importlib.util.spec_from_file_location(sysconfigdata_path.stem, sysconfigdata_path)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        with sysconfigdata_path.open("w") as f:
            f.write("# Generated by cibuildwheel\n")
            f.write("build_time_vars = ")
            self.sysconfigdata = self.localized_vars(
                module.build_time_vars, self.python_dir / "prefix"
            )
            pprint(self.sysconfigdata, stream=f, compact=True)

    def localized_vars(self, orig_vars: dict[str, Any], prefix: Path) -> dict[str, Any]:
        orig_prefix = orig_vars["prefix"]
        localized_vars = {}
        for key, value in orig_vars.items():
            # The host's sysconfigdata will include references to build-time paths.
            # Update these to refer to the current prefix.
            final = value
            if isinstance(final, str):
                final = final.replace(orig_prefix, str(prefix))

            if key == "ANDROID_API_LEVEL":
                if api_level := os.environ.get(key):
                    final = int(api_level)

            # Build systems vary in whether FLAGS variables are read from sysconfig, and if so,
            # whether they're replaced by environment variables or combined with them. Even
            # setuptools has changed its behavior here
            # (https://github.com/pypa/setuptools/issues/4836).
            #
            # Ensure consistency by clearing the sysconfig variables and letting the environment
            # variables take effect alone. This will also work for any non-Python build systems
            # which the build script may call.
            elif key in ["CFLAGS", "CXXFLAGS", "LDFLAGS"]:
                final = ""

            # These variables contain an embedded copy of LDFLAGS.
            elif key in ["LDSHARED", "LDCXXSHARED"]:
                final = final.removesuffix(" " + orig_vars["LDFLAGS"])

            localized_vars[key] = final

        return localized_vars

    def pip_install(self, *args: PathOrStr) -> None:
        if args:
            call("pip", "install", "--upgrade", *args, env=self.env)

    @contextmanager
    def simulate_android(self) -> Generator[None]:
        if not hasattr(self, "android_env"):
            self.android_env = self.env.copy()
            env_output = call(
                self.python_dir / "android.py", "env", env=self.env, capture_stdout=True
            )
            for line in env_output.splitlines():
                key, value = line.removeprefix("export ").split("=", 1)
                value_split = shlex.split(value)
                assert len(value_split) == 1, value_split
                self.android_env[key] = value_split[0]

            # localized_vars cleared the CFLAGS and CXXFLAGS in the sysconfigdata, but most
            # packages take their optimization flags from these variables. Pass these flags via
            # environment variables instead.
            #
            # We don't enable debug information, because it significantly increases binary size,
            # and most Android app developers don't have the NDK installed, so they would have no
            # way to strip it.
            opt = " ".join(
                word for word in self.sysconfigdata["OPT"].split() if not word.startswith("-g")
            )
            for key in ["CFLAGS", "CXXFLAGS"]:
                self.android_env[key] += " " + opt

            # Format the environment so it can be pasted into a shell.
            for key, value in sorted(self.android_env.items()):
                if self.env.get(key) != value:
                    print(f"export {key}={shlex.quote(value)}")

        original_env = {key: os.environ.get(key) for key in self.android_env}
        os.environ.update(self.android_env)

        pth_file = self.site_packages / "_cross_venv.pth"
        pth_file.write_text("import _cross_venv; _cross_venv.initialize()")

        try:
            yield
        finally:
            pth_file.unlink()
            for key, original_value in original_env.items():
                if original_value is None:
                    del os.environ[key]
                else:
                    os.environ[key] = original_value

    def before_build(self) -> None:
        if self.build_options.before_build:
            log.step("Running before_build...")
            shell_prepared(self.build_options.before_build, self.build_options, self.env)

    def build_wheel(self) -> Path:
        log.step("Building wheel...")
        built_wheel_dir = self.tmp_dir / "built_wheel"
        with self.simulate_android():
            call(
                "python",
                "-m",
                "build",
                self.build_options.package_dir,
                "--wheel",
                "--no-isolation",
                "--skip-dependency-check",
                f"--outdir={built_wheel_dir}",
                *get_build_frontend_extra_flags(
                    self.build_frontend,
                    self.build_options.build_verbosity,
                    self.build_options.config_settings,
                ),
            )

        built_wheels = list(built_wheel_dir.glob("*.whl"))
        if len(built_wheels) != 1:
            msg = f"{built_wheel_dir} contains {len(built_wheels)} wheels; expected 1"
            raise errors.FatalError(msg)
        built_wheel = built_wheels[0]

        if built_wheel.name.endswith("none-any.whl"):
            raise errors.NonPlatformWheelError()
        return built_wheel

    def test_wheel(self, wheel: Path) -> None:
        if not (
            self.build_options.test_command
            and self.build_options.test_selector(self.config.identifier)
        ):
            return

        log.step("Testing wheel...")
        if self.config.arch != arch_synonym(platform.machine(), native_platform(), "android"):
            log.warning("Skipping tests on non-native architecture")
            return

        if self.build_options.before_test:
            shell_prepared(self.build_options.before_test, self.build_options, self.env)

        # Install the wheel and test-requires.
        site_packages_dir = self.tmp_dir / "site-packages"
        site_packages_dir.mkdir()
        self.pip_install(
            "--only-binary=:all:",
            "--platform",
            f"android_{self.sysconfigdata['ANDROID_API_LEVEL']}_{self.config.arch}",
            "--extra-index-url",
            "https://chaquo.com/pypi-13.1/",
            "--target",
            site_packages_dir,
            f"{wheel}{self.build_options.test_extras}",
            *self.build_options.test_requires,
        )

        # Copy test-sources. This option is required, as the project directory isn't visible on the
        # emulator.
        if not self.build_options.test_sources:
            msg = "Testing on this platform requires a definition of test-sources."
            raise errors.FatalError(msg)
        cwd_dir = self.tmp_dir / "cwd"
        cwd_dir.mkdir()
        copy_test_sources(self.build_options.test_sources, self.build_options.package_dir, cwd_dir)

        # Parse test-command.
        test_args = shlex.split(self.build_options.test_command)
        if test_args[:2] in [["python", "-c"], ["python", "-m"]]:
            test_args[:3] = [test_args[1], test_args[2], "--"]
        elif test_args[0] in ["pytest"]:
            test_args[:1] = ["-m", test_args[0], "--"]
        else:
            msg = (
                f"Test command '{self.build_options.test_command}' is not supported on this "
                f"platform. Supported commands are 'python -m', 'python -c' and 'pytest'."
            )
            raise errors.FatalError(msg)

        # Run the test app.
        call(
            self.python_dir / "android.py",
            "test",
            "--managed",
            "maxVersion",
            "--site-packages",
            site_packages_dir,
            "--cwd",
            cwd_dir,
            *test_args,
            env=self.env,
        )


def build(options: Options, tmp_path: Path) -> None:
    configs = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )
    if not configs:
        return

    try:
        before_all(options, configs)
        built_wheels: list[Path] = []
        for config in configs:
            Builder(
                config,
                options.build_options(config.identifier),
                tmp_path / config.identifier,
                built_wheels,
            ).build()

    except subprocess.CalledProcessError as error:
        msg = f"Command {error.cmd} failed with code {error.returncode}. {error.stdout or ''}"
        raise errors.FatalError(msg) from error
