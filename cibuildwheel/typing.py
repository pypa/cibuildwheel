import os
import subprocess
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    PopenBytes = subprocess.Popen[bytes]
    PathOrStr = Union[str, os.PathLike[str]]
else:
    PopenBytes = subprocess.Popen
    PathOrStr = Union[str, "os.PathLike[str]"]
