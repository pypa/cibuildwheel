import os, pytest, textwrap
from . import utils
from .template_projects import CTemplateProject


dockcross_only_project = CTemplateProject(
    setup_py_add=textwrap.dedent(r'''
        import os, sys

        # check that we're running in the correct docker image as specified in the
        # environment options CIBW_MANYLINUX1_*_IMAGE
        if "linux" in sys.platform and not os.path.exists("/dockcross"):
            raise Exception(
                "/dockcross directory not found. Is this test running in the correct docker image?"
            )
    ''')
)

def test(tmpdir):
    if utils.platform != "linux":
        pytest.skip("the test is only relevant to the linux build")

    project_dir = str(tmpdir)
    dockcross_only_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_MANYLINUX_X86_64_IMAGE": "dockcross/manylinux2010-x64",
            "CIBW_MANYLINUX_I686_IMAGE": "dockcross/manylinux1-x86",
            "CIBW_BEFORE_BUILD": "/opt/python/cp36-cp36m/bin/pip install -U auditwheel",  # Currently necessary on dockcross images to get auditwheel 2.1 supporting AUDITWHEEL_PLAT
            "CIBW_ENVIRONMENT": 'AUDITWHEEL_PLAT=`if [ $(uname -i) == "x86_64" ]; then echo "manylinux2010_x86_64"; else echo "manylinux1_i686"; fi`',
        },
    )

    # also check that we got the right wheels built
    expected_wheels = [
        w
        for w in utils.expected_wheels("spam", "0.1.0")
        if "-manylinux2010_i686" not in w
    ]
    assert set(actual_wheels) == set(expected_wheels)
