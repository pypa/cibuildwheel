import sys
import sysconfig
from pathlib import Path

assert sys.platform == "android"
assert sysconfig.get_platform().startswith("android-")

android_prefix = Path(f"{sys.prefix}/../python/prefix").resolve()
assert android_prefix.is_dir()

vars = sysconfig.get_config_vars()
assert vars["INCLUDEDIR"] == f"{android_prefix}/include"
assert vars["LDVERSION"] == f"{sys.version_info[0]}.{sys.version_info[1]}{sys.abiflags}"
assert vars["INCLUDEPY"] == f"{vars['INCLUDEDIR']}/python{vars['LDVERSION']}"
assert vars["LIBDIR"] == f"{android_prefix}/lib"
assert vars["Py_ENABLE_SHARED"] == 1

paths = sysconfig.get_paths()
assert paths["include"] == vars["INCLUDEPY"]
assert paths["platinclude"] == vars["INCLUDEPY"]
