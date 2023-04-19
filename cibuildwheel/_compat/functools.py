from __future__ import annotations

import sys

if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from ._functools_cached_property_38 import cached_property

__all__ = ("cached_property",)
