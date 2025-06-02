import os
import platform
import re
from dataclasses import dataclass
from subprocess import CalledProcessError
from textwrap import dedent

import pytest

from .test_projects import new_c_project
from .utils import cibuildwheel_run, expected_wheels

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

if "ANDROID_HOME" not in os.environ:
    pytest.skip(
        "ANDROID_HOME environment variable is not set",
        allow_module_level=True,
    )


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


def test_frontend_good(tmp_path):
    new_c_project().generate(tmp_path)
    wheels = cibuildwheel_run(
        tmp_path,
        add_env={**cp313_env, "CIBW_BUILD_FRONTEND": "build"},
    )
    assert wheels == [f"spam-0.1.0-cp313-cp313-android_21_{native_arch.android_abi}.whl"]


@pytest.mark.parametrize("frontend", ["build[uv]", "pip"])
def test_frontend_bad(frontend, tmp_path, capfd):
    new_c_project().generate(tmp_path)
    with pytest.raises(CalledProcessError):
        cibuildwheel_run(
            tmp_path,
            add_env={**cp313_env, "CIBW_BUILD_FRONTEND": frontend},
        )
    assert "Android requires the build frontend to be 'build'" in capfd.readouterr().err


def test_expected_wheels(tmp_path):
    new_c_project().generate(tmp_path)
    wheels = cibuildwheel_run(tmp_path, add_env={"CIBW_PLATFORM": "android"})
    assert wheels == expected_wheels(
        "spam", "0.1.0", platform="android", machine_arch=native_arch.android_abi
    )


# Any tests which involve the testbed app must be run serially, because all copies of the testbed
# app run on the same emulator with the same application ID.
@pytest.mark.serial
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
                f"warning: Skipping tests for {arch.android_abi}, as the build machine "
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
    project.generate(tmp_path)

    return {
        **cp313_env,
        "CIBW_TEST_SOURCES": "test_spam.py",
        "CIBW_TEST_REQUIRES": "pytest==8.3.5",
    }


@pytest.mark.serial
@pytest.mark.parametrize(
    ("command", "expected_output"),
    [
        ("python -c 'import test_spam; test_spam.test_spam()'", "Spam test passed"),
        ("python -m pytest test_spam.py", "=== 1 passed in "),
        ("pytest test_spam.py", "=== 1 passed in "),
    ],
)
def test_test_command_good(command, expected_output, tmp_path, spam_env, capfd):
    cibuildwheel_run(tmp_path, add_env={**spam_env, "CIBW_TEST_COMMAND": command})
    assert expected_output in capfd.readouterr().out


@pytest.mark.serial
@pytest.mark.parametrize(
    ("command", "expected_output"),
    [
        # Build-time failure
        (
            "./test_spam.py",
            "Test command './test_spam.py' is not supported on Android. "
            "Supported commands are 'python -m', 'python -c' and 'pytest'.",
        ),
        # Runtime failure
        ("pytest test_ham.py", "not found: test_ham.py"),
        (
            "pytest {project}",
            "Test command 'pytest {project}' with a '{project}' or '{package}' "
            "placeholder is not supported on Android",
        ),
        (
            "pytest {package}",
            "Test command 'pytest {package}' with a '{project}' or '{package}' "
            "placeholder is not supported on Android",
        ),
    ],
)
def test_test_command_bad(command, expected_output, tmp_path, spam_env, capfd):
    with pytest.raises(CalledProcessError):
        cibuildwheel_run(tmp_path, add_env={**spam_env, "CIBW_TEST_COMMAND": command})
    assert expected_output in capfd.readouterr().err


@pytest.mark.serial
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


@pytest.mark.serial
def test_api_level(tmp_path, capfd):
    new_c_project().generate(tmp_path)
    wheels = cibuildwheel_run(
        tmp_path,
        add_env={
            **cp313_env,
            "ANDROID_API_LEVEL": "33",
            # Verify that Android dependencies can be installed from the Chaquopy repository, and
            # that wheels tagged with an older version of Android (in this case 24) are still
            # accepted.
            "CIBW_ENVIRONMENT": "PIP_EXTRA_INDEX_URL=https://chaquo.com/pypi-13.1",
            "CIBW_TEST_REQUIRES": "bitarray==3.0.0",
            "CIBW_TEST_COMMAND": (
                "python -c 'from bitarray import bitarray; print(~bitarray(\"01100\"))'"
            ),
        },
    )
    assert wheels == [f"spam-0.1.0-cp313-cp313-android_33_{native_arch.android_abi}.whl"]
    assert "bitarray('10011')" in capfd.readouterr().out
