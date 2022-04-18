import textwrap

from . import test_projects, utils

limited_api_project = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        cmdclass = {}
        extension_kwargs = {}
        if sys.version_info[:2] >= (3, 8):
            from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

            class bdist_wheel_abi3(_bdist_wheel):
                def finalize_options(self):
                    _bdist_wheel.finalize_options(self)
                    self.root_is_pure = False

                def get_tag(self):
                    python, abi, plat = _bdist_wheel.get_tag(self)
                    return python, "abi3", plat

            cmdclass["bdist_wheel"] = bdist_wheel_abi3
            extension_kwargs["define_macros"] = [("Py_LIMITED_API", "0x03080000")]
            extension_kwargs["py_limited_api"] = True
    """
    ),
    setup_py_extension_args_add="**extension_kwargs",
    setup_py_setup_args_add="cmdclass=cmdclass",
)


def test(tmp_path):
    project_dir = tmp_path / "project"
    limited_api_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_SKIP": "pp* ",  # PyPy does not have a Py_LIMITED_API equivalent
        },
    )

    # check that the expected wheels are produced
    expected_wheels = [
        w.replace("cp38-cp38", "cp38-abi3")
        for w in utils.expected_wheels("spam", "0.1.0")
        if "-pp" not in w and "-cp39" not in w and "-cp310" not in w
    ]
    assert set(actual_wheels) == set(expected_wheels)
