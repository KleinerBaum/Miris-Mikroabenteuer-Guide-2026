from __future__ import annotations

from pathlib import Path


FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "src.mikroabenteuer",
    "legacy.v1",
    "import legacy.",
    "from legacy.",
)


def _python_files_to_scan() -> list[Path]:
    files: list[Path] = []
    current_test_file = Path(__file__).resolve()
    for root in (Path("src"), Path("tests")):
        files.extend(
            path
            for path in root.rglob("*.py")
            if path.is_file() and path.resolve() != current_test_file
        )
    files.append(Path("app.py"))
    return files


def test_active_python_files_do_not_use_legacy_or_src_prefixed_imports() -> None:
    matches: list[str] = []

    for path in _python_files_to_scan():
        content = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in content:
                matches.append(f"{path}: {pattern}")
        for line_no, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and "legacy/" in stripped:
                matches.append(f"{path}:{line_no}: {stripped}")

    assert not matches, "Forbidden import layout usage found:\n" + "\n".join(matches)
