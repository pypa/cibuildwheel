from __future__ import annotations

from threading import RLock
from typing import Any, Callable, Generic, TypeVar, overload

__all__ = ["cached_property"]

_NOT_FOUND = object()

_T = TypeVar("_T")


class cached_property(Generic[_T]):
    def __init__(self, func: Callable[[Any], _T]):
        self.func = func
        self.attrname: str | None = None
        self.__doc__ = func.__doc__
        self.lock = RLock()

    def __set_name__(self, owner: type[Any], name: str) -> None:
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            msg = f"Cannot assign the same cached_property to two different names ({self.attrname!r} and {name!r})."
            raise TypeError(msg)

    @overload
    def __get__(self, instance: None, owner: type[Any] | None = ...) -> cached_property[_T]:
        ...

    @overload
    def __get__(self, instance: object, owner: type[Any] | None = ...) -> _T:
        ...

    def __get__(self, instance: object | None, owner: type[Any] | None = None) -> Any:
        if instance is None:
            return self
        if self.attrname is None:
            msg = "Cannot use cached_property instance without calling __set_name__ on it."
            raise TypeError(msg)
        try:
            cache = instance.__dict__
        except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {self.attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            with self.lock:
                # check if another thread filled cache while we awaited lock
                val = cache.get(self.attrname, _NOT_FOUND)
                if val is _NOT_FOUND:
                    val = self.func(instance)
                    try:
                        cache[self.attrname] = val
                    except TypeError:
                        msg = (
                            f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                            f"does not support item assignment for caching {self.attrname!r} property."
                        )
                        raise TypeError(msg) from None
        return val
