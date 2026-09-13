from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[1] / "src" / "bh_sim"
PACKAGE_NAME = "bh_sim"
QT_MODULES = ("PySide6", "PyQt6", "PySide2", "PyQt5", "qtpy")
PROTOTYPE_MODULES = tuple(
    f"{PACKAGE_NAME}.{name}"
    for name in ("audit", "numerics", "radiators", "stream", "thermo", "transients", "unit_ops")
)


def imported_modules(path: Path, package_root: Path = PACKAGE) -> set[str]:
    """Resolve imports from every AST scope, including relative child imports.

    ``from . import adapter`` and ``from package import adapter`` include the
    candidate child module so neither syntax bypasses a forbidden-layer check.
    Literal dynamic imports are also recognized; runtime probes cover imports
    whose target is computed rather than expressed as a string literal.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"))
    relative = path.relative_to(package_root)
    containing_package = [PACKAGE_NAME, *relative.parts[:-1]]
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                assert node.level <= len(containing_package), f"invalid relative import in {path}"
                base_parts = containing_package[: len(containing_package) - node.level + 1]
                if node.module:
                    base_parts.extend(node.module.split("."))
                base = ".".join(base_parts)
            else:
                base = node.module or ""
            if base:
                modules.add(base)
                modules.update(f"{base}.{alias.name}" for alias in node.names if alias.name != "*")
        elif (
            isinstance(node, ast.Call)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "__import__")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "import_module")
            )
        ):
            modules.add(node.args[0].value)
    return modules


def matches_module(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)


def layer_import_violations(folders: tuple[str, ...], forbidden: tuple[str, ...]) -> list[str]:
    violations = []
    for folder in folders:
        for path in (PACKAGE / folder).rglob("*.py"):
            for module in imported_modules(path):
                if matches_module(module, forbidden):
                    violations.append(f"{path.relative_to(PACKAGE)} -> {module}")
    return sorted(violations)


def test_kernel_does_not_import_ui_api_or_storage_adapters() -> None:
    forbidden = (
        "bh_sim.api",
        "bh_sim.application",
        "bh_sim.adapters",
        "bh_sim.composition",
        "bh_sim.persistence",
        "bh_sim.uix",
        "fastapi",
        "pydantic",
        "sqlite3",
        *QT_MODULES,
    )
    assert layer_import_violations(("core", "engine", "solvers"), forbidden) == []


def test_application_policy_uses_ports_instead_of_concrete_adapters() -> None:
    forbidden = (
        "bh_sim.api",
        "bh_sim.adapters",
        "bh_sim.composition",
        "bh_sim.engine",
        "bh_sim.persistence",
        "bh_sim.solvers",
        "fastapi",
        "pydantic",
        "pint",
        "networkx",
        "numpy",
        "scipy",
        "sqlite3",
        *PROTOTYPE_MODULES,
        *QT_MODULES,
    )
    assert layer_import_violations(("application",), forbidden) == []


def test_neutral_boundary_source_depends_only_on_itself_and_stdlib() -> None:
    boundary = PACKAGE / "boundary"
    if not boundary.exists():
        pytest.skip("DW1 neutral boundary has not been introduced yet")
    violations = []
    for path in boundary.rglob("*.py"):
        for module in imported_modules(path):
            if module.split(".")[0] in sys.stdlib_module_names:
                continue
            if module == PACKAGE_NAME or matches_module(module, (f"{PACKAGE_NAME}.boundary",)):
                continue
            violations.append(f"{path.relative_to(PACKAGE)} -> {module}")
    assert sorted(violations) == []


def test_neutral_boundary_imports_in_a_process_without_scientific_or_ui_packages() -> None:
    if not (PACKAGE / "boundary" / "__init__.py").exists():
        pytest.skip("DW1 neutral boundary has not been introduced yet")
    # Start a fresh interpreter: a parent package's eager exports must not defeat
    # neutrality even if the boundary's own source imports only the standard library.
    probe = """
import importlib
import importlib.abc
import pkgutil
import sys

class NeutralBoundaryOnly(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split('.')[0]
        if fullname == 'bh_sim' or fullname.startswith('bh_sim.boundary'):
            return None
        if root in sys.stdlib_module_names:
            return None
        raise AssertionError('neutral import attempted: ' + fullname)

sys.meta_path.insert(0, NeutralBoundaryOnly())
boundary = importlib.import_module('bh_sim.boundary')
for module in pkgutil.walk_packages(boundary.__path__, boundary.__name__ + '.'):
    importlib.import_module(module.name)
for name in getattr(boundary, '__all__', ()):
    getattr(boundary, name)
for name in sys.modules:
    if name.startswith('bh_sim.'):
        assert name.startswith('bh_sim.boundary'), name
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(PACKAGE.parent)},
    )
    assert result.returncode == 0, result.stderr


def test_import_scanner_resolves_nested_relative_and_child_imports(tmp_path: Path) -> None:
    nested = tmp_path / "application" / "nested"
    nested.mkdir(parents=True)
    source = nested / "policy.py"
    source.write_text(
        "from ... import engine\n"
        "from ...persistence import PersistenceStore\n"
        "from ..ports import RunPort\n"
        "from . import helper\n"
        "def deferred():\n"
        "    from bh_sim import adapters\n",
        encoding="utf-8",
    )
    found = imported_modules(source, tmp_path)
    assert {
        "bh_sim.engine",
        "bh_sim.persistence",
        "bh_sim.application.ports",
        "bh_sim.application.nested.helper",
        "bh_sim.adapters",
    } <= found


def test_browser_layer_contains_no_python_or_kernel_imports() -> None:
    web_source = Path(__file__).parents[1] / "web" / "src"
    contents = "\n".join(
        path.read_text(encoding="utf-8") for path in web_source.rglob("*") if path.is_file()
    )
    assert "bh_sim" not in contents
    assert "scipy" not in contents.lower()


def test_native_uix_imports_only_neutral_contracts_qt_and_stdlib() -> None:
    allowed = (f"{PACKAGE_NAME}.boundary", f"{PACKAGE_NAME}.uix")
    qt = ("PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets")
    violations = []
    for path in (PACKAGE / "uix").rglob("*.py"):
        for module in imported_modules(path):
            if module.split(".")[0] in sys.stdlib_module_names:
                continue
            if matches_module(module, (*allowed, *qt)):
                continue
            violations.append(f"{path.relative_to(PACKAGE)} -> {module}")
    assert violations == []


def test_native_preview_operates_with_scientific_imports_blocked(tmp_path: Path) -> None:
    if importlib.util.find_spec("PySide6") is None:
        pytest.skip("optional desktop runtime is not installed")
    probe = """
import importlib.abc
import sys
from pathlib import Path

blocked = (
    'bh_sim.core', 'bh_sim.engine',
    'bh_sim.solvers', 'bh_sim.composition',
    'bh_sim.persistence', 'bh_sim.adapters.storage',
    'bh_sim.adapters.engineering', 'bh_sim.adapters.demo',
    'bh_sim.audit', 'bh_sim.numerics',
    'bh_sim.radiators', 'bh_sim.stream',
    'bh_sim.thermo', 'bh_sim.transients',
    'bh_sim.unit_ops', 'numpy', 'scipy', 'pint', 'networkx', 'fastapi'
)
def forbidden(name):
    return any(name == root or name.startswith(root + '.') for root in blocked)
class NoScientificRuntime(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if forbidden(fullname):
            raise AssertionError('native preview attempted forbidden import: ' + fullname)
sys.meta_path.insert(0, NoScientificRuntime())
from PySide6.QtWidgets import QApplication
from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.uix.window import WorkstationWindow
from bh_sim.uix.workspace import WorkspaceSettings
app = QApplication([])
root = Path(sys.argv[1])
window = WorkstationWindow(create_preview_gateway(root), WorkspaceSettings(root / 'layout.ini'))
assert window.create_draft('Isolated preview')
assert window.save_current()
window.close_draft()
assert window.open_draft('Isolated preview')
assert window.close()
assert not any(forbidden(name) for name in sys.modules)
print('PASS: native create/save/open without scientific runtime or FastAPI')
"""
    result = subprocess.run(
        [sys.executable, "-c", probe, str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(PACKAGE.parent), "QT_QPA_PLATFORM": "offscreen"},
    )
    assert result.returncode == 0, result.stderr


def test_missing_desktop_dependency_reports_explicit_capability() -> None:
    probe = """
import importlib.abc
import runpy
import sys
class NoQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == 'PySide6':
            raise ImportError('desktop runtime intentionally absent')
sys.meta_path.insert(0, NoQt())
runpy.run_module('bh_sim.desktop_launcher', run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", probe], check=False, capture_output=True, text=True, timeout=10
    )
    assert result.returncode != 0
    assert "DESKTOP_RUNTIME_UNAVAILABLE" in result.stderr
    assert "install the optional desktop dependencies" in result.stderr
