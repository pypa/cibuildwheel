from configparser import ConfigParser
from pathlib import Path
from typing import Any, MutableMapping, Optional

import toml
from packaging.specifiers import SpecifierSet


class NoProjectFileError(RuntimeError):
    pass


class ProjectFile:
    def __init__(self, package_dir: Path) -> None:
        setup_py = package_dir / "setup.py"
        self.setup_py: Optional[Path] = setup_py if setup_py.exists() else None

        setup_cfg = package_dir / "setup.cfg"
        self.setup_cfg: Optional[ConfigParser]
        try:
            config = ConfigParser()
            config.read(setup_cfg)
            self.setup_cfg = config
        except FileNotFoundError:
            self.setup_cfg = None

        pyproject_toml = package_dir / 'pyproject.toml'
        self.pyproject_toml: Optional[MutableMapping[str, Any]]
        try:
            self.pyproject_toml = toml.load(pyproject_toml)
        except FileNotFoundError:
            self.pyproject_toml = None

        if self.setup_py is None and self.setup_cfg is None and self.pyproject_toml is None:
            raise NoProjectFileError('Could not find setup.py, setup.cfg, or pyproject.toml at root of package')

    def get_requires_python(self) -> Optional[SpecifierSet]:
        if self.pyproject_toml is not None:
            try:
                return SpecifierSet(self.pyproject_toml['project']['requires-python'])
            except KeyError:
                pass

        if self.setup_cfg is not None:
            try:
                return SpecifierSet(self.setup_cfg['options']['python_requires'])
            except KeyError:
                pass

        return None
