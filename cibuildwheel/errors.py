"""
Errors that can cause the build to fail. Each subclass of FatalError has
a different return code, by defining them all here, we can ensure that they're
semantically clear and unique.
"""

import textwrap


class FatalError(BaseException):
    """
    Raising an error of this type will cause the message to be printed to
    stderr and the process to be terminated. Within cibuildwheel, raising this
    exception produces a better error message, and optional traceback.
    """

    return_code: int = 1


class ConfigurationError(FatalError):
    return_code = 2


class NothingToDoError(FatalError):
    return_code = 3


class DeprecationError(FatalError):
    return_code = 4


class NonPlatformWheelError(FatalError):
    def __init__(self) -> None:
        message = textwrap.dedent(
            """
            Build failed because a pure Python wheel was generated.

            If you intend to build a pure-Python wheel, you don't need cibuildwheel - use
            `pip wheel -w DEST_DIR .` instead.

            If you expected a platform wheel, check your project configuration, or run
            cibuildwheel with CIBW_BUILD_VERBOSITY=1 to view build logs.
            """
        )
        super().__init__(message)
        self.return_code = 5


class AlreadyBuiltWheelError(FatalError):
    def __init__(self, wheel_name: str) -> None:
        message = textwrap.dedent(
            f"""
            Build failed because a wheel named {wheel_name} was already generated in the current run.

            If you expected another wheel to be generated, check your project configuration, or run
            cibuildwheel with CIBW_BUILD_VERBOSITY=1 to view build logs.
            """
        )
        super().__init__(message)
        self.return_code = 6


class OCIEngineTooOldError(FatalError):
    return_code = 7
