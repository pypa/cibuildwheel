import os
import re
import shutil
import sys
from itertools import chain
from pathlib import Path

from filelock import FileLock

from cibuildwheel.util.file import CIBW_CACHE_PATH, download

# In the future we might pick a different Flang release depending on the NDK version,
# but so far all Python versions use the same NDK version, so there's no need.
RELEASE_URL = "https://github.com/termux/ndk-toolchain-clang-with-flang/releases/download"
RELEASE_VERSION = "r27c"
ARCHS = ["aarch64", "x86_64"]

# The compiler is built for Linux x86_64, so we use Docker on macOS.
DOCKER_IMAGE = "debian:trixie"


def main() -> None:
    cache_dir = CIBW_CACHE_PATH / f"flang-android-{RELEASE_VERSION}"
    with FileLock(f"{cache_dir}.lock"):
        if not cache_dir.exists():
            download_flang(cache_dir)

    run_flang(cache_dir)


def download_flang(cache_dir: Path) -> None:
    tmp_dir = Path(f"{cache_dir}.tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    for archive_name in [f"package-flang-{arch}.tar.bz2" for arch in ARCHS] + [
        "package-flang-host.tar.bz2",
        "package-install.tar.bz2",
    ]:
        archive_path = tmp_dir / archive_name
        download(f"{RELEASE_URL}/{RELEASE_VERSION}/{archive_name}", archive_path)
        shutil.unpack_archive(archive_path, tmp_dir)
        archive_path.unlink()

    # Merge the extracted trees together, along with the necessary parts of the NDK. Based on
    # https://github.com/kivy/python-for-android/blob/develop/pythonforandroid/recipes/fortran/__init__.py)
    flang_toolchain = tmp_dir / "toolchain"
    (tmp_dir / "out/install/linux-x86/clang-dev").rename(flang_toolchain)

    ndk_toolchain = Path(os.environ["CC"]).parents[1]
    if (clang_ver_flang := clang_ver(flang_toolchain)) != (
        clang_ver_ndk := clang_ver(ndk_toolchain)
    ):
        msg = f"Flang uses Clang {clang_ver_flang}, but NDK uses Clang {clang_ver_ndk}"
        raise ValueError(msg)

    clang_lib_path = f"lib/clang/{clang_ver_ndk}/lib"
    shutil.rmtree(flang_toolchain / clang_lib_path)

    for src, dst in [
        (f"{tmp_dir}/build-{arch}-install", f"sysroot/usr/lib/{arch}-linux-android")
        for arch in ARCHS
    ] + [
        (f"{tmp_dir}/build-host-install", ""),
        (f"{ndk_toolchain}/{clang_lib_path}", clang_lib_path),
        (f"{ndk_toolchain}/sysroot", "sysroot"),
    ]:
        shutil.copytree(src, flang_toolchain / dst, symlinks=True, dirs_exist_ok=True)

    flang_toolchain.rename(cache_dir)
    shutil.rmtree(tmp_dir)


def clang_ver(toolchain: Path) -> str:
    versions = [p.name for p in (toolchain / "lib/clang").iterdir()]
    assert len(versions) == 1
    return versions[0]


def run_flang(cache_dir: Path) -> None:
    match = re.fullmatch(r".+/(.+)-clang", os.environ["CC"])
    assert match is not None
    target = match[1]

    # In a future Flang version the executable name will change to "flang"
    # (https://blog.llvm.org/posts/2025-03-11-flang-new/).
    args = [f"{cache_dir}/bin/flang-new", f"--target={target}", *sys.argv[1:]]

    if sys.platform == "linux":
        pass
    elif sys.platform == "darwin":
        args = [
            *["docker", "run", "--rm", "--platform", "linux/amd64"],
            *chain.from_iterable(
                # Docker on macOS only allows certain directories to be mounted as volumes
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
