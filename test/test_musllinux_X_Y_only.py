from __future__ import annotations

import textwrap

import pytest

from . import test_projects, utils

project_with_manylinux_symbols = test_projects.new_c_project(
    spam_c_top_level_add=textwrap.dedent(
        r"""
        #include <stdlib.h>

        #if defined(__GLIBC_PREREQ)
        #error "Must not run on a glibc linux environment"
        #endif
        """
    ),
    spam_c_function_add=textwrap.dedent(
        r"""
        sts = 0;
        """
    ),
)


@pytest.mark.parametrize(
    "musllinux_image",
    ["musllinux_1_1", "musllinux_1_2"],
)
@pytest.mark.usefixtures("docker_cleanup")
def test(musllinux_image, tmp_path):
    if utils.platform != "linux":
        pytest.skip("the container image test is only relevant to the linux build")

    project_dir = tmp_path / "project"
    project_with_manylinux_symbols.generate(project_dir)

    # build the wheels
    add_env = {
        "CIBW_BUILD": "*-musllinux*",
        "CIBW_MUSLLINUX_X86_64_IMAGE": musllinux_image,
        "CIBW_MUSLLINUX_I686_IMAGE": musllinux_image,
        "CIBW_MUSLLINUX_AARCH64_IMAGE": musllinux_image,
        "CIBW_MUSLLINUX_PPC64LE_IMAGE": musllinux_image,
        "CIBW_MUSLLINUX_S390X_IMAGE": musllinux_image,
    }

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = utils.expected_wheels(
        "spam",
        "0.1.0",
        manylinux_versions=[],
        musllinux_versions=[musllinux_image],
    )
    assert set(actual_wheels) == set(expected_wheels)
