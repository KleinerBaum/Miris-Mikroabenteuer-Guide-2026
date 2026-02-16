"""Smoke test for package import in src-layout installs."""

import mikroabenteuer


def test_import_mikroabenteuer_from_src() -> None:
    """Ensure local package is importable and resolves to src path."""
    assert "mikroabenteuer" in mikroabenteuer.__name__
    assert "src/mikroabenteuer" in mikroabenteuer.__file__.replace("\\", "/")
