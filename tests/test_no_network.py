"""Analysis code imports no HTTP client.

Stages (e) through (h) of the pipeline never touch the network. This is
enforceable, so it is enforced.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "argmax"

OFFLINE_PACKAGES = ["analysis", "extract", "verdict", "persist", "datasets"]

FORBIDDEN = {
    "httpx",
    "requests",
    "aiohttp",
    "urllib.request",
    "urllib3",
    "openai",
    "together",
    "socket",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _offline_modules() -> list[Path]:
    return [p for pkg in OFFLINE_PACKAGES for p in (SRC / pkg).rglob("*.py")]


@pytest.mark.parametrize("path", _offline_modules(), ids=lambda p: p.name)
def test_offline_module_imports_no_http_client(path: Path):
    bad = {
        name
        for name in _imports(path)
        for forbidden in FORBIDDEN
        if name == forbidden or name.startswith(f"{forbidden}.")
    }
    assert not bad, f"{path.relative_to(SRC)} imports {sorted(bad)}"


def test_offline_packages_exist():
    """Guards against the parametrization silently collecting nothing."""
    assert len(_offline_modules()) >= len(OFFLINE_PACKAGES)
