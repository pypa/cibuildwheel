import pytest

from cibuildwheel.platforms.macos import _setup_arch_environment


@pytest.mark.parametrize(
    ("identifier", "host_platform", "archflags", "cmake_archs"),
    [
        ("cp314-macosx_arm64", "macosx-11.0-arm64", "-arch arm64", "arm64"),
        (
            "cp314-macosx_universal2",
            "macosx-10.9-universal2",
            "-arch arm64 -arch x86_64",
            "arm64;x86_64",
        ),
        ("cp314-macosx_x86_64", "macosx-10.9-x86_64", "-arch x86_64", "x86_64"),
    ],
)
def test_setup_arch_environment(
    identifier: str, host_platform: str, archflags: str, cmake_archs: str
) -> None:
    env: dict[str, str] = {}

    _setup_arch_environment(identifier, env)

    assert env == {
        "_PYTHON_HOST_PLATFORM": host_platform,
        "ARCHFLAGS": archflags,
        "CMAKE_OSX_ARCHITECTURES": cmake_archs,
    }


def test_setup_arch_environment_keeps_existing_values() -> None:
    env = {
        "_PYTHON_HOST_PLATFORM": "custom-platform",
        "ARCHFLAGS": "-arch custom",
        "CMAKE_OSX_ARCHITECTURES": "custom-arch",
    }

    _setup_arch_environment("cp314-macosx_arm64", env)

    assert env == {
        "_PYTHON_HOST_PLATFORM": "custom-platform",
        "ARCHFLAGS": "-arch custom",
        "CMAKE_OSX_ARCHITECTURES": "custom-arch",
    }
