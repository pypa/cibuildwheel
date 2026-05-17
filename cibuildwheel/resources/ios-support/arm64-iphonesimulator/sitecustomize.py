# A site customization that can be used to trick pip into installing packages
# cross-platform. If the folder containing this file is on your PYTHONPATH when
# you invoke python, the interpreter will behave as if it were running on
# arm64 iphonesimulator.
import sys
import os

# Apply the cross-platform patch
import _cross_arm64_iphonesimulator
import _cross_venv


# Call the next sitecustomize script if there is one
# (https://nedbatchelder.com/blog/201001/running_code_at_python_startup.html).
del sys.modules["sitecustomize"]
this_dir = os.path.dirname(__file__)
path_index = sys.path.index(this_dir)
del sys.path[path_index]
try:
    import sitecustomize  # noqa: F401
finally:
    sys.path.insert(path_index, this_dir)
