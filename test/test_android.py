import platform
from dataclasses import dataclass
from subprocess import CalledProcessError
from textwrap import dedent

import pytest

from .test_projects import new_c_project
from .utils import cibuildwheel_run

system_machine = (platform.system(), platform.machine())
if system_machine not in [("Linux", "x86_64"), ("Darwin", "arm64"), ("Darwin", "x86_64")]:
    pytest.skip(
        f"Android development tools are not available for {system_machine}",
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
other_arch = next(arch for arch in archs if arch != native_arch)


cp313_env = {
    "CIBW_PLATFORM": "android",
    "CIBW_BUILD": "cp313-*",
    "CIBW_TEST_SOURCES": "setup.cfg",  # Dummy file to ensure the variable is non-empty.
}


@pytest.mark.parametrize(
    ("frontend", "expected_success"),
    [("build", True), ("build[uv]", False), ("pip", False)],
)
def test_frontend(frontend, expected_success, tmp_path, capfd):
    new_c_project().generate(tmp_path)
    try:
        wheels = cibuildwheel_run(
            tmp_path,
            add_env={**cp313_env, "CIBW_BUILD_FRONTEND": frontend},
        )
    except CalledProcessError:
        if expected_success:
            pytest.fail("unexpected failure")
        assert "Android requires the build frontend to be 'build'" in capfd.readouterr().err
    else:
        if not expected_success:
            pytest.fail("unexpected success")
        assert wheels == [f"spam-0.1.0-cp313-cp313-android_21_{native_arch.android_abi}.whl"]


# Any tests which involve the testbed app must be run serially, because all copies of the testbed
# app run on the same emulator with the same application ID.
@pytest.mark.serial
def test_archs(tmp_path, capfd):
    new_c_project().generate(tmp_path)
    wheels = cibuildwheel_run(
        tmp_path,
        add_env={
            **cp313_env,
            "CIBW_ARCHS": "all",
            "CIBW_TEST_COMMAND": (
                'python -c \'import platform; print("machine" + "=" + platform.machine())\''
            ),
        },
    )
    assert wheels == [f"spam-0.1.0-cp313-cp313-android_21_{arch.android_abi}.whl" for arch in archs]

    # The native architecture should run tests.
    stdout, stderr = capfd.readouterr()
    machine_lines = [line for line in stdout.splitlines() if "machine=" in line]
    assert len(machine_lines) == 1
    assert machine_lines[0] == f"machine={native_arch.linux_machine}"

    # The non-native architecture should give a warning that it can't run tests.
    assert (
        f"warning: Skipping tests for {other_arch.android_abi}, as the build machine "
        f"only supports {native_arch.android_abi}"
    ) in stderr


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


@pytest.mark.serial
@pytest.mark.parametrize(
    ("command", "expected_success", "expected_output"),
    [
        # Success
        ("python -c 'import test_spam; test_spam.test_spam()'", True, "Spam test passed"),
        ("python -m pytest test_spam.py", True, "=== 1 passed in "),
        ("pytest test_spam.py", True, "=== 1 passed in "),
        # Build-time failure
        (
            "./test_spam.py",
            False,
            (
                "Test command './test_spam.py' is not supported on Android. "
                "Supported commands are 'python -m', 'python -c' and 'pytest'."
            ),
        ),
        # Runtime failure
        ("pytest test_ham.py", False, "not found: test_ham.py"),
    ],
)
def test_test_command(command, expected_success, expected_output, tmp_path, capfd):
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
    try:
        cibuildwheel_run(
            tmp_path,
            add_env={
                **cp313_env,
                "CIBW_TEST_SOURCES": "test_spam.py",
                "CIBW_TEST_REQUIRES": "pytest==8.3.5",
                "CIBW_TEST_COMMAND": command,
            },
        )
    except CalledProcessError:
        if expected_success:
            pytest.fail("unexpected failure")
        assert expected_output in capfd.readouterr().err
    else:
        if not expected_success:
            pytest.fail("unexpected success")
        assert expected_output in capfd.readouterr().out


@pytest.mark.serial
def test_no_test_sources(tmp_path, capfd):
    new_c_project().generate(tmp_path)
    with pytest.raises(CalledProcessError):
        cibuildwheel_run(
            tmp_path,
            add_env={
                **cp313_env,
                "CIBW_TEST_SOURCES": "",
                "CIBW_TEST_COMMAND": "python -c 'import sys'",
            },
        )
    assert "Testing on Android requires a definition of test-sources." in capfd.readouterr().err


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
            "CIBW_TEST_REQUIRES": "bitarray==3.0.0",
            "CIBW_TEST_COMMAND": (
                "python -c 'from bitarray import bitarray; print(~bitarray(\"01100\"))'"
            ),
        },
    )
    assert wheels == [f"spam-0.1.0-cp313-cp313-android_33_{native_arch.android_abi}.whl"]
    assert "bitarray('10011')" in capfd.readouterr().out
