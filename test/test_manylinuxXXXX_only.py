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
        #include <pthread.h>

        #if !defined(__GLIBC_PREREQ)
        #error "Must run on a glibc linux environment"
        #endif

        #if !__GLIBC_PREREQ(2, 17)  /* manylinux2014 is glibc 2.17 */
        #error "Must run on a glibc >= 2.5 linux environment"
        #endif

        #if __GLIBC_PREREQ(2, 28)
        #include <threads.h>
        #endif
        """
    ),
    spam_c_function_add=textwrap.dedent(
        r"""
        #if __GLIBC_PREREQ(2, 34)
            // pthread_mutexattr_init was moved to libc.so.6 in manylinux_2_34+
            pthread_mutexattr_t attr;
            sts = pthread_mutexattr_init(&attr);
            if (sts == 0) {
                pthread_mutexattr_destroy(&attr);
            }
        #elif __GLIBC_PREREQ(2, 28)
            // thrd_equal & thrd_current are only available in manylinux_2_28+
            sts = thrd_equal(thrd_current(), thrd_current()) ? 0 : 1;
        #elif __GLIBC_PREREQ(2, 24)
            // nextupf is only available in manylinux_2_24+
            sts = (int)nextupf(0.0F);
        #elif __GLIBC_PREREQ(2, 17)  /* manylinux2014 is glibc 2.17 */
            // secure_getenv is only available in manylinux2014+
            sts = (int)(intptr_t)secure_getenv("NON_EXISTING_ENV_VARIABLE");
        #endif
        """
    ),
)


@pytest.mark.parametrize(
    "manylinux_image",
    [
        "manylinux2014",
        "manylinux_2_28",
        "manylinux_2_34",
    ],
)
@pytest.mark.usefixtures("docker_cleanup")
def test(manylinux_image, tmp_path):
    if utils.get_platform() != "linux":
        pytest.skip("the container image test is only relevant to the linux build")
    elif manylinux_image in {"manylinux_2_28", "manylinux_2_34"} and platform.machine() == "i686":
        pytest.skip(f"{manylinux_image} doesn't exist for i686 architecture")

    project_dir = tmp_path / "project"
    project_with_manylinux_symbols.generate(project_dir)

    # build the wheels
    # CFLAGS environment variable is necessary to fail at build time,
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
    if manylinux_image in {"manylinux_2_28", "manylinux_2_34"} and platform.machine() == "x86_64":
        # We don't have a manylinux_2_28+ image for i686
        add_env["CIBW_ARCHS"] = "x86_64"
    if platform.machine() == "aarch64":
        # We just have a manylinux_2_31 image for armv7l
        add_env["CIBW_ARCHS"] = "aarch64"

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)

    platform_tag_map = {
        "manylinux2014": ["manylinux2014", "manylinux_2_17"],
    }
    expected_wheels = utils.expected_wheels(
        "spam",
        "0.1.0",
        manylinux_versions=platform_tag_map.get(manylinux_image, [manylinux_image]),
        musllinux_versions=[],
    )

    if manylinux_image in {"manylinux_2_28", "manylinux_2_34"} and platform.machine() == "x86_64":
        # We don't have a manylinux_2_28+ image for i686
        expected_wheels = [w for w in expected_wheels if "i686" not in w]

    if platform.machine() == "aarch64":
        # We just have a manylinux_2_31 image for armv7l
        expected_wheels = [w for w in expected_wheels if "armv7l" not in w]

    assert set(actual_wheels) == set(expected_wheels)
