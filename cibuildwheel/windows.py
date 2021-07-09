import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Set
from zipfile import ZipFile

from .architecture import Architecture
from .environment import ParsedEnvironment
from .logger import log
from .typing import PathOrStr, assert_never
from .util import (
    BuildFrontend,
    BuildOptions,
    BuildSelector,
    NonPlatformWheelError,
    download,
    get_build_verbosity_extra_flags,
    get_pip_version,
    prepare_command,
    read_python_configs,
)

CIBW_INSTALL_PATH = Path("C:\\cibw")


def call(
    args: Sequence[PathOrStr], env: Optional[Dict[str, str]] = None, cwd: Optional[PathOrStr] = None
) -> None:
    print("+ " + " ".join(str(a) for a in args))
    # we use shell=True here, even though we don't need a shell due to a bug
    # https://bugs.python.org/issue8557
    subprocess.run([str(a) for a in args], env=env, cwd=cwd, shell=True, check=True)


def shell(
    command: str, env: Optional[Dict[str, str]] = None, cwd: Optional[PathOrStr] = None
) -> None:
    print(f"+ {command}")
    subprocess.run(command, env=env, cwd=cwd, shell=True, check=True)


def get_nuget_args(version: str, arch: str) -> List[str]:
    python_name = "python"
    if arch == "32":
        python_name += "x86"
    return [
        python_name,
        "-Version",
        version,
        "-FallbackSource",
        "https://api.nuget.org/v3/index.json",
        "-OutputDirectory",
        str(CIBW_INSTALL_PATH / "python"),
    ]


class PythonConfiguration(NamedTuple):
    version: str
    arch: str
    identifier: str
    url: Optional[str] = None


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],
) -> List[PythonConfiguration]:

    full_python_configs = read_python_configs("windows")

    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]

    map_arch = {
        "32": Architecture.x86,
        "64": Architecture.AMD64,
    }

    # skip builds as required
    python_configurations = [
        c
        for c in python_configurations
        if build_selector(c.identifier) and map_arch[c.arch] in architectures
    ]

    return python_configurations


def extract_zip(zip_src: Path, dest: Path) -> None:
    with ZipFile(zip_src) as zip:
        zip.extractall(dest)


def install_cpython(version: str, arch: str, nuget: Path) -> Path:
    nuget_args = get_nuget_args(version, arch)
    installation_path = Path(nuget_args[-1]) / (nuget_args[0] + "." + version) / "tools"
    call([nuget, "install", *nuget_args])
    return installation_path


def install_pypy(version: str, arch: str, url: str) -> Path:
    assert arch == "64" and "win64" in url
    # Inside the PyPy zip file is a directory with the same name
    zip_filename = url.rsplit("/", 1)[-1]
    extension = ".zip"
    assert zip_filename.endswith(extension)
    installation_path = CIBW_INSTALL_PATH / zip_filename[: -len(extension)]
    if not installation_path.exists():
        pypy_zip = CIBW_INSTALL_PATH / zip_filename
        download(url, pypy_zip)
        # Extract to the parent directory because the zip file still contains a directory
        extract_zip(pypy_zip, installation_path.parent)
        (installation_path / "python.exe").symlink_to(installation_path / "pypy3.exe")
    return installation_path


def setup_python(
    python_configuration: PythonConfiguration,
    dependency_constraint_flags: Sequence[PathOrStr],
    environment: ParsedEnvironment,
    build_frontend: BuildFrontend,
) -> Dict[str, str]:

    nuget = CIBW_INSTALL_PATH / "nuget.exe"
    if not nuget.exists():
        log.step("Downloading nuget...")
        download("https://dist.nuget.org/win-x86-commandline/latest/nuget.exe", nuget)

    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f"Installing Python {implementation_id}...")

    if implementation_id.startswith("cp"):
        installation_path = install_cpython(
            python_configuration.version, python_configuration.arch, nuget
        )
    elif implementation_id.startswith("pp"):
        assert python_configuration.url is not None
        installation_path = install_pypy(
            python_configuration.version, python_configuration.arch, python_configuration.url
        )
    else:
        raise ValueError("Unknown Python implementation")

    assert (installation_path / "python.exe").exists()

    log.step("Setting up build environment...")

    # set up PATH and environment variables for run_with_env
    env = os.environ.copy()
    env["PYTHON_VERSION"] = python_configuration.version
    env["PYTHON_ARCH"] = python_configuration.arch
    env["PATH"] = os.pathsep.join(
        [str(installation_path), str(installation_path / "Scripts"), env["PATH"]]
    )
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    # update env with results from CIBW_ENVIRONMENT
    env = environment.as_dictionary(prev_environment=env)

    # for the logs - check we're running the right version of python
    call(["where", "python"], env=env)
    call(["python", "--version"], env=env)
    call(["python", "-c", "\"import struct; print(struct.calcsize('P') * 8)\""], env=env)
    where_python = (
        subprocess.run(
            ["where", "python"],
            env=env,
            universal_newlines=True,
            check=True,
            stdout=subprocess.PIPE,
        )
        .stdout.splitlines()[0]
        .strip()
    )
    if where_python != str(installation_path / "python.exe"):
        print(
            "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    log.step("Installing build tools...")

    # Install pip

    requires_reinstall = not (installation_path / "Scripts" / "pip.exe").exists()
    if requires_reinstall:
        # maybe pip isn't installed at all. ensurepip resolves that.
        call(["python", "-m", "ensurepip"], env=env, cwd=CIBW_INSTALL_PATH)

    # upgrade pip to the version matching our constraints
    # if necessary, reinstall it to ensure that it's available on PATH as 'pip.exe'
    call(
        [
            "python",
            "-m",
            "pip",
            "install",
            "--force-reinstall" if requires_reinstall else "--upgrade",
            "pip",
            *dependency_constraint_flags,
        ],
        env=env,
        cwd=CIBW_INSTALL_PATH,
    )

    assert (installation_path / "Scripts" / "pip.exe").exists()
    where_pip = (
        subprocess.run(
            ["where", "pip"], env=env, universal_newlines=True, check=True, stdout=subprocess.PIPE
        )
        .stdout.splitlines()[0]
        .strip()
    )
    if where_pip.strip() != str(installation_path / "Scripts" / "pip.exe"):
        print(
            "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    call(["pip", "--version"], env=env)

    if build_frontend == "pip":
        call(
            [
                "pip",
                "install",
                "--upgrade",
                "setuptools",
                "wheel",
                *dependency_constraint_flags,
            ],
            env=env,
        )
    elif build_frontend == "build":
        call(
            ["pip", "install", "--upgrade", "build[virtualenv]", *dependency_constraint_flags],
            env=env,
        )
    else:
        assert_never(build_frontend)

    return env


def build(options: BuildOptions) -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="cibuildwheel"))
    built_wheel_dir = temp_dir / "built_wheel"
    repaired_wheel_dir = temp_dir / "repaired_wheel"

    try:
        if options.before_all:
            log.step("Running before_all...")
            env = options.environment.as_dictionary(prev_environment=os.environ)
            before_all_prepared = prepare_command(
                options.before_all, project=".", package=options.package_dir
            )
            shell(before_all_prepared, env=env)

        python_configurations = get_python_configurations(
            options.build_selector, options.architectures
        )

        for config in python_configurations:
            log.build_start(config.identifier)

            dependency_constraint_flags: Sequence[PathOrStr] = []
            if options.dependency_constraints:
                dependency_constraint_flags = [
                    "-c",
                    options.dependency_constraints.get_for_python_version(config.version),
                ]

            # install Python
            env = setup_python(
                config,
                dependency_constraint_flags,
                options.environment,
                options.build_frontend,
            )

            # run the before_build command
            if options.before_build:
                log.step("Running before_build...")
                before_build_prepared = prepare_command(
                    options.before_build, project=".", package=options.package_dir
                )
                shell(before_build_prepared, env=env)

            log.step("Building wheel...")
            if built_wheel_dir.exists():
                shutil.rmtree(built_wheel_dir)
            built_wheel_dir.mkdir(parents=True)

            verbosity_flags = get_build_verbosity_extra_flags(options.build_verbosity)

            if options.build_frontend == "pip":
                # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
                # see https://github.com/pypa/cibuildwheel/pull/369
                call(
                    [
                        "python",
                        "-m",
                        "pip",
                        "wheel",
                        options.package_dir.resolve(),
                        f"--wheel-dir={built_wheel_dir}",
                        "--no-deps",
                        *get_build_verbosity_extra_flags(options.build_verbosity),
                    ],
                    env=env,
                )
            elif options.build_frontend == "build":
                config_setting = " ".join(verbosity_flags)
                build_env = env.copy()
                if options.dependency_constraints:
                    constraints_path = options.dependency_constraints.get_for_python_version(
                        config.version
                    )
                    # Bug in pip <= 21.1.3 - we can't have a space in the
                    # constraints file, and pip doesn't support drive letters
                    # in uhi.  After probably pip 21.2, we can use uri. For
                    # now, use a temporary file.
                    if " " in str(constraints_path):
                        tmp_file = tempfile.NamedTemporaryFile(
                            "w", suffix="constraints.txt", delete=False, dir=CIBW_INSTALL_PATH
                        )
                        with tmp_file as new_constraints_file, open(constraints_path) as f:
                            new_constraints_file.write(f.read())
                            constraints_path = Path(new_constraints_file.name)

                    build_env["PIP_CONSTRAINT"] = str(constraints_path)
                    build_env["VIRTUALENV_PIP"] = get_pip_version(env)
                    call(
                        [
                            "python",
                            "-m",
                            "build",
                            options.package_dir,
                            "--wheel",
                            f"--outdir={built_wheel_dir}",
                            f"--config-setting={config_setting}",
                        ],
                        env=build_env,
                    )
            else:
                assert_never(options.build_frontend)

            built_wheel = next(built_wheel_dir.glob("*.whl"))

            # repair the wheel
            if repaired_wheel_dir.exists():
                shutil.rmtree(repaired_wheel_dir)
            repaired_wheel_dir.mkdir(parents=True)

            if built_wheel.name.endswith("none-any.whl"):
                raise NonPlatformWheelError()

            if options.repair_command:
                log.step("Repairing wheel...")
                repair_command_prepared = prepare_command(
                    options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir
                )
                shell(repair_command_prepared, env=env)
            else:
                shutil.move(str(built_wheel), repaired_wheel_dir)

            repaired_wheel = next(repaired_wheel_dir.glob("*.whl"))

            if options.test_command and options.test_selector(config.identifier):
                log.step("Testing wheel...")
                # set up a virtual environment to install and test from, to make sure
                # there are no dependencies that were pulled in at build time.
                call(["pip", "install", "virtualenv", *dependency_constraint_flags], env=env)
                venv_dir = Path(tempfile.mkdtemp())

                # Use --no-download to ensure determinism by using seed libraries
                # built into virtualenv
                call(["python", "-m", "virtualenv", "--no-download", venv_dir], env=env)

                virtualenv_env = env.copy()
                virtualenv_env["PATH"] = os.pathsep.join(
                    [
                        str(venv_dir / "Scripts"),
                        virtualenv_env["PATH"],
                    ]
                )

                # check that we are using the Python from the virtual environment
                call(["where", "python"], env=virtualenv_env)

                if options.before_test:
                    before_test_prepared = prepare_command(
                        options.before_test,
                        project=".",
                        package=options.package_dir,
                    )
                    shell(before_test_prepared, env=virtualenv_env)

                # install the wheel
                call(
                    ["pip", "install", str(repaired_wheel) + options.test_extras],
                    env=virtualenv_env,
                )

                # test the wheel
                if options.test_requires:
                    call(["pip", "install"] + options.test_requires, env=virtualenv_env)

                # run the tests from c:\, with an absolute path in the command
                # (this ensures that Python runs the tests against the installed wheel
                # and not the repo code)
                test_command_prepared = prepare_command(
                    options.test_command,
                    project=Path(".").resolve(),
                    package=options.package_dir.resolve(),
                )
                shell(test_command_prepared, cwd="c:\\", env=virtualenv_env)

                # clean up
                shutil.rmtree(venv_dir)

            # we're all done here; move it to output (remove if already exists)
            shutil.move(str(repaired_wheel), options.output_dir)
            log.build_end()
    except subprocess.CalledProcessError as error:
        log.step_end_with_error(
            f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
        )
        sys.exit(1)
