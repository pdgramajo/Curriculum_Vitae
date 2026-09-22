"""Shared fixtures for the cvapp test suite (design 8).

These are the backbone of every later test module: project_factory builds
isolated tmp_path projects, sample_sources writes the real CV stem names,
and fake_run makes subprocess.run scriptable for the rendering tests.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# The 11 real CV stems (names only matter for order/listing tests; the real
# CV YAMLs are user data and are never read by unit tests).
REAL_CV_STEMS = [
    "Pablo_Gramajo",
    "Pablo_Gramajo_Analista_Automatizacion_Sr",
    "Pablo_Gramajo_Data_Analist",
    "Pablo_Gramajo_Data_Analist_new",
    "Pablo_Gramajo_FrontEnd2",
    "Pablo_Gramajo_Frontend_CV",
    "Pablo_Gramajo_FullStack_CV",
    "Pablo_Gramajo_FullStack_CV_es",
    "Pablo_Gramajo_Gerente_sistemas",
    "Pablo_Gramajo_Net_CV",
    "Pablo_Gramajo_react_CV",
]


@pytest.fixture
def project_factory(tmp_path: Path):
    """Builds a tmp_path project with optional cvapp.yaml / CVs / output files.

    Returns a factory that creates a fresh project per test and returns its
    root Path. config_text is written verbatim as cvapp.yaml (raw YAML text
    keeps the tests independent of any YAML library); cv_stems become empty
    `*.yaml` files; output_files become empty files inside rendercv_output/.
    """

    def _factory(
        *,
        config_text: str | None = None,
        cv_stems: list[str] | None = None,
        output_files: list[str] | None = None,
    ) -> Path:
        root = tmp_path / "project"
        root.mkdir()
        if config_text is not None:
            (root / "cvapp.yaml").write_text(config_text, encoding="utf-8")
        if cv_stems:
            for stem in cv_stems:
                (root / f"{stem}.yaml").write_text("name: dummy\n", encoding="utf-8")
        if output_files:
            out_dir = root / "rendercv_output"
            out_dir.mkdir()
            for name in output_files:
                (out_dir / name).write_bytes(b"")
        return root

    return _factory


@pytest.fixture
def sample_sources(tmp_path: Path) -> Path:
    """A directory with empty files named after the 11 real CV stems."""
    root = tmp_path / "cvs"
    root.mkdir()
    for stem in REAL_CV_STEMS:
        (root / f"{stem}.yaml").touch()
    return root


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch):
    """Patches subprocess.run so tests can script the result and inspect calls.

    Set ``fake.result`` to a CompletedProcess, or ``fake.error`` to an
    exception to raise (e.g. TimeoutExpired, FileNotFoundError). Every call is
    recorded in ``fake.calls`` as (args, kwargs).
    """

    class FakeRun:
        def __init__(self) -> None:
            self.result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            self.error: BaseException | None = None
            self.calls: list[tuple[tuple, dict]] = []

        def run(self, *args, **kwargs) -> subprocess.CompletedProcess:
            self.calls.append((args, kwargs))
            if self.error is not None:
                raise self.error
            return self.result

    fake = FakeRun()
    monkeypatch.setattr(subprocess, "run", fake.run)
    return fake
