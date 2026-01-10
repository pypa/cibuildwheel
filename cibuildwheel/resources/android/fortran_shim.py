# Based on
# https://github.com/kivy/python-for-android/blob/develop/pythonforandroid/recipes/fortran/__init__.py

import os
import re
import shutil
import sys
from itertools import chain
from pathlib import Path

from filelock import FileLock

from cibuildwheel.util.file import CIBW_CACHE_PATH, download

RELEASE_URL = "https://github.com/termux/ndk-toolchain-clang-with-flang/releases/download"
RELEASE_VERSION = "r27c"

# The compiler is built for Linux x86_64, so we use Docker on macOS.
DOCKER_IMAGE = "debian:trixie"


def main() -> None:
    cache_dir = CIBW_CACHE_PATH / f"flang-android-{RELEASE_VERSION}"
    with FileLock(f"{cache_dir}.lock"):
        if not cache_dir.exists():
            download_flang(cache_dir)

    flang_dir = Path(__file__).parents[2] / "flang"
    with FileLock(f"{flang_dir}.lock"):
        if not flang_dir.exists():
            setup_flang(cache_dir, flang_dir)

    run_flang(flang_dir)


def download_flang(cache_dir: Path) -> None:
    tmp_dir = Path(f"{cache_dir}.tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    for archive_name, src, dst in [
        (
            f"package-flang-{arch}.tar.bz2",
            f"build-{arch}-install",
            f"sysroot/usr/lib/{arch}-linux-android",
        )
        for arch in ["aarch64", "x86_64"]
    ] + [
        ("package-install.tar.bz2", "out/install/linux-x86/clang-dev", ""),
        ("package-flang-host.tar.bz2", "build-host-install", ""),
    ]:
        archive_path = tmp_dir / archive_name
        download(f"{RELEASE_URL}/{RELEASE_VERSION}/{archive_name}", archive_path)
        shutil.unpack_archive(archive_path, tmp_dir)
        archive_path.unlink()

        (tmp_dir / dst).mkdir(parents=True, exist_ok=True)
        for src_path in (tmp_dir / src).iterdir():
            src_path.rename(tmp_dir / dst / src_path.name)

    tmp_dir.rename(cache_dir)


def setup_flang(cache_dir: Path, flang_dir: Path) -> None:
    toolchain_dir = Path(os.environ["CC"]).parents[1]
    ndk_dir = toolchain_dir.parents[3]
    clang_ver_ndk = clang_ver(ndk_dir)

    clang_ver_cache = clang_ver(cache_dir)
    if clang_ver_cache != clang_ver_ndk:
        msg = f"Flang uses Clang {clang_ver_cache}, but NDK uses Clang {clang_ver_ndk}"
        raise ValueError(msg)

    # Merge the Flang tree with the parts of the NDK it uses.
    tmp_dir = Path(f"{flang_dir}.tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    merge_path(cache_dir, tmp_dir)
    merge_path(toolchain_dir, tmp_dir, f"lib/clang{clang_ver_ndk}/lib")
    merge_path(toolchain_dir, tmp_dir, "sysroot")

    tmp_dir.rename(flang_dir)


def clang_ver(toolchain_dir: Path) -> str:
    versions = [p.name for p in (toolchain_dir / "lib/clang").iterdir()]
    assert len(versions) == 1
    return versions[0]


# The merged tree is more than 1 GB, so use symlinks to avoid copying.
def merge_path(src_dir: Path, dst_dir: Path, rel_path: str | None = None) -> None:
    if rel_path is None:
        for p in src_dir.iterdir():
            merge_path(src_dir, dst_dir, p.name)
        return

    if not dst_dir.exists():
        dst_dir.mkdir()
    elif dst_dir.is_dir():
        if dst_dir.is_symlink():
            old_src_dir = dst_dir.readlink()
            dst_dir.unlink()
            dst_dir.mkdir()
            for p in old_src_dir.iterdir():
                (dst_dir / p.name).symlink_to(p)
    else:
        msg = f"{dst_dir} is not a directory"
        raise ValueError(msg)

    prefix, sep, suffix = rel_path.partition("/")
    if sep:
        merge_path(src_dir / prefix, dst_dir / prefix, suffix)
    else:
        dst_path = dst_dir / rel_path
        if dst_path.exists():
            merge_path(src_dir / rel_path, dst_dir / rel_path)
        else:
            dst_path.symlink_to(src_dir / rel_path)


def run_flang(flang_dir: Path) -> None:
    match = re.fullmatch(r"(.+)-clang", os.environ["CC"])
    assert match is not None
    args = [f"{flang_dir}/bin/flang-new", f"--target={match[1]}", *sys.argv[1:]]

    if sys.platform == "linux":
        pass
    elif sys.platform == "darwin":
        args = [
            *["docker", "run"],
            *chain.from_iterable(
                # Docker on macOS only allows certain directories to be mounted as volumes,
                # by default, but they include all the locations we're likely to need.
                ["-v", f"{path}:{path}"]
                for path in ["/private", "/Users", "/tmp"]
            ),
            *["-w", str(Path.cwd()), "--entrypoint", args[0], DOCKER_IMAGE, *args[1:]],
        ]
    else:
        msg = f"unknown platform: {sys.platform}"
        raise ValueError(msg)

    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
