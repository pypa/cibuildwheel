from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from tomllib import load  # noqa: TID251
else:
    from tomli import load  # noqa: TID251

__all__ = ("load",)
