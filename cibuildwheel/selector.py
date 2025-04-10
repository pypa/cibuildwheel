import itertools
from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatch
from typing import Any

import bracex
from packaging.specifiers import SpecifierSet
from packaging.version import Version


def selector_matches(patterns: str, string: str) -> bool:
    """
    Returns True if `string` is matched by any of the wildcard patterns in
    `patterns`.

    Matching is according to fnmatch, but with shell-like curly brace
    expansion. For example, 'cp{36,37}-*' would match either of 'cp36-*' or
    'cp37-*'.
    """

    patterns_list = patterns.split()
    expanded_patterns = itertools.chain.from_iterable(bracex.expand(p) for p in patterns_list)
    return any(fnmatch(string, pat) for pat in expanded_patterns)


class EnableGroup(StrEnum):
    """
    Groups of build selectors that are not enabled by default.
    """

    CPythonFreeThreading = "cpython-freethreading"
    CPythonPrerelease = "cpython-prerelease"
    PyPy = "pypy"
    GraalPy = "graalpy"

    @classmethod
    def all_groups(cls) -> frozenset["EnableGroup"]:
        return frozenset(cls)


@dataclass(frozen=True, kw_only=True)
class BuildSelector:
    """
    This class holds a set of build/skip patterns. You call an instance with a
    build identifier, and it returns True if that identifier should be
    included. Only call this on valid identifiers, ones that have at least 2
    numeric digits before the first dash.
    """

    build_config: str
    skip_config: str
    requires_python: SpecifierSet | None = None
    enable: frozenset[EnableGroup] = frozenset()

    def __call__(self, build_id: str) -> bool:
        # Filter build selectors by python_requires if set
        if self.requires_python is not None:
            py_ver_str = build_id.split("-")[0]
            py_ver_str = py_ver_str.removesuffix("t")
            major = int(py_ver_str[2])
            minor = int(py_ver_str[3:])
            version = Version(f"{major}.{minor}.99")
            if not self.requires_python.contains(version):
                return False

        # filter out groups that are not enabled
        if EnableGroup.CPythonFreeThreading not in self.enable and fnmatch(build_id, "cp3??t-*"):
            return False
        if EnableGroup.CPythonPrerelease not in self.enable and fnmatch(build_id, "cp314*"):
            return False
        if EnableGroup.PyPy not in self.enable and fnmatch(build_id, "pp*"):
            return False
        if EnableGroup.GraalPy not in self.enable and fnmatch(build_id, "gp*"):
            return False

        should_build = selector_matches(self.build_config, build_id)
        should_skip = selector_matches(self.skip_config, build_id)

        return should_build and not should_skip

    def options_summary(self) -> Any:
        return {
            "build_config": self.build_config,
            "skip_config": self.skip_config,
            "requires_python": str(self.requires_python),
            "enable": sorted(group.value for group in self.enable),
        }


@dataclass(frozen=True)
class TestSelector:
    """
    A build selector that can only skip tests according to a skip pattern.
    """

    skip_config: str

    def __call__(self, build_id: str) -> bool:
        should_skip = selector_matches(self.skip_config, build_id)
        return not should_skip

    def options_summary(self) -> Any:
        return {"skip_config": self.skip_config}
