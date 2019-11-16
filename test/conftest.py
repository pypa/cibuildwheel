'''
pytest conftest.py.
'''


import test.shared.utils


utils = test.shared.utils.utils  # export the utils fixture to be usable by any test
