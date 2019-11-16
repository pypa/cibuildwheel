import os
import sys 

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from shared import utils


def test(tmp_path):
    project_dir = os.path.dirname(__file__)

    # build the wheels
    utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': 'cp3?-*',
        'CIBW_SKIP': 'cp37-*',
    }, output_dir=tmp_path)

    # check that we got the right wheels. There should be no 2.7 or 3.7.
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if ('-cp3' in w) and ('-cp37' not in w)]
    actual_wheels = [x.name for x in tmp_path.iterdir()]
    assert set(actual_wheels) == set(expected_wheels)
