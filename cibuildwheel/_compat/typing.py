from __future__ import annotations

import sys

if sys.version_info < (3, 8):
    from typing_extensions import Final, Literal, OrderedDict, Protocol, TypedDict
else:
    from typing import Final, Literal, OrderedDict, Protocol, TypedDict  # noqa: TID251

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, assert_never
else:
    from typing import NotRequired, assert_never  # noqa: TID251

__all__ = (
    "Final",
    "Literal",
    "Protocol",
    "Protocol",
    "TypedDict",
    "OrderedDict",
    "assert_never",
    "NotRequired",
)
