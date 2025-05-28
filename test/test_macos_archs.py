import platform

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()
basic_project.files["tests/test_suite.py"] = r"""
import platform
print("running tests on " + platform.machine())
"""


ALL_MACOS_WHEELS = {
    *utils.expected_wheels("spam", "0.1.0", machine_arch="x86_64"),
    *utils.expected_wheels("spam", "0.1.0", machine_arch="arm64", include_universal2=True),
}

DEPLOYMENT_TARGET_TOO_LOW_WARNING = "Bumping MACOSX_DEPLOYMENT_TARGET"


def test_cross_compiled_build(tmp_path):
    if utils.get_platform() != "macos":
        pytest.skip("this test is only relevant to macos")
    if utils.get_xcode_version() < (12, 2):
        pytest.skip("this test only works with Xcode 12.2 or greater")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={"CIBW_ARCHS": "x86_64, universal2, arm64"},
        single_python=True,
    )
    python_tag = "cp{}{}".format(*utils.SINGLE_PYTHON_VERSION)
    expected_wheels = [w for w in ALL_MACOS_WHEELS if python_tag in w]
    assert set(actual_wheels) == set(expected_wheels)


@pytest.mark.parametrize("build_universal2", [False, True])
@pytest.mark.parametrize(
    "test_config",
    [
        {
            "CIBW_TEST_COMMAND": '''python -c "import platform; print('running tests on ' + platform.machine())"''',
        },
        {
            "CIBW_TEST_COMMAND": "python tests/test_suite.py",
            "CIBW_TEST_SOURCES": "tests",
        },
    ],
)
def test_cross_compiled_test(tmp_path, capfd, build_universal2, test_config):
    if utils.get_platform() != "macos":
        pytest.skip("this test is only relevant to macos")
    if utils.get_xcode_version() < (12, 2):
        pytest.skip("this test only works with Xcode 12.2 or greater")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp310-*" if build_universal2 else "*p310-*",
            "CIBW_ARCHS": "universal2" if build_universal2 else "x86_64 arm64",
            "CIBW_BUILD_VERBOSITY": "3",
            **test_config,
        },
    )

    captured = capfd.readouterr()

    assert DEPLOYMENT_TARGET_TOO_LOW_WARNING not in captured.err

    platform_machine = platform.machine()
    if platform_machine == "x86_64":
        # ensure that tests were run on only x86_64
        assert "running tests on x86_64" in captured.out
        assert "running tests on arm64" not in captured.out
        if build_universal2:
            assert (
                "While universal2 wheels can be built on x86_64, the arm64 part of the wheel cannot be tested"
                in captured.err
            )
        else:
            assert (
                "While arm64 wheels can be built on x86_64, they cannot be tested" in captured.err
            )
    elif platform_machine == "arm64":
        # ensure that tests were run on both x86_64 and arm64
        assert "running tests on x86_64" in captured.out
        assert "running tests on arm64" in captured.out
        assert (
            "While universal2 wheels can be built on x86_64, the arm64 part of the wheel cannot be tested"
            not in captured.err
        )
        assert (
            "While arm64 wheels can be built on x86_64, they cannot be tested" not in captured.err
        )

    if build_universal2:
        expected_wheels = [w for w in ALL_MACOS_WHEELS if "cp310" in w and "universal2" in w]
    else:
        expected_wheels = [w for w in ALL_MACOS_WHEELS if "p310-" in w and "universal2" not in w]
        if platform_machine == "x86_64":
            expected_wheels = [w for w in expected_wheels if not ("pp310" in w and "arm64" in w)]

    assert set(actual_wheels) == set(expected_wheels)


def test_deployment_target_warning_is_firing(tmp_path, capfd):
    # force the warning to check that we can detect it if it happens
    if utils.get_platform() != "macos":
        pytest.skip("this test is only relevant to macos")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_ARCHS": "x86_64",
            "MACOSX_DEPLOYMENT_TARGET": "10.8",
            "CIBW_BUILD_VERBOSITY": "3",
        },
        single_python=True,
    )

    captured = capfd.readouterr()
    assert DEPLOYMENT_TARGET_TOO_LOW_WARNING in captured.err


@pytest.mark.parametrize("skip_arm64_test", [False, True])
def test_universal2_testing_on_x86_64(tmp_path, capfd, skip_arm64_test):
    if utils.get_platform() != "macos":
        pytest.skip("this test is only relevant to macos")
    if utils.get_xcode_version() < (12, 2):
        pytest.skip("this test only works with Xcode 12.2 or greater")
    if platform.machine() != "x86_64":
        pytest.skip("this test only works on x86_64")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_COMMAND": '''python -c "import platform; print('running tests on ' + platform.machine())"''',
            "CIBW_ARCHS": "universal2",
            "CIBW_TEST_SKIP": "*_universal2:arm64" if skip_arm64_test else "",
        },
        single_python=True,
    )

    captured = capfd.readouterr()

    if platform.machine() == "x86_64":
        assert "running tests on x86_64" in captured.out
        assert "running tests on arm64" not in captured.out

        warning_message = "While universal2 wheels can be built on x86_64, the arm64 part of the wheel cannot be tested"
        if skip_arm64_test:
            assert warning_message not in captured.err
        else:
            assert warning_message in captured.err

    python_tag = "cp{}{}".format(*utils.SINGLE_PYTHON_VERSION)
    expected_wheels = [w for w in ALL_MACOS_WHEELS if python_tag in w and "universal2" in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_universal2_testing_on_arm64(build_frontend_env, tmp_path, capfd):
    # cibuildwheel should test the universal2 wheel on both x86_64 and arm64, when run on arm64
    if utils.get_platform() != "macos":
        pytest.skip("this test is only relevant to macos")
    if platform.machine() != "arm64":
        pytest.skip("this test only works on arm64")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_ARCHS": "universal2",
            # check that a native dependency is correctly installed, once per each testing arch
            "CIBW_TEST_REQUIRES": "--only-binary :all: pillow>=10.3",  # pillow>=10.3 provides wheels for macOS 10.10, not 10.9
            "CIBW_TEST_COMMAND": '''python -c "import PIL, platform; print(f'running tests on {platform.machine()} with pillow {PIL.__version__}')"''',
            **build_frontend_env,
        },
        single_python=True,
    )

    captured = capfd.readouterr()
    assert "running tests on arm64 with pillow" in captured.out
    assert "running tests on x86_64 with pillow" in captured.out

    python_tag = "cp{}{}".format(*utils.SINGLE_PYTHON_VERSION)
    expected_wheels = [w for w in ALL_MACOS_WHEELS if python_tag in w and "universal2" in w]
    assert set(actual_wheels) == set(expected_wheels)


def test_cp38_arm64_testing(tmp_path, capfd, request):
    if utils.get_platform() != "macos":
        pytest.skip("this test is only relevant to macos")
    if utils.get_xcode_version() < (12, 2):
        pytest.skip("this test only works with Xcode 12.2 or greater")
    if platform.machine() != "arm64":
        pytest.skip("this test only works on arm64")
    if request.config.getoption("--run-cp38-universal2"):
        pytest.skip("--run-cp38-universal2 option skips this test")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp38-*",
            "CIBW_TEST_COMMAND": '''python -c "import platform; print('running tests on ' + platform.machine())"''',
            "CIBW_ARCHS": "x86_64,universal2,arm64",
        },
    )

    captured = capfd.readouterr()

    assert "running tests on x86_64" in captured.out
    assert "running tests on arm64" not in captured.out

    warning_message = "While cibuildwheel can build CPython 3.8 universal2/arm64 wheels, we cannot test the arm64 part of them"
    assert warning_message in captured.err

    expected_wheels = [w for w in ALL_MACOS_WHEELS if "cp38" in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_cp38_arm64_testing_universal2_installer(tmp_path, capfd, request):
    if not request.config.getoption("--run-cp38-universal2"):
        pytest.skip("needs --run-cp38-universal2 option to run")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp38-*",
            "CIBW_TEST_COMMAND": '''python -c "import platform; print('running tests on ' + platform.machine())"''',
            "CIBW_ARCHS": "x86_64,universal2,arm64",
            "MACOSX_DEPLOYMENT_TARGET": "11.0",
        },
    )

    captured = capfd.readouterr()

    assert "running tests on x86_64" in captured.out
    assert "running tests on arm64" in captured.out

    warning_message = "While cibuildwheel can build CPython 3.8 universal2/arm64 wheels, we cannot test the arm64 part of them"
    assert warning_message not in captured.err

    expected_wheels = [w.replace("10_9", "11_0") for w in ALL_MACOS_WHEELS if "cp38" in w]

    assert set(actual_wheels) == set(expected_wheels)
