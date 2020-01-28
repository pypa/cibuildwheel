
from fnmatch import fnmatch
import subprocess, sys, os, shutil, io, jinja2
from tempfile import mkdtemp
from contextlib import contextmanager


IS_WINDOWS_RUNNING_ON_AZURE = os.path.exists('C:\\hostedtoolcache')
IS_WINDOWS_RUNNING_ON_TRAVIS = os.environ.get('TRAVIS_OS_NAME') == 'windows'


# Python 2 does not have a tempfile.TemporaryDirectory context manager
@contextmanager
def TemporaryDirectoryIfNone(path):
    _path = path or mkdtemp()
    try:
        yield _path
    finally:
        if path is None:
            shutil.rmtree(_path)


def cibuildwheel_get_build_identifiers(project_path, env=None):
    '''
    Returns the list of build identifiers that cibuildwheel will try to build
    for the current platform.
    '''
    cmd_output = subprocess.check_output(
        [sys.executable, '-m', 'cibuildwheel', '--print-build-identifiers', project_path],
        universal_newlines=True,
        env=env,
    )

    return cmd_output.strip().split('\n')


def cibuildwheel_run(project_path, env=None, add_env=None, output_dir=None):
    '''
    Runs cibuildwheel as a subprocess, building the project at project_path.

    Uses the current Python interpreter.

    :param project_path: path of the project to be built.
    :param env: full environment to be used, os.environ if None
    :param add_env: environment used to update env
    :param output_dir: directory where wheels are saved. If None, a temporary
    directory will be used for the duration of the command.
    :return: list of built wheels (file names).
    '''
    if env is None:
        env = os.environ.copy()
        # If present in the host environment, remove the MACOSX_DEPLOYMENT_TARGET for consistency
        env.pop('MACOSX_DEPLOYMENT_TARGET', None)

    if add_env is not None:
        env.update(add_env)

    with TemporaryDirectoryIfNone(output_dir) as _output_dir:
        subprocess.check_call(
            [sys.executable, '-m', 'cibuildwheel', '--output-dir', str(_output_dir), project_path],
            env=env,
        )
        wheels = os.listdir(_output_dir)
    return wheels


def expected_wheels(package_name, package_version, manylinux_versions=['manylinux1', 'manylinux2010'],
                    macosx_deployment_target=None):
    '''
    Returns a list of expected wheels from a run of cibuildwheel.
    '''
    # per PEP 425 (https://www.python.org/dev/peps/pep-0425/), wheel files shall have name of the form
    # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    # {python tag} and {abi tag} are closely related to the python interpreter used to build the wheel
    # so we'll merge them below as python_abi_tag
    python_abi_tags = ['cp27-cp27m', 'cp35-cp35m', 'cp36-cp36m', 'cp37-cp37m', 'cp38-cp38']
    if platform == 'linux':
        python_abi_tags.append('cp27-cp27mu')  # python 2.7 has 2 different ABI on manylinux
        platform_tags = []
        for architecture in ['x86_64', 'i686']:
            for manylinux_version in manylinux_versions:
                platform_tags.append('{manylinux_version}_{architecture}'.format(
                    manylinux_version=manylinux_version, architecture=architecture
                ))
            
        def get_platform_tags(python_abi_tag):
            return platform_tags
        
    elif platform == 'windows':

        def get_platform_tags(python_abi_tag):
            return ['win32', 'win_amd64']
        
    elif platform == 'macos':
        
        def get_platform_tags(python_abi_tag):
            if python_abi_tag == 'cp38-cp38':
                return ['macosx_' + (macosx_deployment_target or "10.9").replace(".", "_") + '_x86_64']
            else:
                return ['macosx_' + (macosx_deployment_target or "10.6").replace(".", "_") + '_intel']
    else:
        raise Exception('unsupported platform')

    templates = []
    for python_abi_tag in python_abi_tags:
        for platform_tag in get_platform_tags(python_abi_tag):
            templates.append('{package_name}-{package_version}-{python_abi_tag}-{platform_tag}.whl'.format(
                package_name=package_name, package_version=package_version,
                python_abi_tag=python_abi_tag, platform_tag=platform_tag
            ))

    if IS_WINDOWS_RUNNING_ON_TRAVIS:
        # Python 2.7 isn't supported on Travis.
        templates = [t for t in templates if '-cp27-' not in t]

    return templates


def generate_project(path, 
                     template_path='./test/project_template',
                     setup_py_add='',
                     setup_py_setup_args_add='',
                     spam_c_top_level_add='',
                     spam_c_function_add='',
                     extra_files=[]):
    ignore_patterns = ['.pytest_*', '*.pyc', '__pycache__', '.DS_Store']

    template_context = dict(
        setup_py_add=setup_py_add,
        setup_py_setup_args_add=setup_py_setup_args_add,
        spam_c_top_level_add=spam_c_top_level_add,
        spam_c_function_add=spam_c_function_add,
    )
    
    for root, dirs, files in os.walk(template_path):
        for name in files+dirs:

            src_path = os.path.join(root, name)
            dst_path = src_path.replace(template_path, path, 1)

            is_dir = (name in dirs)

            if any(fnmatch(name, pattern) for pattern in ignore_patterns):
                if is_dir:
                    dirs.remove(name)
                continue

            if is_dir:
                os.mkdir(src_path)
            else:
                try:
                    with io.open(src_path, encoding='utf8') as f:
                        template = jinja2.Template(f.read())
                    with io.open(dst_path, 'w', encoding='utf8') as f:
                        f.write(template.render(template_context))
                except UnicodeDecodeError:
                    # binary files are copied without variable substitution
                    shutil.copyfile(src_path, dst_path)
    
    for filename, content in extra_files:
        file_path = os.path.join(path, filename)
        try:
            os.makedirs(os.path.dirname(file_path))
        except OSError:
            pass
        with io.open(file_path, 'w', encoding='utf8') as f:
            f.write(content)


platform = None

if "CIBW_PLATFORM" in os.environ:
    platform = os.environ["CIBW_PLATFORM"]
elif sys.platform.startswith("linux"):
    platform = "linux"
elif sys.platform.startswith("darwin"):
    platform = "macos"
elif sys.platform in ["win32", "cygwin"]:
    platform = "windows"
else:
    raise Exception("Unsupported platform")
