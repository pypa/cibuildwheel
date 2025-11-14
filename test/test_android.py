import os
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from subprocess import CalledProcessError
from textwrap import dedent
from zipfile import ZipFile

import pytest

from .test_projects import new_c_project
from .utils import cibuildwheel_run, expected_wheels

pytestmark = pytest.mark.android


CIBW_PLATFORM = os.environ.get("CIBW_PLATFORM", "android")
if CIBW_PLATFORM != "android":
    pytest.skip(f"{CIBW_PLATFORM=}", allow_module_level=True)

if (platform.system(), platform.machine()) not in [
    ("Linux", "x86_64"),
    ("Darwin", "arm64"),
    ("Darwin", "x86_64"),
]:
    pytest.skip(
        f"cibuildwheel does not support building Android wheels on "
        f"{platform.system()} {platform.machine()}",
        allow_module_level=True,
    )

# Azure Pipelines does not set the CI variable.
ci = any(key in os.environ for key in ["CI", "TF_BUILD"])

if "ANDROID_HOME" not in os.environ:
    msg = "ANDROID_HOME environment variable is not set"

    # Fail if we're on a CI service which is supposed to have the Android SDK
    # pre-installed; otherwise skip the module.
    if (
        ("CIRRUS_CI" in os.environ and platform.system() == "Darwin")
        or "GITHUB_ACTIONS" in os.environ
        or "TF_BUILD" in os.environ
    ):
        pytest.fail(msg)
    else:
        pytest.skip(msg, allow_module_level=True)

# Many CI services don't support running the Android emulator: see platforms.md.
supports_emulator = (not ci) or ("GITHUB_ACTIONS" in os.environ and platform.system() == "Linux")


def needs_emulator(test):
    # All copies of the testbed app run on the same emulator with the same
    # application ID, so these tests must be run serially.
    test = pytest.mark.serial(test)

    if not supports_emulator:
        test = pytest.mark.skip("This CI platform doesn't support the emulator")(test)
    return test


@dataclass
class Architecture:
    linux_machine: str
    macos_machine: str
    android_abi: str


archs = [
    Architecture("aarch64", "arm64", "arm64_v8a"),
    Architecture("x86_64", "x86_64", "x86_64"),
]
native_arch = next(
    arch for arch in archs if platform.machine() in [arch.linux_machine, arch.macos_machine]
)


cp313_env = {
    "CIBW_PLATFORM": "android",
    "CIBW_BUILD": "cp313-*",
}


def test_android_home(tmp_path, capfd):
    new_c_project().generate(tmp_path)
    env = os.environ.copy()
    del env["ANDROID_HOME"]

    with pytest.raises(CalledProcessError):
        cibuildwheel_run(tmp_path, env={**env, **cp313_env})
    assert "ANDROID_HOME environment variable is not set" in capfd.readouterr().err


# android-env.sh may need to install the NDK, and it isn't safe to do that multiple
# times in parallel. So make sure there's at least one test which gets as far as doing
# a build, which is marked as serial so it will run before the parallel tests, but isn't
# marked as needs_emulator so it will run on all CI platforms.
@pytest.mark.serial
def test_expected_wheels(tmp_path, spam_env):
    # Since this test covers all Python versions, check the cross venv.
    test_module = "_cross_venv_test_android"
    project = new_c_project(setup_py_add=f"import {test_module}")
    project.files[f"{test_module}.py"] = (Path(__file__).parent / f"{test_module}.py").read_text()
    project.generate(tmp_path)

    # Build wheels for all Python versions on the current architecture.
    del spam_env["CIBW_BUILD"]
    if not supports_emulator:
        del spam_env["CIBW_TEST_COMMAND"]

    wheels = cibuildwheel_run(tmp_path, add_env=spam_env)
    assert wheels == expected_wheels(
        "spam", "0.1.0", platform="android", machine_arch=native_arch.android_abi
    )


@needs_emulator
def test_frontend_good(tmp_path, build_frontend_env):
    new_c_project().generate(tmp_path)
    wheels = cibuildwheel_run(
        tmp_path,
        add_env={**cp313_env, **build_frontend_env, "CIBW_TEST_COMMAND": "python -m site"},
    )
    assert wheels == [f"spam-0.1.0-cp313-cp313-android_21_{native_arch.android_abi}.whl"]


@pytest.mark.parametrize("frontend", ["pip"])
def test_frontend_bad(frontend, tmp_path, capfd):
    new_c_project().generate(tmp_path)
    with pytest.raises(CalledProcessError):
        cibuildwheel_run(
            tmp_path,
            add_env={**cp313_env, "CIBW_BUILD_FRONTEND": frontend},
        )
    assert "Android requires the build frontend to be 'build'" in capfd.readouterr().err


@needs_emulator
def test_archs(tmp_path, capfd):
    new_c_project().generate(tmp_path)

    # Build all architectures while checking the handling of the `before` commands.
    command_pattern = 'echo "Hello from {0}, package={{package}}, python=$(which python)"'
    output_pattern = (
        f"Hello from {{0}}, package={tmp_path}, python=/.+/cp313-android_{{1}}/venv/bin/python"
    )

    wheels = cibuildwheel_run(
        tmp_path,
        add_env={
            **cp313_env,
            "CIBW_ARCHS": "all",
            "CIBW_BEFORE_ALL": "echo 'Hello from before_all'",
            "CIBW_BEFORE_BUILD": command_pattern.format("before_build"),
            "CIBW_BEFORE_TEST": command_pattern.format("before_test"),
            "CIBW_TEST_COMMAND": (
                "python -c 'import platform; print(f\"Hello from {platform.machine()}\")'"
            ),
        },
    )
    assert wheels == [f"spam-0.1.0-cp313-cp313-android_21_{arch.android_abi}.whl" for arch in archs]

    stdout, stderr = capfd.readouterr()
    lines = (line for line in stdout.splitlines() if line.startswith("Hello from"))
    assert next(lines) == "Hello from before_all"

    # All architectures should be built, but only the native architecture should run tests.
    for arch in archs:
        abi = arch.android_abi
        assert re.fullmatch(output_pattern.format("before_build", abi), next(lines))
        if arch == native_arch:
            assert re.fullmatch(output_pattern.format("before_test", abi), next(lines))
            assert next(lines) == f"Hello from {arch.linux_machine}"
        else:
            assert (
                f"Skipping tests for {arch.android_abi}, as the build machine "
                f"only supports {native_arch.android_abi}"
            ) in stderr

    try:
        line = next(lines)
    except StopIteration:
        pass
    else:
        pytest.fail(f"Unexpected line: {line!r}")


def test_build_requires(tmp_path, capfd):
    # Build-time requirements should be installed for the build platform, not for Android. Prove
    # this by installing some non-pure-Python requirements and using them in setup.py.
    #
    # setup_requires is installed via ProjectBuilder.get_requires_for_build.
    project = new_c_project(
        setup_py_setup_args_add="setup_requires=['cmake==3.31.4']",
        setup_py_add=dedent(
            """\
            if "egg_info" not in sys.argv:
                import subprocess
                subprocess.run(["cmake", "--version"], check=True)

                from bitarray import bitarray
                print(f"{bitarray('10110').count()=}")
            """
        ),
    )

    # [build_system] requires is installed via ProjectBuilder.build_system_requires.
    project.files["pyproject.toml"] = dedent(
        """\
        [build-system]
        requires = ["setuptools", "wheel", "bitarray==3.3.2"]
        """
    )

    project.generate(tmp_path)
    cibuildwheel_run(tmp_path, add_env={**cp313_env})

    # Test for a specific version to minimize the chance that we ran a system cmake.
    stdout = capfd.readouterr().out
    assert "cmake version 3.31.4" in stdout
    assert "bitarray('10110').count()=3" in stdout


@pytest.fixture
def spam_env(tmp_path):
    project = new_c_project()
    project.files["test_spam.py"] = dedent(
        """\
        import spam

        def test_spam():
            assert spam.filter("ham")
            assert not spam.filter("spam")
            print("Spam test passed")
        """
    )
    project.files["test_empty.py"] = dedent(
        """\
        def test_empty():
            pass
        """
    )

    project.generate(tmp_path)

    return {
        **cp313_env,
        "CIBW_TEST_SOURCES": "test_spam.py test_empty.py",
        "CIBW_TEST_REQUIRES": "pytest==8.3.5",
        "CIBW_TEST_COMMAND": "python -m pytest",
    }


@needs_emulator
@pytest.mark.parametrize(
    ("command", "expected_output"),
    [
        ("python3 -c 'import test_spam; test_spam.test_spam()'", "Spam test passed"),
        ("python -m pytest", "=== 2 passed in "),
        ("python -m pytest test_spam.py", "=== 1 passed in "),
        ("pytest test_spam.py", "=== 1 passed in "),
    ],
)
def test_test_command_good(command, expected_output, tmp_path, spam_env, capfd):
    cibuildwheel_run(tmp_path, add_env={**spam_env, "CIBW_TEST_COMMAND": command})
    stdout, stderr = capfd.readouterr()
    assert expected_output in stdout

    if not command.startswith("python"):
        assert (
            f"Test command {command!r} is not supported on Android. cibuildwheel "
            "will try to execute it as if it started with 'python -m'."
        ) in stderr


BAD_FORMAT_ERROR = (
    "Test command '{}' is not supported on Android. "
    "Command must begin with 'python' or 'python3', and contain '-m' or '-c'."
)
BAD_PLACEHOLDER_ERROR = (
    "Test command '{}' with a '{{project}}' or '{{package}}' placeholder "
    "is not supported on Android"
)


@needs_emulator
@pytest.mark.parametrize(
    ("command", "expected_output"),
    [
        # Build-time failure
        ("./test_spam.py", BAD_FORMAT_ERROR.format("./test_spam.py")),
        ("python test_spam.py", BAD_FORMAT_ERROR.format("python test_spam.py")),
        ("pytest {project}", BAD_PLACEHOLDER_ERROR.format("pytest {project}")),
        ("pytest {package}", BAD_PLACEHOLDER_ERROR.format("pytest {package}")),
        # Runtime failure
        ("pytest test_ham.py", "not found: test_ham.py"),
    ],
)
def test_test_command_bad(command, expected_output, tmp_path, spam_env, capfd):
    with pytest.raises(CalledProcessError):
        cibuildwheel_run(tmp_path, add_env={**spam_env, "CIBW_TEST_COMMAND": command})
    assert expected_output in capfd.readouterr().err


@needs_emulator
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ("", 0),
        ("-E", 1),
    ],
)
def test_test_command_python_options(options, expected, tmp_path, capfd):
    project = new_c_project()
    project.generate(tmp_path)

    command = 'import sys; print(f"{sys.flags.ignore_environment=}")'
    cibuildwheel_run(
        tmp_path,
        add_env={
            **cp313_env,
            "CIBW_TEST_COMMAND": f"python {options} -c '{command}'",
        },
    )
    assert f"sys.flags.ignore_environment={expected}" in capfd.readouterr().out


@needs_emulator
def test_package_subdir(tmp_path, spam_env, capfd):
    spam_paths = list(tmp_path.iterdir())
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    for path in spam_paths:
        path.rename(package_dir / path.name)

    spam_env["CIBW_TEST_SOURCES"] = " ".join(
        f"package/{path}" for path in spam_env["CIBW_TEST_SOURCES"].split()
    )
    cibuildwheel_run(tmp_path, package_dir, add_env=spam_env)
    assert "=== 2 passed in " in capfd.readouterr().out


@needs_emulator
def test_no_test_sources(tmp_path, capfd):
    new_c_project().generate(tmp_path)
    with pytest.raises(CalledProcessError):
        cibuildwheel_run(
            tmp_path,
            add_env={**cp313_env, "CIBW_TEST_COMMAND": "python -m unittest discover"},
        )
    assert (
        "On this platform, you must copy your test files to the testbed app by "
        "setting the `test-sources` option"
    ) in capfd.readouterr().err


@needs_emulator
def test_environment_markers(tmp_path):
    project = new_c_project()
    test_filename = "test_environment_markers.py"
    project.files[test_filename] = dedent(
        """\
        import pytest

        def test_android():
            import certifi

        def test_not_android():
            try:
                import platformdirs
            except ImportError:
                pass
            else:
                pytest.fail("`platformdirs` should not have been installed")
        """
    )
    project.generate(tmp_path)

    cibuildwheel_run(
        tmp_path,
        add_env={
            **cp313_env,
            "CIBW_TEST_COMMAND": f"python -m pytest {test_filename}",
            "CIBW_TEST_SOURCES": test_filename,
            "CIBW_TEST_REQUIRES": "pytest certifi;sys_platform=='android' platformdirs;sys_platform!='android'",
        },
    )


@needs_emulator
def test_verbosity(tmp_path, capfd):
    new_c_project().generate(tmp_path)
    test_env = {
        **cp313_env,
        "CIBW_TEST_COMMAND": """python -c 'print("Hello world")'""",
    }
    verbose_lines = [
        "> Task :app:packageDebug",  # Gradle
        "I/TestRunner: run started: 1 tests",  # Logcat
    ]

    cibuildwheel_run(tmp_path, add_env=test_env)
    stdout = capfd.readouterr().out
    for line in verbose_lines:
        assert line not in stdout

    cibuildwheel_run(
        tmp_path,
        add_env={**test_env, "CIBW_BUILD_VERBOSITY": "1"},
    )
    stdout = capfd.readouterr().out
    for line in verbose_lines:
        assert line in stdout


@needs_emulator
def test_api_level(tmp_path, capfd):
    project = new_c_project()
    project.files["pyproject.toml"] = dedent(
        """\
        [build-system]
        requires = ["setuptools"]

        [tool.cibuildwheel]
        android.environment.ANDROID_API_LEVEL = "33"
        android.environment.PIP_EXTRA_INDEX_URL = "https://chaquo.com/pypi-13.1"
        """
    )
    project.generate(tmp_path)

    wheels = cibuildwheel_run(
        tmp_path,
        add_env={
            **cp313_env,
            # Verify that Android dependencies can be installed from the Chaquopy repository, and
            # that wheels tagged with an older version of Android (in this case 24) are still
            # accepted.
            "CIBW_TEST_REQUIRES": "bitarray==3.0.0",
            "CIBW_TEST_COMMAND": (
                "python -c 'from bitarray import bitarray; print(~bitarray(\"01100\"))'"
            ),
        },
    )
    assert wheels == [f"spam-0.1.0-cp313-cp313-android_33_{native_arch.android_abi}.whl"]
    assert "bitarray('10011')" in capfd.readouterr().out


@needs_emulator
def test_libcxx(tmp_path, capfd):
    project_dir = tmp_path / "project"
    output_dir = tmp_path / "output"

    # cibuildwheel should be able to run `patchelf` and `wheel` even when its
    # environment's `bin` directory is not on the PATH.
    non_venv_path = ":".join(
        item for item in os.environ["PATH"].split(":") if Path(item) != Path(sys.executable).parent
    )

    # A C++ package should include libc++, and the extension module should be able to
    # find it using DT_RUNPATH.
    new_c_project(setup_py_extension_args_add="language='c++'").generate(project_dir)
    script = 'import spam; print(", ".join(f"{s}: {spam.filter(s)}" for s in ["ham", "spam"]))'
    cp313_test_env = {
        **cp313_env,
        "CIBW_TEST_COMMAND": f"python -c '{script}'",
        "PATH": non_venv_path,
    }

    # Including external libraries requires API level 24.
    with pytest.raises(CalledProcessError):
        cibuildwheel_run(project_dir, add_env=cp313_test_env, output_dir=output_dir)
    assert "libc++_shared.so requires ANDROID_API_LEVEL to be at least 24" in capfd.readouterr().err

    wheels = cibuildwheel_run(
        project_dir,
        add_env={**cp313_test_env, "ANDROID_API_LEVEL": "24"},
        output_dir=output_dir,
    )
    assert len(wheels) == 1
    names = ZipFile(output_dir / wheels[0]).namelist()
    libcxx_names = [
        name for name in names if re.fullmatch(r"spam\.libs/libc\+\+_shared-[0-9a-f]{8}\.so", name)
    ]
    assert len(libcxx_names) == 1
    assert "ham: 1, spam: 0" in capfd.readouterr().out

    # A C package should not include libc++.
    rmtree(project_dir)
    rmtree(output_dir)
    new_c_project().generate(project_dir)
    wheels = cibuildwheel_run(project_dir, add_env=cp313_env, output_dir=output_dir)
    assert len(wheels) == 1
    for name in ZipFile(output_dir / wheels[0]).namelist():
        assert ".libs" not in name
