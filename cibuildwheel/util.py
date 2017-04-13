from fnmatch import fnmatch


def prepare_command(command, python, pip):
    '''
    Preprocesses a command by expanding variables like {python} or {pip}.

    For example, used for the before_build option, where the user would
    like to run a command like `python setup.py test`. If the command should run on
    Python 3, the user could write `{python} setup.py test`. This command would expand
    it out to python2 or python3 as appropriate.
    '''
    return command.format(python=python, pip=pip)


class BuildSkipper(object):
    def __init__(self, skip_config):
        self.patterns = skip_config.split()

    def __call__(self, build_id):
        return any(fnmatch(build_id, pattern) for pattern in self.patterns)

    def __repr__(self):
        return 'BuildSkipper(%r)' % ' '.join(self.patterns)
