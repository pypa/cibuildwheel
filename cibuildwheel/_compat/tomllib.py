from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from tomllib import load
else:
    from tomli import load

__all__ = ("load",)
