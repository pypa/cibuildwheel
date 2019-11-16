import os
import sys 

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from shared import utils


def test(tmp_path):
    project_dir = os.path.dirname(__file__)

    # build the wheels
    utils.cibuildwheel_run(project_dir, add_env={
        # write python version information to a temporary file, this is
        # checked in setup.py
        'CIBW_BEFORE_BUILD': '''python -c "import sys; open('/tmp/pythonversion.txt', 'w').write(sys.version)" && python -c "import sys; open('/tmp/pythonexecutable.txt', 'w').write(sys.executable)"''',
        'CIBW_BEFORE_BUILD_WINDOWS': '''python -c "import sys; open('c:\\pythonversion.txt', 'w').write(sys.version)" && python -c "import sys; open('c:\\pythonexecutable.txt', 'w').write(sys.executable)"''',
    }, output_dir=tmp_path)
    
    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    actual_wheels = [x.name for x in tmp_path.iterdir()]
    assert set(actual_wheels) == set(expected_wheels)
