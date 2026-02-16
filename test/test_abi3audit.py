import subprocess
import textwrap

import pytest

from . import test_projects, utils

pyproject_toml = r"""
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
"""

limited_api_project = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import sysconfig

        IS_CPYTHON = sys.implementation.name == "cpython"
        Py_GIL_DISABLED = sysconfig.get_config_var("Py_GIL_DISABLED")
        CAN_USE_ABI3 = IS_CPYTHON and not Py_GIL_DISABLED
        setup_options = {}
        extension_kwargs = {}
        if CAN_USE_ABI3 and sys.version_info[:2] >= (3, 10):
            extension_kwargs["define_macros"] = [("Py_LIMITED_API", "0x030A0000")]
            extension_kwargs["py_limited_api"] = True
            setup_options = {"bdist_wheel": {"py_limited_api": "cp310"}}
    """
    ),
    setup_py_extension_args_add="**extension_kwargs",
    setup_py_setup_args_add="options=setup_options",
)

limited_api_project.files["pyproject.toml"] = pyproject_toml

# Project that claims abi3 but violates the stable ABI by calling
# PyUnicode_AsUTF8 (not in stable ABI until 3.13) without defining
# Py_LIMITED_API in the C code.
violating_abi3_project = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import sysconfig

        IS_CPYTHON = sys.implementation.name == "cpython"
        Py_GIL_DISABLED = sysconfig.get_config_var("Py_GIL_DISABLED")
        CAN_USE_ABI3 = IS_CPYTHON and not Py_GIL_DISABLED
        setup_options = {}
        extension_kwargs = {}
        if CAN_USE_ABI3 and sys.version_info[:2] >= (3, 10):
            # Intentionally NOT defining Py_LIMITED_API as a C macro,
            # but still tagging the wheel as abi3.
            extension_kwargs["py_limited_api"] = True
            setup_options = {"bdist_wheel": {"py_limited_api": "cp310"}}
    """
    ),
    spam_c_function_add=textwrap.dedent(
        r"""
        // Call a function not in the stable ABI until Python 3.13.
        // Without Py_LIMITED_API defined, the compiler allows it.
        PyObject *str_obj = PyUnicode_FromString(content);
        const char *utf8 = PyUnicode_AsUTF8(str_obj);
        (void)utf8;
        Py_DECREF(str_obj);
    """
    ),
    setup_py_extension_args_add="**extension_kwargs",
    setup_py_setup_args_add="options=setup_options",
)

violating_abi3_project.files["pyproject.toml"] = pyproject_toml


def test_abi3audit_runs_on_abi3_wheel(tmp_path, capfd):
    """Test that abi3audit runs automatically on abi3 wheels."""
    project_dir = tmp_path / "project"
    limited_api_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            # Let's only build one cpython version to keep the test fast.
            "CIBW_BUILD": "cp310-*",
            "CIBW_ARCHS": "native",
        },
    )

    assert len(actual_wheels) >= 1

    captured = capfd.readouterr()
    assert "Running abi3audit" in captured.out


def test_abi3audit_skipped_for_non_abi3_wheel(tmp_path, capfd):
    """Test that abi3audit does not run for non-abi3 wheels."""
    project_dir = tmp_path / "project"
    basic_project = test_projects.new_c_project()
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_ARCHS": "native",
        },
        single_python=True,
    )

    assert len(actual_wheels) >= 1

    captured = capfd.readouterr()
    assert "Running abi3audit" not in captured.out


def test_abi3audit_detects_violation(tmp_path, capfd):
    """Test that abi3audit catches stable ABI violations and fails the build.

    This project tags the wheel as cp310-abi3 but uses PyUnicode_AsUTF8,
    which was not part of the stable ABI until Python 3.13.
    """
    project_dir = tmp_path / "project"
    violating_abi3_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_BUILD": "cp310-*",
                "CIBW_ARCHS": "native",
            },
        )

    captured = capfd.readouterr()
    assert "Running abi3audit" in captured.out
