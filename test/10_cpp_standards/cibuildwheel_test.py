import os
import sys 

import pytest

import utils


def test_cpp11(tmp_path):
    add_env = {"CIBW_SKIP": "cp27-win*", "CIBW_ENVIRONMENT": "STANDARD=11"}
    # VC for python 2.7 do not support modern standards
    if utils.platform == "macos":
        add_env["MACOSX_DEPLOYMENT_TARGET"] = "10.9"
    project_dir = os.path.dirname(__file__)
    # this test checks if c++11 standard is supported.

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [x for x in utils.expected_wheels('spam', '0.1.0',
                       macosx_deployment_target="10.9") if "cp27-cp27m-win" not in x]
    assert set(actual_wheels) == set(expected_wheels)


def test_cpp14():
    add_env = {"CIBW_SKIP": "cp27-win* cp35-win*", "CIBW_ENVIRONMENT": "STANDARD=14"}
    # VC for python 2.7 do not support modern standards
    # manylinux1 docker image do not support compilers with standards newer than c++11
    # python 3.4 and 3.5 are compiled with MSVC 10. which not support c++14
    if utils.platform == "macos":
        add_env["MACOSX_DEPLOYMENT_TARGET"] = "10.9"
    project_dir = os.path.dirname(__file__)
    # this test checks if c++14 standard is supported.

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [x for x in utils.expected_wheels(
                       'spam', '0.1.0', macosx_deployment_target="10.9")
                       if "cp27-cp27m-win" not in x and "cp35-cp35m-win" not in x]
    assert set(actual_wheels) == set(expected_wheels)

def test_cpp17():
    # python 2.7 use `register` keyword which is forbidden in c++17 standard 
    # manylinux1 docker image do not support compilers with standards newer than c++11
    # python 3.4 and 3.5 are compiled with MSVC 10. which not support c++17
    if os.environ.get("APPVEYOR_BUILD_WORKER_IMAGE", "") == "Visual Studio 2015":
        pytest.skip("Visual Studio 2015 does not support c++17")

    add_env = {"CIBW_SKIP": "cp27-win* cp35-win*", "CIBW_ENVIRONMENT": "STANDARD=17"}
    if utils.platform == "macos":
        add_env["MACOSX_DEPLOYMENT_TARGET"] = "10.13"

    project_dir = os.path.dirname(__file__)
    # this test checks if c++17 standard is supported.

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [x for x in utils.expected_wheels('spam', '0.1.0',
                       macosx_deployment_target="10.13") 
                       if "cp27-cp27m-win" not in x and "cp35-cp35m-win" not in x]
    assert set(actual_wheels) == set(expected_wheels)

