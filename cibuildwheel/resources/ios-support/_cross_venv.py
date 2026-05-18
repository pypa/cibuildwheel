import shutil
import sys
import sysconfig
from pathlib import Path

SITE_PACKAGE_PATH = Path(__file__).parent

###########################################################################
# importlib module patches
###########################################################################


def patch_env_create(env):
    """
    Patch the process of creating virtual environments to ensure that the cross
    environment modification files are also copied as part of environment
    creation.
    """
    old_pip_env_create = env._PipBackend.create

    def pip_env_create(self, path, *args, **kwargs):
        result = old_pip_env_create(self, path, *args, **kwargs)
        # Copy any _cross_*.pth or _cross_*.py file, plus the cross-platform
        # sysconfigdata module and sysconfig_vars JSON to the new environment.
        data_name = sysconfig._get_sysconfigdata_name()
        json_name = data_name.replace("_sysconfigdata", "_sysconfig_vars")
        for filename in [
            "_cross_venv.pth",
            "_cross_venv.py",
            f"_cross_{sys.implementation._multiarch.replace('-', '_')}.py",
            f"{data_name}.py",
            f"{json_name}.json",
        ]:
            src = SITE_PACKAGE_PATH / filename
            target = Path(path) / src.relative_to(
                SITE_PACKAGE_PATH.parent.parent.parent
            )
            if not target.exists():
                shutil.copy(src, target)
        return result

    env._PipBackend.create = pip_env_create


# Import hook that patches the creation of virtual environments by `build`
#
# The approach used here is the same as the one used by virtualenv to patch
# distutils (but without support for the older load_module API).
# https://docs.python.org/3/library/importlib.html#setting-up-an-importer
_BUILD_PATCH = ("build.env",)


class _Finder:
    """A meta path finder that allows patching the imported build modules."""

    fullname = None

    # lock[0] is threading.Lock(), but initialized lazily to avoid importing
    # threading very early at startup, because there are gevent-based
    # applications that need to be first to import threading by themselves.
    # See https://github.com/pypa/virtualenv/issues/1895 for details.
    lock = []  # noqa: RUF012

    def find_spec(self, fullname, path, target=None):
        if fullname in _BUILD_PATCH and self.fullname is None:
            # initialize lock[0] lazily
            if len(self.lock) == 0:
                import threading

                lock = threading.Lock()
                # there is possibility that two threads T1 and T2 are
                # simultaneously running into find_spec, observing .lock as
                # empty, and further going into hereby initialization. However
                # due to the GIL, list.append() operation is atomic and this
                # way only one of the threads will "win" to put the lock
                # - that every thread will use - into .lock[0].
                # https://docs.python.org/3/faq/library.html#what-kinds-of-global-value-mutation-are-thread-safe
                self.lock.append(lock)

            from functools import partial
            from importlib.util import find_spec

            with self.lock[0]:
                self.fullname = fullname
                try:
                    spec = find_spec(fullname, path)
                    if spec is not None:
                        # https://www.python.org/dev/peps/pep-0451/#how-loading-will-work
                        old = spec.loader.exec_module
                        func = self.exec_module
                        if old is not func:
                            spec.loader.exec_module = partial(func, old)
                        return spec
                finally:
                    self.fullname = None
        return None

    @staticmethod
    def exec_module(old, module):
        old(module)
        if module.__name__ in _BUILD_PATCH:
            patch_env_create(module)


sys.meta_path.insert(0, _Finder())
