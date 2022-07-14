from __future__ import annotations

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


def test_abi3(tmp_path):
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
        if "-pp" not in w and "-cp39" not in w and "-cp310" not in w and "-cp311" not in w
    ]
    assert set(actual_wheels) == set(expected_wheels)


ctypes_project = test_projects.TestProject()
ctypes_project.files["setup.py"] = textwrap.dedent(
    """
    from setuptools import setup, Extension

    from distutils.command.build_ext import build_ext as _build_ext
    class CTypesExtension(Extension): pass
    class build_ext(_build_ext):
        def build_extension(self, ext):
            self._ctypes = isinstance(ext, CTypesExtension)
            return super().build_extension(ext)

        def get_export_symbols(self, ext):
            if self._ctypes:
                return ext.export_symbols
            return super().get_export_symbols(ext)

        def get_ext_filename(self, ext_name):
            if self._ctypes:
                return ext_name + '.so'
            return super().get_ext_filename(ext_name)

    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
    class bdist_wheel_abi_none(_bdist_wheel):
        def finalize_options(self):
            _bdist_wheel.finalize_options(self)
            self.root_is_pure = False

        def get_tag(self):
            python, abi, plat = _bdist_wheel.get_tag(self)
            return "py3", "none", plat

    setup(
        name="ctypesexample",
        version="1.0.0",
        py_modules = ["ctypesexample.summing"],
        ext_modules=[
            CTypesExtension(
                "ctypesexample.csumlib",
                ["ctypesexample/csumlib.c"],
            ),
        ],
        cmdclass={'build_ext': build_ext, 'bdist_wheel': bdist_wheel_abi_none},
    )
    """
)
ctypes_project.files["ctypesexample/csumlib.c"] = textwrap.dedent(
    """
    #ifdef _WIN32
    #define LIBRARY_API __declspec(dllexport)
    #else
    #define LIBRARY_API
    #endif

    #include <stdlib.h>


    LIBRARY_API double *add_vec3(double *a, double *b)
    {
        double *res = malloc(sizeof(double) * 3);

        for (int i = 0; i < 3; ++i)
        {
            res[i] = a[i] + b[i];
        }

        return res;
    }
    """
)
ctypes_project.files["ctypesexample/summing.py"] = textwrap.dedent(
    """
    import ctypes
    import pathlib

    # path of the shared library
    libfile = pathlib.Path(__file__).parent / "csumlib.so"
    csumlib = ctypes.CDLL(str(libfile))

    type_vec3 = ctypes.POINTER(ctypes.c_double * 3)

    csumlib.add_vec3.restype = type_vec3
    csumlib.add_vec3.argtypes = [type_vec3, type_vec3]
    def add(a: list, b: list) -> list:
        a_p = (ctypes.c_double * 3)(*a)
        b_p = (ctypes.c_double * 3)(*b)
        r_p = csumlib.add_vec3(a_p,b_p)

        return [l for l in r_p.contents]
    """
)

ctypes_project.files["test/add_test.py"] = textwrap.dedent(
    """
    import ctypesexample.summing

    def test():
        a = [1, 2, 3]
        b = [4, 5, 6]
        assert ctypesexample.summing.add(a, b) == [5, 7, 9]
    """
)


def test_abi_none(tmp_path, capfd):
    project_dir = tmp_path / "project"
    ctypes_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_REQUIRES": "pytest",
            "CIBW_TEST_COMMAND": "pytest {project}/test",
            # limit the number of builds for test performance reasons
            "CIBW_BUILD": "cp38-* cp310-* pp39-*",
        },
    )

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("ctypesexample", "1.0.0", python_abi_tags=["py3-none"])
    assert set(actual_wheels) == set(expected_wheels)

    # check that each wheel was built once, and reused
    captured = capfd.readouterr()
    assert "Building wheel..." in captured.out
    assert "Found previously built wheel" in captured.out
