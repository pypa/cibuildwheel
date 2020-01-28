import os, shutil, io, jinja2
from fnmatch import fnmatch

DIR = os.path.dirname(__file__)
FILE_IGNORE_PATTERNS = ['.pytest_*', '*.pyc', '__pycache__', '.DS_Store']

class TemplateProject(object):
    def __init__(self, template_path, template_variables, extra_files):
        self.template_path = template_path
        self.template_variables = template_variables
        self.extra_files = extra_files or []
    
    def generate(self, path):
        for root, dirs, files in os.walk(self.template_path):
            for name in files+dirs:

                src_path = os.path.join(root, name)
                dst_path = src_path.replace(self.template_path, path, 1)

                is_dir = (name in dirs)

                if any(fnmatch(name, pattern) for pattern in FILE_IGNORE_PATTERNS):
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
                            f.write(template.render(self.template_variables))
                    except UnicodeDecodeError:
                        # binary files are copied without variable substitution
                        shutil.copyfile(src_path, dst_path)
        
        for filename, content in self.extra_files:
            file_path = os.path.join(path, filename)
            try:
                os.makedirs(os.path.dirname(file_path))
            except OSError:
                pass
            with io.open(file_path, 'w', encoding='utf8') as f:
                f.write(content)


class TemplateProjectC(TemplateProject):
    def __init__(self,
                 setup_py_add='',
                 setup_py_setup_args_add='',
                 spam_c_top_level_add='',
                 spam_c_function_add='',
                 extra_files=None):
        super(TemplateProjectC, self).__init__(
            template_path=os.path.join(DIR, 'project_template'),
            template_variables=dict(
                setup_py_add=setup_py_add,
                setup_py_setup_args_add=setup_py_setup_args_add,
                spam_c_top_level_add=spam_c_top_level_add,
                spam_c_function_add=spam_c_function_add,
            ),
            extra_files=extra_files,
        )

class TemplateProjectCPP(TemplateProject):
    def __init__(self,
                 spam_cpp_top_level_add='',
                 extra_files=None):
        super(TemplateProjectCPP, self).__init__(
            template_path=os.path.join(DIR, 'cpp_project_template'),
            template_variables=dict(
                spam_cpp_top_level_add=spam_cpp_top_level_add,
            ),
            extra_files=extra_files,
        )