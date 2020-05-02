
import jinja2
from .base import TemplateProject


setup_py_template = r'''
from setuptools import setup, Extension

{{ setup_py_add }}

setup(
    {{ setup_py_setup_args_add | indent(4) }}
)
'''

setup_cfg_template = r'''
[metadata]
name = spam
version = 0.1.0

{{ setup_cfg_add }}
'''


class SetuptoolsTemplateProject(TemplateProject):
    def __init__(self, *, setup_py_add='', setup_py_setup_args_add='', setup_cfg_add=''):
        super().__init__()

        self.files.update({
            'setup.py': jinja2.Template(setup_py_template),
            'setup.cfg': jinja2.Template(setup_cfg_template),
        })

        self.template_context.update({
            'setup_py_add': setup_py_add,
            'setup_py_setup_args_add': setup_py_setup_args_add,
            'setup_cfg_add': setup_cfg_add,
        })
