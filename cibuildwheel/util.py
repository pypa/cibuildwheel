from fnmatch import fnmatch


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
