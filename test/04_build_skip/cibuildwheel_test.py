import os
import utils

def test():
    project_dir = os.path.dirname(__file__)

    # build the wheels
    utils.run_cibuildwheel(project_dir, add_env={
        'CIBW_BUILD': 'cp3?-*',
        'CIBW_SKIP': 'cp34-*',
    })

    # check that we got the right wheels. There should be no 2.7 or 3.4.
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if ('-cp3' in w) and ('-cp34' not in w)]
    actual_wheels = os.listdir('wheelhouse')
    assert set(actual_wheels) == set(expected_wheels)
