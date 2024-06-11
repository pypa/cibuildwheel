import contextlib
import os
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Generator
from zipfile import ZipFile


def extract_zip(zip_src: Path, dest: Path) -> None:
    with ZipFile(zip_src) as zip_:
        for zinfo in zip_.filelist:
            zip_.extract(zinfo, dest)

            # Set permissions to the same values as they were set in the archive
            # We have to do this manually due to
            # https://github.com/python/cpython/issues/59999
            # But some files in the zipfile seem to have external_attr with 0
            # permissions. In that case just use the default value???
            permissions = (zinfo.external_attr >> 16) & 0o777
            if permissions != 0:
                dest.joinpath(zinfo.filename).chmod(permissions)


def extract_tar(tar_src: Path, dest: Path) -> None:
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


@dataclass(frozen=True)
class FileReport:
    name: str
    size: str


# Can be replaced by contextlib.chdir in Python 3.11
@contextlib.contextmanager
def chdir(new_path: Path | str) -> Generator[None, None, None]:
    """Non thread-safe context manager to change the current working directory."""

    cwd = os.getcwd()
    try:
        os.chdir(new_path)
        yield
    finally:
        os.chdir(cwd)