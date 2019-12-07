"""
Utility functions used by the cibuildwheel tests.
"""

import subprocess, sys, os, io, shutil, jinja2
from fnmatch import fnmatch

IS_WINDOWS_RUNNING_ON_AZURE = os.path.exists("C:\\hostedtoolcache")
IS_WINDOWS_RUNNING_ON_TRAVIS = os.environ.get("TRAVIS_OS_NAME") == "windows"


def cibuildwheel_get_build_identifiers(project_path, env=None):
    """
    Returns the list of build identifiers that cibuildwheel will try to build
    for the current platform.
    """
    cmd_output = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "cibuildwheel",
            "--print-build-identifiers",
            project_path,
        ],
        universal_newlines=True,
        env=env,
    )

    return cmd_output.strip().split("\n")


def cibuildwheel_run(project_path, env=None, add_env=None):
    """
    Runs cibuildwheel as a subprocess, building the project at project_path.

    Uses the current Python interpreter.
    Configure settings using env.
    """
    if env is None:
        env = os.environ.copy()

    if add_env is not None:
        env.update(add_env)

    subprocess.check_call(
        [sys.executable, "-m", "cibuildwheel", project_path], env=env,
    )


def expected_wheels(package_name, package_version):
    """
    Returns a list of expected wheels from a run of cibuildwheel.
    """
    if platform == "linux":
        templates = [
            "{package_name}-{package_version}-cp27-cp27m-manylinux1_x86_64.whl",
            "{package_name}-{package_version}-cp27-cp27mu-manylinux1_x86_64.whl",
            "{package_name}-{package_version}-cp35-cp35m-manylinux1_x86_64.whl",
            "{package_name}-{package_version}-cp36-cp36m-manylinux1_x86_64.whl",
            "{package_name}-{package_version}-cp37-cp37m-manylinux1_x86_64.whl",
            "{package_name}-{package_version}-cp38-cp38-manylinux1_x86_64.whl",
            "{package_name}-{package_version}-cp27-cp27m-manylinux2010_x86_64.whl",
            "{package_name}-{package_version}-cp27-cp27mu-manylinux2010_x86_64.whl",
            "{package_name}-{package_version}-cp35-cp35m-manylinux2010_x86_64.whl",
            "{package_name}-{package_version}-cp36-cp36m-manylinux2010_x86_64.whl",
            "{package_name}-{package_version}-cp37-cp37m-manylinux2010_x86_64.whl",
            "{package_name}-{package_version}-cp38-cp38-manylinux2010_x86_64.whl",
            "{package_name}-{package_version}-cp27-cp27m-manylinux1_i686.whl",
            "{package_name}-{package_version}-cp27-cp27mu-manylinux1_i686.whl",
            "{package_name}-{package_version}-cp35-cp35m-manylinux1_i686.whl",
            "{package_name}-{package_version}-cp36-cp36m-manylinux1_i686.whl",
            "{package_name}-{package_version}-cp37-cp37m-manylinux1_i686.whl",
            "{package_name}-{package_version}-cp38-cp38-manylinux1_i686.whl",
            "{package_name}-{package_version}-cp27-cp27m-manylinux2010_i686.whl",
            "{package_name}-{package_version}-cp27-cp27mu-manylinux2010_i686.whl",
            "{package_name}-{package_version}-cp35-cp35m-manylinux2010_i686.whl",
            "{package_name}-{package_version}-cp36-cp36m-manylinux2010_i686.whl",
            "{package_name}-{package_version}-cp37-cp37m-manylinux2010_i686.whl",
            "{package_name}-{package_version}-cp38-cp38-manylinux2010_i686.whl",
        ]
    elif platform == "windows":
        templates = [
            "{package_name}-{package_version}-cp27-cp27m-win32.whl",
            "{package_name}-{package_version}-cp35-cp35m-win32.whl",
            "{package_name}-{package_version}-cp36-cp36m-win32.whl",
            "{package_name}-{package_version}-cp37-cp37m-win32.whl",
            "{package_name}-{package_version}-cp38-cp38-win32.whl",
            "{package_name}-{package_version}-cp27-cp27m-win_amd64.whl",
            "{package_name}-{package_version}-cp35-cp35m-win_amd64.whl",
            "{package_name}-{package_version}-cp36-cp36m-win_amd64.whl",
            "{package_name}-{package_version}-cp37-cp37m-win_amd64.whl",
            "{package_name}-{package_version}-cp38-cp38-win_amd64.whl",
        ]
    elif platform == "macos":
        templates = [
            "{package_name}-{package_version}-cp27-cp27m-macosx_10_6_intel.whl",
            "{package_name}-{package_version}-cp35-cp35m-macosx_10_6_intel.whl",
            "{package_name}-{package_version}-cp36-cp36m-macosx_10_6_intel.whl",
            "{package_name}-{package_version}-cp37-cp37m-macosx_10_6_intel.whl",
            "{package_name}-{package_version}-cp38-cp38-macosx_10_9_x86_64.whl",
        ]
    else:
        raise Exception("unsupported platform")

    if IS_WINDOWS_RUNNING_ON_TRAVIS:
        # Python 2.7 isn't supported on Travis.
        templates = [t for t in templates if "-cp27-" not in t]

    return [
        filename.format(package_name=package_name, package_version=package_version)
        for filename in templates
    ]

def generate_project(path, template_path='./test/project_template',
                     setup_py_add='', extra_files=[]):
    ignore_patterns = ['.pytest_*', '*.pyc', '__pycache__', '.DS_Store']
    template_context = dict(setup_py_add=setup_py_add)
    
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
                    shutil.copyfile(src_path, dst_path)
    
    for filename, content in extra_files:
        file_path = os.path.join(path, filename)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        except FileExistsError:
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
