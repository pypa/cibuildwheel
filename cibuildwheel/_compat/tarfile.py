# Based on https://github.com/pypa/build/blob/f4ebd495cc0c2c74155bd4fe48b76399fb7927ac/src/build/_compat/tarfile.py

from __future__ import annotations

import sys
import tarfile

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path

    TarFile = tarfile.TarFile

# Per https://peps.python.org/pep-0706/, the "data" filter will become
# the default in Python 3.14. The first series of releases with the filter
# had a broken filter that could not process symlinks correctly.
elif (3, 11, 5) <= sys.version_info < (3, 14):

    class TarFile(tarfile.TarFile):  # pragma: no cover
        extraction_filter = staticmethod(tarfile.data_filter)

else:
    TarFile = tarfile.TarFile  # pragma: no cover


# Same availability matrix as the TarFile subclass above. On runtimes that
# ship the stdlib ``data`` filter we delegate to it; the fallback branch is
# only reached on 3.10.0-3.10.12 / 3.11.0-3.11.4 and validates each member
# manually before extraction.
if sys.version_info >= (3, 11, 5):

    def safe_extractall(tar: tarfile.TarFile, path: Path) -> None:  # pragma: no cover
        """Extract every member of ``tar`` into ``path`` via the PEP 706 ``data`` filter."""
        tar.extractall(path, filter="data")

else:

    def safe_extractall(tar: tarfile.TarFile, path: Path) -> None:  # pragma: no cover
        """Validate every member of ``tar``, then extract into ``path``.

        Reached on 3.10.0-3.10.12 / 3.11.0-3.11.4 where the stdlib ``data`` filter is missing. Device or special files,
        paths that escape ``path``, and symlinks/hardlinks whose targets resolve outside ``path`` are rejected before
        any write hits the disk.

        """
        base = path.resolve()
        for member in tar.getmembers():
            _validate_safe_member(member, base)
        tar.extractall(path)


def _validate_safe_member(member: tarfile.TarInfo, base: Path) -> None:
    if member.ischr() or member.isblk() or member.isfifo():
        msg = f"refusing to extract special device file {member.name!r}"
        raise tarfile.TarError(msg)
    target = (base / member.name).resolve(strict=False)
    if not target.is_relative_to(base):
        msg = f"refusing to extract {member.name!r}: path escapes destination"
        raise tarfile.TarError(msg)
    if member.issym() or member.islnk():
        link_base = target.parent if member.issym() else base
        link_target = (link_base / member.linkname).resolve(strict=False)
        if not link_target.is_relative_to(base):
            msg = f"refusing to extract {member.name!r}: link target escapes destination"
            raise tarfile.TarError(msg)


__all__ = [
    "TarFile",
    "safe_extractall",
]
