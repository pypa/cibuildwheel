import fnmatch
import json
import platform
import typing
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from filelock import FileLock

from cibuildwheel import __version__ as cibw_version
from cibuildwheel.util.file import download, extract_tar


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


def github_api_request(path: str, *, max_retries: int = 3) -> dict[str, Any]:
    """
    Makes a GitHub API request to the given path and returns the JSON response.
    """
    api_url = f"https://api.github.com/{path}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"cibuildwheel/{cibw_version}",
    }
    request = urllib.request.Request(api_url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return typing.cast(dict[str, Any], json.load(response))

    except (urllib.error.URLError, TimeoutError) as e:
        if max_retries > 0:
            print(f"Retrying GitHub API request due to error: {e}")
            return github_api_request(path, max_retries=max_retries - 1)
        else:
            msg = f"GitHub API request failed (Network error: {e}). Check network connection."

            raise PythonBuildStandaloneError(msg) from e


def _find_matching_asset_url(
    *,
    release_tag: str,
    release_data: dict[str, Any],
    python_version: str,
    arch_identifier: str,
    platform_identifier: str,
    libc_identifier: str | None,
) -> tuple[str, str]:
    """Finds the matching asset URL and filename."""
    assets = release_data.get("assets", [])

    if not assets:
        msg = f"No download assets found in release {release_tag}."
        raise PythonBuildStandaloneError(msg)

    expected_suffix = f"{arch_identifier}-{platform_identifier}"
    if libc_identifier:
        expected_suffix += f"-{libc_identifier}"
    expected_suffix += "-install_only.tar.gz"

    asset_pattern = f"cpython-{python_version}.*-{expected_suffix}"
    print(f"Looking for file with pattern {asset_pattern}'")

    for asset in assets:
        asset_name = asset.get("name")
        if not asset_name or not isinstance(asset_name, str):
            continue

        if not fnmatch.fnmatch(asset_name, asset_pattern):
            continue

        asset_url = asset.get("browser_download_url")
        if asset_url and isinstance(asset_url, str):
            return asset_url, asset_name

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
    """Finds the python executable within the extracted directory structure. Raises FatalError."""
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
    release_tag: str, python_version: str, temp_dir: Path, cache_dir: Path
) -> Path:
    """
    Returns a Python environment from python-build-standalone,
    downloading it if necessary using a cache, and expanding it into a fresh base path.

    Args:
        release_tag: The exact GitHub release tag (e.g., "20240224").
        python_version: The Python version string (e.g., "3.12").
        temp_dir: A directory where the Python environment will be extracted.
        cache_dir: A directory to store/retrieve downloaded archives.

    Returns:
        The absolute path to the python executable within the extracted environment (in temp_dir).

    Raises:
        PythonBuildStandaloneError: If the platform is unsupported, the build cannot be found,
                    download/extraction fails, or configuration is invalid.
    """

    print(
        f"Creating python-build-standalone environment: version={python_version}, tag={release_tag}"
    )

    arch_id, platform_id, libc_id = _get_platform_identifiers()
    release_data = github_api_request(
        f"repos/astral-sh/python-build-standalone/releases/tags/{release_tag}"
    )

    asset_url, asset_filename = _find_matching_asset_url(
        release_tag=release_tag,
        release_data=release_data,
        python_version=python_version,
        arch_identifier=arch_id,
        platform_identifier=platform_id,
        libc_identifier=libc_id,
    )

    archive_path = _download_or_get_from_cache(
        asset_url=asset_url, asset_filename=asset_filename, cache_dir=cache_dir
    )

    python_base_dir = temp_dir / f"pbs-{release_tag}-{python_version}"
    assert not python_base_dir.exists()
    extract_tar(archive_path, python_base_dir)

    return _find_python_executable(python_base_dir)
