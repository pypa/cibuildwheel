import os

import utils


def test():
    project_dir = os.path.dirname(__file__)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': 'cp3?-*',
        'CIBW_SKIP': 'cp37-*',
    })

    # check that we got the right wheels. There should be no 2.7 or 3.7.
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if ('-cp3' in w) and ('-cp37' not in w)]
    assert set(actual_wheels) == set(expected_wheels)
