"""File handling functions with default case and error handling."""

from __future__ import annotations

import contextlib
import os
import shutil
import ssl
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Generator
from zipfile import ZipFile

import certifi


def extract_zip(zip_src: Path, dest: Path) -> None:
    """Extracts a zip and correctly sets permissions on extracted files.

    Note:
      - sets permissions to the same values as they were set in the archive
      - files with no clear permissions in `external_attr` will be extracted with default values
    """
    with ZipFile(zip_src) as zip_:
        for zinfo in zip_.filelist:
            zip_.extract(zinfo, dest)

            # We have to do this manually due to https://github.com/python/cpython/issues/59999
            permissions = (zinfo.external_attr >> 16) & 0o777
            if permissions != 0:
                dest.joinpath(zinfo.filename).chmod(permissions)


def extract_tar(tar_src: Path, dest: Path) -> None:
    """Extracts a tar file using the stdlib 'tar' filter.

    See: https://docs.python.org/3/library/tarfile.html#tarfile.tar_filter for filter details
    """
    with tarfile.open(tar_src) as tar_:
        tar_.extraction_filter = getattr(tarfile, "tar_filter", (lambda member, _: member))
        tar_.extractall(dest)


def download(url: str, dest: Path) -> None:
    print(f"+ Download {url} to {dest}")
    dest_dir = dest.parent
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True)

    # we've had issues when relying on the host OS' CA certificates on Windows,
    # so we use certifi (this sounds odd but requests also does this by default)
    cafile = os.environ.get("SSL_CERT_FILE", certifi.where())
    context = ssl.create_default_context(cafile=cafile)
    repeat_num = 3
    for i in range(repeat_num):
        try:
            with urllib.request.urlopen(url, context=context) as response:
                dest.write_bytes(response.read())
                return

        except OSError:
            if i == repeat_num - 1:
                raise
            sleep(3)


def move_file(src_file: Path, dst_file: Path) -> Path:
    """Moves a file safely while avoiding potential semantic confusion:

    1. `dst_file` must point to the target filename, not a directory
    2. `dst_file` will be overwritten if it already exists
    3. any missing parent directories will be created

    Returns the fully resolved Path of the resulting file.

    Raises:
        NotADirectoryError: If any part of the intermediate path to `dst_file` is an existing file
        IsADirectoryError: If `dst_file` points directly to an existing directory
    """
    src_file = src_file.resolve(strict=True)
    dst_file = dst_file.resolve()

    if dst_file.is_dir():
        msg = "dst_file must be a valid target filename, not an existing directory."
        raise IsADirectoryError(msg)
    dst_file.unlink(missing_ok=True)
    dst_file.parent.mkdir(parents=True, exist_ok=True)

    # using shutil.move() as Path.rename() is not guaranteed to work across filesystem boundaries
    # explicit str() needed for Python 3.8
    resulting_file = shutil.move(str(src_file), str(dst_file))
    return Path(resulting_file).resolve(strict=True)


@dataclass(frozen=True)
class FileReport:
    """Caches basic details about a file to avoid repeated calls to `stat()`."""

    name: str
    size: str


# Required until end of Python 3.10 support
@contextlib.contextmanager
def chdir(new_path: Path | str) -> Generator[None, None, None]:
    """Non thread-safe context manager to temporarily change the current working directory.

    Equivalent to `contextlib.chdir` in Python 3.11
    """

    cwd = os.getcwd()
    try:
        os.chdir(new_path)
        yield
    finally:
        os.chdir(cwd)
