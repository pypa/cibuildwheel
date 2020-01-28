import os
import textwrap
from . import utils


project_dir = os.path.dirname(__file__)

def test():
    utils.generate_project(
        path=project_dir,
        extra_files=[
            ('spam/__init__.py', textwrap.dedent('''
                __version__ = "0.2.0"
            ''')),
            ('setup.cfg', textwrap.dedent('''
                [metadata]
                name = spam
                version = attr: spam.__version__

                [options]
                packages = find:
            '''))
        ],
    )

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels('spam', '0.2.0')
    assert set(actual_wheels) == set(expected_wheels)
