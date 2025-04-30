# This module is copied into the site-packages directory of an Android build environment, and
# activated via a .pth file when we want the environment to simulate Android.

import os
import platform
import re
import sys
import sysconfig
from pathlib import Path


def initialize():
    # os ######################################################################
    def cross_os_uname():
        return os.uname_result(
            (
                "Linux",
                "localhost",
                # The Linux kernel version and release are unlikely to be significant, but return
                # realistic values anyway (from an API level 24 emulator).
                "3.18.91+",
                "#1 SMP PREEMPT Tue Jan 9 20:35:43 UTC 2018",
                os.environ["HOST"].split("-")[0],
            )
        )

    os.name = "posix"
    os.uname = cross_os_uname

    # platform ################################################################
    #
    # We can't determine the user-visible Android version number from the API level, so return a
    # string which will work fine for display, but will fail to parse as a version number.
    def cross_android_ver(*args, **kwargs):
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
    def cross_getandroidapilevel():
        return sysconfig.get_config_var("ANDROID_API_LEVEL")

    sys.cross_compiling = True  # Some packages may recognize this from the crossenv tool.
    sys.getandroidapilevel = cross_getandroidapilevel
    sys.implementation._multiarch = os.environ["HOST"]
    sys.platform = "android"

    # _get_sysconfigdata_name is implemented in terms of sys.abiflags, sys.platform and
    # sys.implementation._multiarch. Determine the abiflags from the filename.
    sysconfigdata_path = next(Path(__file__).parent.glob("_sysconfigdata_*.py"))
    sys.abiflags = re.match(r"_sysconfigdata_(.*?)_", sysconfigdata_path.name)[1]

    # sysconfig ###############################################################
    #
    sysconfig._init_config_vars()

    # sysconfig.get_platform, which determines the wheel tag, is implemented in terms of
    # sys.platform, sysconfig.get_config_var("ANDROID_API_LEVEL") (see localized_vars in
    # android.py), and os.uname.
