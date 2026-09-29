from __future__ import annotations

from zipfile import ZipFile

from cibuildwheel.util.packaging import (
    pep420_namespace_packages,
    with_delvewheel_namespace_pkgs,
)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_WINDOWS_REPAIR = "delvewheel repair -w {dest_dir} -v {wheel}"


def _write_wheel(path: Path, names: list[str]) -> Path:
    with ZipFile(path, "w") as zf:
        for name in names:
            zf.writestr(name, b"#\n")
    return path


def test_detects_top_level_namespace_package(tmp_path: Path) -> None:
    wheel = _write_wheel(
        tmp_path / "ns-1.0-cp312-cp312-win_amd64.whl",
        [
            "company/mod.py",
            "company/ext.pyd",
            "ns-1.0.dist-info/METADATA",
            "ns-1.0.dist-info/RECORD",
        ],
    )

    assert pep420_namespace_packages(wheel) == ("company",)


def test_regular_package_is_not_a_namespace(tmp_path: Path) -> None:
    wheel = _write_wheel(
        tmp_path / "pkg-1.0-cp312-cp312-win_amd64.whl",
        [
            "pkg/__init__.py",
            "pkg/ext.pyd",
            "pkg-1.0.dist-info/METADATA",
        ],
    )

    assert pep420_namespace_packages(wheel) == ()


def test_nested_namespace_collapses_to_deepest_name(tmp_path: Path) -> None:
    wheel = _write_wheel(
        tmp_path / "ns-1.0-cp312-cp312-win_amd64.whl",
        [
            "company/cloud/mod.py",
            "company/cloud/ext.pyd",
            "ns-1.0.dist-info/METADATA",
        ],
    )

    assert pep420_namespace_packages(wheel) == ("company.cloud",)


def test_namespace_parent_with_regular_child(tmp_path: Path) -> None:
    wheel = _write_wheel(
        tmp_path / "ns-1.0-cp312-cp312-win_amd64.whl",
        [
            "company/pkg/__init__.py",
            "company/pkg/ext.pyd",
            "ns-1.0.dist-info/METADATA",
        ],
    )

    assert pep420_namespace_packages(wheel) == ("company",)


def test_ignores_dist_info_and_data_dirs(tmp_path: Path) -> None:
    wheel = _write_wheel(
        tmp_path / "pkg-1.0-cp312-cp312-win_amd64.whl",
        [
            "pkg/__init__.py",
            "pkg-1.0.dist-info/licenses/extra.py",
            "pkg-1.0.data/purelib/notpkg/mod.py",
        ],
    )

    assert pep420_namespace_packages(wheel) == ()


def test_repair_command_adds_namespace_pkg_for_delvewheel() -> None:
    result = with_delvewheel_namespace_pkgs(DEFAULT_WINDOWS_REPAIR, ("company.cloud", "other"))

    assert result == DEFAULT_WINDOWS_REPAIR + ' --namespace-pkg "company.cloud;other"'


def test_repair_command_leaves_non_delvewheel_alone() -> None:
    command = "auditwheel repair -w {dest_dir} {wheel}"

    assert with_delvewheel_namespace_pkgs(command, ("company",)) == command


def test_repair_command_respects_existing_namespace_pkg_flag() -> None:
    command = DEFAULT_WINDOWS_REPAIR + " --namespace-pkg already.set"

    assert with_delvewheel_namespace_pkgs(command, ("company",)) == command


def test_repair_command_noop_without_packages() -> None:
    assert with_delvewheel_namespace_pkgs(DEFAULT_WINDOWS_REPAIR, ()) == DEFAULT_WINDOWS_REPAIR
