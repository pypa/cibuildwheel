from fnmatch import fnmatch
import warnings
import os
from time import sleep

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


def prepare_command(command, **kwargs):
    '''
    Preprocesses a command by expanding variables like {python}.

    For example, used in the test_command option to specify the path to the
    project's root.
    '''
    return command.format(python='python', pip='pip', **kwargs)


def get_build_verbosity_extra_flags(level):
    if level > 0:
        return ['-' + level * 'v']
    elif level < 0:
        return ['-' + -level * 'q']
    else:
        return []


class BuildSelector(object):
    def __init__(self, build_config, skip_config):
        self.build_patterns = build_config.split()
        self.skip_patterns = skip_config.split()

    def __call__(self, build_id):
        def match_any(patterns):
            return any(fnmatch(build_id, pattern) for pattern in patterns)
        return match_any(self.build_patterns) and not match_any(self.skip_patterns)

    def __repr__(self):
        return 'BuildSelector({!r} - {!r})'.format(' '.join(self.build_patterns), ' '.join(self.skip_patterns))


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


def download(url, dest):
    print('+ Download ' + url + ' to ' + dest)
    dest_dir = os.path.dirname(dest)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    repeat_num = 3
    for i in range(repeat_num):
        try:
            response = urlopen(url)
        except:
            if i == repeat_num - 1:
                raise
            sleep(3)
            continue
        break

    try:
        with open(dest, 'wb') as file:
            file.write(response.read())
    finally:
        response.close()
