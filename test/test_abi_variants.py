import textwrap

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


def test_abi3(tmp_path):
    project_dir = tmp_path / "project"
    limited_api_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            # free_threaded, GraalPy, and PyPy do not have a Py_LIMITED_API equivalent, just build one of those
            # also limit the number of builds for test performance reasons
            "CIBW_BUILD": "cp39-* cp310-* pp310-* gp311_242-* cp312-* cp313t-*",
            "CIBW_ENABLE": "all",
        },
    )

    # check that the expected wheels are produced
    if utils.get_platform() == "pyodide":
        # there's only 1 possible configuration for pyodide, cp312. It builds
        # a wheel that is tagged abi3, compatible back to 3.10
        expected_wheels = utils.expected_wheels(
            "spam",
            "0.1.0",
            python_abi_tags=["cp310-abi3"],
        )
    else:
        expected_wheels = utils.expected_wheels(
            "spam",
            "0.1.0",
            python_abi_tags=[
                "cp39-cp39",
                "cp310-abi3",  # <-- ABI3, works with 3.10 and 3.12
                "cp313-cp313t",
                "pp310-pypy310_pp73",
                "graalpy311-graalpy242_311_native",
            ],
        )

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
        package_dir = {"": "src"},
        py_modules = ["ctypesexample.summing"],
        ext_modules=[
            CTypesExtension(
                "ctypesexample.csumlib",
                ["src/ctypesexample/csumlib.c"],
            ),
        ],
        cmdclass={'build_ext': build_ext, 'bdist_wheel': bdist_wheel_abi_none},
    )
    """
)
ctypes_project.files["src/ctypesexample/csumlib.c"] = textwrap.dedent(
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
ctypes_project.files["src/ctypesexample/summing.py"] = textwrap.dedent(
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

ctypes_project.files["pyproject.toml"] = pyproject_toml


def test_abi_none(tmp_path, capfd):
    project_dir = tmp_path / "project"
    ctypes_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_REQUIRES": "pytest",
            "CIBW_TEST_COMMAND": f"{utils.invoke_pytest()} {{project}}/test",
            # limit the number of builds for test performance reasons
            "CIBW_BUILD": "cp38-* cp{}{}-* cp313t-* pp310-*".format(*utils.SINGLE_PYTHON_VERSION),
            "CIBW_ENABLE": "all",
        },
    )

    expected_wheels = utils.expected_wheels("ctypesexample", "1.0.0", python_abi_tags=["py3-none"])
    # check that the expected wheels are produced
    assert set(actual_wheels) == set(expected_wheels)

    captured = capfd.readouterr()

    if utils.get_platform() == "pyodide":
        # pyodide builds a different platform tag for each python version, so
        # wheels are not reused
        assert "Found previously built wheel" not in captured.out
    else:
        # check that each wheel was built once, and reused
        assert "Building wheel..." in captured.out
        assert "Found previously built wheel" in captured.out
