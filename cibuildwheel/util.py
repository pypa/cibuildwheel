from fnmatch import fnmatch
import warnings


def prepare_command(command, project):
    '''
    Preprocesses a command by expanding variables like {project}.

    For example, used for the before_build option, where the user would
    like to run a command like `python setup.py test`. If the command should run on
    Python 3, the user could write `{python} setup.py test`. This command would expand
    it out to python2 or python3 as appropriate.
    '''
    if '{python}' in command or '{pip}' in command:
        warnings.warn("'{python}' and '{pip}' are no longer needed, and have been deprecated. Simply use 'python' or 'pip' instead.",
            DeprecationWarning)

    return command.format(python='python', pip='pip', project=project)


class BuildSkipper(object):
    def __init__(self, skip_config):
        self.patterns = skip_config.split()

    def __call__(self, build_id):
        return any(fnmatch(build_id, pattern) for pattern in self.patterns)

    def __repr__(self):
        return 'BuildSkipper(%r)' % ' '.join(self.patterns)


# Taken from https://stackoverflow.com/a/107717
class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)
