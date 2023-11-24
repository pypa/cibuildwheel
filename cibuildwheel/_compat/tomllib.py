from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from tomllib import load, loads
else:
    from tomli import load, loads

__all__ = ["load", "loads"]
