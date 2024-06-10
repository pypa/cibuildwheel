"""
Errors that can cause the build to fail. Each subclass of FatalError has
a different return code, by defining them all here, we can ensure that they're
semantically clear and unique.
"""


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
