# A site package that turns a macOS virtual environment
# into an x86_64 iphonesimulator cross-platform virtual environment
import platform
import subprocess
import sys
import sysconfig

###########################################################################
# sys module patches
###########################################################################
sys.cross_compiling = True
sys.platform = "ios"
sys.implementation._multiarch = "x86_64-iphonesimulator"
sys.base_prefix = sysconfig._get_sysconfigdata()["prefix"]
sys.base_exec_prefix = sysconfig._get_sysconfigdata()["prefix"]

###########################################################################
# subprocess module patches
###########################################################################
subprocess._can_fork_exec = True


###########################################################################
# platform module patches
###########################################################################

def cross_system():
    return "iOS"


def cross_uname():
    return platform.uname_result(
        system="iOS",
        node="build",
        release="13.0",
        version="",
        machine="x86_64",
    )


def cross_ios_ver(system="", release="", model="", is_simulator=False):
    if system == "":
        system = "iOS"
    if release == "":
        release = "13.0"
    if model == "":
        model = "iphonesimulator"

    return platform.IOSVersionInfo(system, release, model, True)


platform.system = cross_system
platform.uname = cross_uname
platform.ios_ver = cross_ios_ver


###########################################################################
# sysconfig module patches
###########################################################################

def cross_get_platform():
    return "ios-13.0-x86_64-iphonesimulator"


def cross_get_sysconfigdata_name():
    return "_sysconfigdata__ios_x86_64-iphonesimulator"


sysconfig.get_platform = cross_get_platform
sysconfig._get_sysconfigdata_name = cross_get_sysconfigdata_name

# Ensure module-level values cached at time of import are updated.
sysconfig._BASE_PREFIX = sys.base_prefix
sysconfig._BASE_EXEC_PREFIX = sys.base_exec_prefix

# Force sysconfig data to be loaded (and cached).
sysconfig._init_config_vars()
