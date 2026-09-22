"""Forbidden patterns guard (task 2.9, threat-matrix)."""

from __future__ import annotations

from pathlib import Path


def test_forbidden_patterns_not_present() -> None:
    src_dir = Path("src")
    forbidden = ("shell=True", "os.execv", "osascript")
    violations: list[str] = []
    for pyfile in src_dir.rglob("*.py"):
        try:
            text = pyfile.read_text(encoding="utf-8")
        except Exception:
            continue
        for pat in forbidden:
            if pat in text:
                violations.append(f"{pyfile}:{pat}")
    assert not violations, f"Forbidden patterns found: {violations}"
