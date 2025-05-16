import fnmatch
import functools
import json
import platform
import typing
from pathlib import Path

from filelock import FileLock

from cibuildwheel.util.file import download, extract_tar
from cibuildwheel.util.resources import PYTHON_BUILD_STANDALONE_RELEASES


class PythonBuildStandaloneAsset(typing.TypedDict):
    name: str
    url: str


class PythonBuildStandaloneRelease(typing.TypedDict):
    tag: str
    assets: list[PythonBuildStandaloneAsset]


class PythonBuildStandaloneReleaseData(typing.TypedDict):
    releases: list[PythonBuildStandaloneRelease]


@functools.cache
def get_python_build_standalone_release_data() -> PythonBuildStandaloneReleaseData:
    with open(PYTHON_BUILD_STANDALONE_RELEASES, "rb") as f:
        return typing.cast(PythonBuildStandaloneReleaseData, json.load(f))


class PythonBuildStandaloneError(Exception):
    """Errors related to python-build-standalone."""


def _get_platform_identifiers() -> tuple[str, str, str | None]:
    """
    Detects the current platform and returns architecture, platform, and libc
    identifiers.
    """
    system = platform.system()
    machine = platform.machine()
    machine_lower = machine.lower()

    arch_identifier: str
    platform_identifier: str
    libc_identifier: str | None = None

    # Map Architecture
    if machine_lower in ["x86_64", "amd64"]:
        arch_identifier = "x86_64"
    elif machine_lower in ["aarch64", "arm64"]:
        arch_identifier = "aarch64"
    else:
        msg = f"Unsupported architecture: {system} {machine}. Cannot download appropriate Python build."
        raise PythonBuildStandaloneError(msg)

    # Map OS + Libc
    if system == "Linux":
        platform_identifier = "unknown-linux"
        libc_identifier = "musl" if "musl" in (platform.libc_ver() or ("", "")) else "gnu"
    elif system == "Darwin":
        platform_identifier = "apple-darwin"
    elif system == "Windows":
        platform_identifier = "pc-windows-msvc"
    else:
        msg = f"Unsupported operating system: {system}. Cannot download appropriate Python build."
        raise PythonBuildStandaloneError(msg)

    print(
        f"Detected platform: arch='{arch_identifier}', platform='{platform_identifier}', libc='{libc_identifier}'"
    )
    return arch_identifier, platform_identifier, libc_identifier


def _get_pbs_asset(
    *,
    python_version: str,
    arch_identifier: str,
    platform_identifier: str,
    libc_identifier: str | None,
) -> tuple[str, str, str]:
    """Finds the asset, returning (tag, filename, url)."""
    release_data = get_python_build_standalone_release_data()

    expected_suffix = f"{arch_identifier}-{platform_identifier}"
    if libc_identifier:
        expected_suffix += f"-{libc_identifier}"
    expected_suffix += "-install_only.tar.gz"

    asset_pattern = f"cpython-{python_version}.*-{expected_suffix}"
    print(f"Looking for file with pattern {asset_pattern}")

    for release in release_data["releases"]:
        for asset in release["assets"]:
            asset_name = asset["name"]
            if not fnmatch.fnmatch(asset_name, asset_pattern):
                continue

            asset_url = asset["url"]
            return release["tag"], asset_url, asset_name

    # If loop completes without finding a match
    msg = f"Could not find python-build-standalone release asset matching {asset_pattern!r}."
    raise PythonBuildStandaloneError(msg)


def _download_or_get_from_cache(asset_url: str, asset_filename: str, cache_dir: Path) -> Path:
    with FileLock(cache_dir / (asset_filename + ".lock")):
        asset_cache_path = cache_dir / asset_filename
        if asset_cache_path.is_file():
            print(f"Using cached python_build_standalone: {asset_cache_path}")
            return asset_cache_path

        print(f"Downloading python_build_standalone: {asset_url} to {asset_cache_path}")
        download(asset_url, asset_cache_path)
        return asset_cache_path


def _find_python_executable(extracted_dir: Path) -> Path:
    """Finds the python executable within the extracted directory structure."""
    # Structure is typically 'python/bin/python' or 'python/python.exe'
    base_install_dir = extracted_dir / "python"

    if platform.system() == "Windows":
        executable_path = base_install_dir / "python.exe"
    else:
        executable_path = base_install_dir / "bin" / "python"

    if not executable_path.is_file():
        msg = f"Could not locate python executable at expected path {executable_path} within {extracted_dir}."
        raise PythonBuildStandaloneError(msg)

    print(f"Found python executable: {executable_path}")
    return executable_path.resolve()  # Return absolute path


def create_python_build_standalone_environment(
    python_version: str, temp_dir: Path, cache_dir: Path
) -> Path:
    """
    Returns a Python environment from python-build-standalone, downloading it
    if necessary using a cache, and expanding it into a fresh base path.

    Args:
        python_version: The Python version string (e.g., "3.12").
        temp_dir: A directory where the Python environment will be created.
        cache_dir: A directory to store/retrieve downloaded archives.

    Returns:
        The absolute path to the python executable within the created environment (in temp_dir).

    Raises:
        PythonBuildStandaloneError: If the platform is unsupported, the build cannot be found,
                    download/extraction fails, or configuration is invalid.
    """

    print(f"Creating python-build-standalone environment: version={python_version}")

    arch_id, platform_id, libc_id = _get_platform_identifiers()

    pbs_tag, asset_url, asset_filename = _get_pbs_asset(
        python_version=python_version,
        arch_identifier=arch_id,
        platform_identifier=platform_id,
        libc_identifier=libc_id,
    )

    print(f"Using python-build-standalone release: {pbs_tag}")

    archive_path = _download_or_get_from_cache(
        asset_url=asset_url, asset_filename=asset_filename, cache_dir=cache_dir
    )

    python_base_dir = temp_dir / "pbs"
    assert not python_base_dir.exists()
    extract_tar(archive_path, python_base_dir)

    return _find_python_executable(python_base_dir)
