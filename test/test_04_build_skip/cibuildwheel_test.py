import os


def test(utils):
    # build the wheels
    utils.cibuildwheel_run(add_env={
        'CIBW_BUILD': 'cp3?-*',
        'CIBW_SKIP': 'cp37-*',
    })

    # check that we got the right wheels. There should be no 2.7 or 3.7.
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if ('-cp3' in w) and ('-cp37' not in w)]
    actual_wheels = utils.list_wheels()
    assert set(actual_wheels) == set(expected_wheels)
