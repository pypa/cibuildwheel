import os
import shutil
import ssl
import tarfile
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path, PurePath
from typing import Final
from zipfile import ZipFile

import certifi
from platformdirs import user_cache_path

from ..errors import FatalError

DEFAULT_CIBW_CACHE_PATH: Final[Path] = user_cache_path(appname="cibuildwheel", appauthor="pypa")
CIBW_CACHE_PATH: Final[Path] = Path(
    os.environ.get("CIBW_CACHE_PATH", DEFAULT_CIBW_CACHE_PATH)
).resolve()


def download(url: str, dest: Path) -> None:
    print(f"+ Download {url} to {dest}")
    dest_dir = dest.parent
    dest_dir.mkdir(parents=True, exist_ok=True)

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
            time.sleep(3)


def extract_zip(zip_src: Path, dest: Path) -> None:
    """Extracts a zip and correctly sets permissions on extracted files.

    Notes:
        - sets permissions to the same values as they were set in the archive
        - files with no clear permissions in `external_attr` will be extracted with default values
    """
    with ZipFile(zip_src) as zip_:
        for zinfo in zip_.filelist:
            zip_.extract(zinfo, dest)

            # Set permissions to the same values as they were set in the archive
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


def copy_into_local(src: Path, dst: PurePath) -> None:
    """Copy a path from src to dst, regardless of whether it's a file or a directory."""
    # Ensure the target folder location exists
    Path(dst.parent).mkdir(exist_ok=True, parents=True)

    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy(src, dst)


def copy_test_sources(
    test_sources: list[str],
    project_dir: Path,
    test_dir: PurePath,
    copy_into: Callable[[Path, PurePath], None] = copy_into_local,
) -> None:
    """Copy the list of test sources from the package to the test directory.

    :param test_sources: A list of test paths, relative to the project_dir.
    :param project_dir: The root of the project.
    :param test_dir: The folder where test sources should be placed.
    :param copy_into: The copy function to use. By default, does a local
        filesystem copy; but an OCIContainer.copy_info method (or equivalent)
        can be provided.
    """
    for test_path in test_sources:
        source = project_dir.resolve() / test_path

        if not source.exists():
            msg = f"Test source {test_path} does not exist."
            raise FatalError(msg)

        copy_into(source, test_dir / test_path)
