from __future__ import annotations

import platform
import textwrap

import pytest

from . import test_projects, utils

# TODO: specify these at runtime according to manylinux_image
project_with_manylinux_symbols = test_projects.new_c_project(
    spam_c_top_level_add=textwrap.dedent(
        r"""
        #include <malloc.h>
        #include <stdlib.h>
        #include <stdint.h>
        #include <math.h>

        #if !defined(__GLIBC_PREREQ)
        #error "Must run on a glibc linux environment"
        #endif

        #if !__GLIBC_PREREQ(2, 5)  /* manylinux1 is glibc 2.5 */
        #error "Must run on a glibc >= 2.5 linux environment"
        #endif

        #if __GLIBC_PREREQ(2, 28)
        #include <threads.h>
        #endif
        """
    ),
    spam_c_function_add=textwrap.dedent(
        r"""
        #if __GLIBC_PREREQ(2, 28)
            // thrd_equal & thrd_current are only available in manylinux_2_28+
            sts = thrd_equal(thrd_current(), thrd_current()) ? 0 : 1;;
        #elif __GLIBC_PREREQ(2, 24)
            // nextupf is only available in manylinux_2_24+
            sts = (int)nextupf(0.0F);
        #elif __GLIBC_PREREQ(2, 17)  /* manylinux2014 is glibc 2.17 */
            // secure_getenv is only available in manylinux2014+
            sts = (int)(intptr_t)secure_getenv("NON_EXISTING_ENV_VARIABLE");
        #elif __GLIBC_PREREQ(2, 10)  /* manylinux2010 is glibc 2.12 */
            // malloc_info is only available on manylinux2010+
            sts = malloc_info(0, stdout);
        #endif
        """
    ),
)


@pytest.mark.parametrize(
    "manylinux_image",
    ["manylinux1", "manylinux2010", "manylinux2014", "manylinux_2_24", "manylinux_2_28"],
)
def test(manylinux_image, tmp_path):
    if utils.platform != "linux":
        pytest.skip("the container image test is only relevant to the linux build")
    elif platform.machine() not in ["x86_64", "i686"]:
        if manylinux_image in ["manylinux1", "manylinux2010"]:
            pytest.skip("manylinux1 and 2010 doesn't exist for non-x86 architectures")
    elif manylinux_image == "manylinux_2_28" and platform.machine() == "i686":
        pytest.skip("manylinux_2_28 doesn't exist for i686 architecture")

    project_dir = tmp_path / "project"
    project_with_manylinux_symbols.generate(project_dir)

    # build the wheels
    # CFLAGS environment variable is necessary to fail on 'malloc_info' (on manylinux1) during compilation/linking,
    # rather than when dynamically loading the Python
    add_env = {
        "CIBW_BUILD": "*-manylinux*",
        "CIBW_ENVIRONMENT": 'CFLAGS="$CFLAGS -O0 -Werror=implicit-function-declaration"',
        "CIBW_MANYLINUX_X86_64_IMAGE": manylinux_image,
        "CIBW_MANYLINUX_I686_IMAGE": manylinux_image,
        "CIBW_MANYLINUX_PYPY_X86_64_IMAGE": manylinux_image,
        "CIBW_MANYLINUX_AARCH64_IMAGE": manylinux_image,
        "CIBW_MANYLINUX_PPC64LE_IMAGE": manylinux_image,
        "CIBW_MANYLINUX_S390X_IMAGE": manylinux_image,
        "CIBW_MANYLINUX_PYPY_AARCH64_IMAGE": manylinux_image,
        "CIBW_MANYLINUX_PYPY_I686_IMAGE": manylinux_image,
    }
    if manylinux_image in {"manylinux1"}:
        # We don't have a manylinux1 image for PyPy & CPython 3.10 and above
        add_env["CIBW_SKIP"] = "pp* cp31*"
    if manylinux_image in {"manylinux2010"}:
        # We don't have a manylinux2010 image for PyPy 3.9, CPython 3.11
        add_env["CIBW_SKIP"] = "pp39* cp311*"
    if manylinux_image == "manylinux_2_28" and platform.machine() == "x86_64":
        # We don't have a manylinux_2_28 image for i686
        add_env["CIBW_ARCHS"] = "x86_64"

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)

    platform_tag_map = {
        "manylinux1": ["manylinux_2_5", "manylinux1"],
        "manylinux2010": ["manylinux_2_12", "manylinux2010"],
        "manylinux2014": ["manylinux_2_17", "manylinux2014"],
    }
    expected_wheels = utils.expected_wheels(
        "spam",
        "0.1.0",
        manylinux_versions=platform_tag_map.get(manylinux_image, [manylinux_image]),
        musllinux_versions=[],
    )
    if manylinux_image in {"manylinux1"}:
        # remove PyPy & CPython 3.10 and above
        expected_wheels = [w for w in expected_wheels if "-pp" not in w and "-cp31" not in w]

    if manylinux_image in {"manylinux2010"}:
        # remove PyPy 3.9 & CPython 3.11
        expected_wheels = [w for w in expected_wheels if "-pp39" not in w and "-cp311" not in w]

    if manylinux_image == "manylinux_2_28" and platform.machine() == "x86_64":
        # We don't have a manylinux_2_28 image for i686
        expected_wheels = [w for w in expected_wheels if "i686" not in w]

    assert set(actual_wheels) == set(expected_wheels)
