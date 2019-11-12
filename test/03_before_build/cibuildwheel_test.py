import os

import utils


def test():
    project_dir = os.path.dirname(__file__)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        # write python version information to a temporary file, this is
        # checked in setup.py
        'CIBW_BEFORE_BUILD': '''python -c "import sys; open('/tmp/pythonversion.txt', 'w').write(sys.version)" && python -c "import sys; open('/tmp/pythonexecutable.txt', 'w').write(sys.executable)"''',
        'CIBW_BEFORE_BUILD_WINDOWS': '''python -c "import sys; open('c:\\pythonversion.txt', 'w').write(sys.version)" && python -c "import sys; open('c:\\pythonexecutable.txt', 'w').write(sys.executable)"''',
    })

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)
