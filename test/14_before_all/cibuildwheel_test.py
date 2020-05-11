import os

import utils


def test():
    project_dir = os.path.dirname(__file__)

    with open(os.path.join(project_dir, "text_info.txt"), mode='w') as ff:
        print("dummy text", file=ff)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        # write python version information to a temporary file, this is
        # checked in setup.py
        'CIBW_BEFORE_ALL': '''python -c "open('{project}/text_info.txt', 'w').write('sample text')"''',
    })


    # also check that we got the right wheels
    os.remove(os.path.join(project_dir, "text_info.txt"))
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)
