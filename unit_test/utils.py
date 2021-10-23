from cibuildwheel.options import CommandLineArguments


def get_default_command_line_arguments() -> CommandLineArguments:
    defaults = CommandLineArguments()

    defaults.platform = "auto"
    defaults.allow_empty = False
    defaults.archs = None
    defaults.config_file = ""
    defaults.output_dir = None
    defaults.package_dir = "."
    defaults.prerelease_pythons = False
    defaults.print_build_identifiers = False

    return defaults
