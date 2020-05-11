import os
import sys

from setuptools import (
    Extension,
    setup,
)

# assert that the Python version as written to text_info.txt in the CIBW_BEFORE_ALL step
# is the same one as is currently running.
with open("text_info.txt") as f:
    stored_text = f.read()

print("## stored text: "+stored_text)
assert stored_text == "sample text"



setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
