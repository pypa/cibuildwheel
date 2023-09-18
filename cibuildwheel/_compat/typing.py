from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, assert_never
else:
    from typing import NotRequired, assert_never

__all__ = (
    "assert_never",
    "NotRequired",
)
