# This module is copied into the site-packages directory of an Android build environment, and
# activated via a .pth file when we want the environment to simulate Android.

import os
import platform
import re
import sys
import sysconfig
from pathlib import Path
from typing import Any


def initialize() -> None:
    if not (host_triplet := os.environ.get("CIBW_HOST_TRIPLET")):
        return

    # os ######################################################################
    def cross_os_uname() -> os.uname_result:
        return os.uname_result(
            (
                "Linux",
                "localhost",
                # The Linux kernel version and release are unlikely to be significant, but return
                # realistic values anyway (from an API level 24 emulator).
                "3.18.91+",
                "#1 SMP PREEMPT Tue Jan 9 20:35:43 UTC 2018",
                host_triplet.split("-")[0],
            )
        )

    os.name = "posix"
    os.uname = cross_os_uname

    # platform ################################################################
    #
    # We can't determine the user-visible Android version number from the API level, so return a
    # string which will work fine for display, but will fail to parse as a version number.
    def cross_android_ver(*args: Any, **kwargs: Any) -> platform.AndroidVer:
        return platform.AndroidVer(
            release=f"API level {cross_getandroidapilevel()}",
            api_level=cross_getandroidapilevel(),
            manufacturer="Google",
            model="sdk_gphone64",
            device="emu64",
            is_emulator=True,
        )

    # platform.uname, platform.system etc. are all implemented in terms of platform.android_ver.
    platform.android_ver = cross_android_ver

    # sys #####################################################################
    def cross_getandroidapilevel() -> int:
        api_level = sysconfig.get_config_var("ANDROID_API_LEVEL")
        assert isinstance(api_level, int)
        return api_level

    # Some packages may recognize sys.cross_compiling from the crossenv tool.
    sys.cross_compiling = True  # type: ignore[attr-defined]
    sys.getandroidapilevel = cross_getandroidapilevel  # type: ignore[attr-defined]
    sys.implementation._multiarch = host_triplet  # type: ignore[attr-defined]
    sys.platform = "android"

    # Determine the abiflags from the sysconfigdata filename.
    sysconfigdata_path = next(Path(__file__).parent.glob("_sysconfigdata_*.py"))
    abiflags_match = re.match(r"_sysconfigdata_(.*?)_", sysconfigdata_path.name)
    assert abiflags_match is not None
    sys.abiflags = abiflags_match[1]

    # sysconfig ###############################################################
    #
    # Load the sysconfigdata file, generating its name from sys.abiflags,
    # sys.platform, and sys.implementation._multiarch.
    sysconfig._init_config_vars()  # type: ignore[attr-defined]

    # We don't change the actual sys.base_prefix and base_exec_prefix, because that
    # could have unpredictable effects. Instead, we change the sysconfig variables
    # used by sysconfig.get_paths().
    vars = sysconfig.get_config_vars()
    try:
        host_prefix = vars["host_prefix"]  # This variable was added in Python 3.14.
    except KeyError:
        host_prefix = vars["exec_prefix"]
    vars["installed_base"] = vars["installed_platbase"] = host_prefix

    # sysconfig.get_platform, which determines the wheel tag, is implemented in terms of
    # sys.platform, sysconfig.get_config_var("ANDROID_API_LEVEL") (see localized_vars in
    # android.py), and os.uname.
