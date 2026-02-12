from __future__ import annotations

import ast
from pathlib import Path

SRC_PACKAGE_DIR = Path("src/mikroabenteuer")


def _iter_python_modules() -> list[Path]:
    return sorted(
        path for path in SRC_PACKAGE_DIR.glob("*.py") if path.name != "__init__.py"
    )


def test_relative_import_targets_exist_in_src_package() -> None:
    for module_path in _iter_python_modules():
        tree = ast.parse(
            module_path.read_text(encoding="utf-8"), filename=str(module_path)
        )

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level != 1 or node.module is None:
                continue

            target_module = SRC_PACKAGE_DIR / f"{node.module}.py"
            target_package = SRC_PACKAGE_DIR / node.module / "__init__.py"

            assert target_module.exists() or target_package.exists(), (
                f"{module_path} imports '.{node.module}' but no matching module exists "
                f"in {SRC_PACKAGE_DIR}."
            )


def test_src_package_does_not_use_legacy_root_imports() -> None:
    for module_path in _iter_python_modules():
        tree = ast.parse(
            module_path.read_text(encoding="utf-8"), filename=str(module_path)
        )

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("mikroabenteuer")
            ):
                raise AssertionError(
                    f"{module_path} uses legacy absolute import '{node.module}'. "
                    "Use package-local imports under src.mikroabenteuer instead."
                )
