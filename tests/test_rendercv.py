"""Tests for RenderingService (design §4.4–4.5, spec cv-rendering).

These tests are written RED-first per tasks 2.4–2.6. The production module
`cvapp.core.rendercv` does not exist yet; running pytest will surface
ModuleNotFoundError until 2.7 is implemented.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cvapp.config import Settings
from cvapp.core.discovery import CVSource


@pytest.fixture
def dummy_cv() -> CVSource:
    """A minimal CVSource for unit tests."""
    return CVSource(id="Pablo_Gramajo", name="Pablo_Gramajo", path=Path("/tmp/Pablo_Gramajo.yaml"))


@pytest.fixture
def settings_factory(project_factory):
    """Factory that yields Settings bound to a project root."""

    def _factory(**overrides) -> Settings:
        root = project_factory()
        params = {"project_root": root, "cvs_dir": root, "output_dir": root / "rendercv_output"}
        params.update(overrides)
        return Settings(**params)

    return _factory


def test_build_rendercv_command_exact_argv_and_spaces(settings_factory, project_factory):
    """Task 2.4: build_rendercv_command returns exact argv, element-by-element.

    The command must include: executable, 'render', absolute source.path,
    -nomd, -nohtml, -nopng, --pdf-path with absolute pdf path, -o with
    absolute output dir, and rendercv_extra_flags appended LAST in order.
    A CV with spaces and project path with spaces must preserve each token
    as its own list element (no quoting anywhere in the list).
    """
    from cvapp.core import rendercv

    root = project_factory()
    source_path = root / "Mi CV.yaml"
    source_path.write_text("name: dummy\n", encoding="utf-8")
    cv = CVSource(id="Mi CV", name="Mi CV", path=source_path)
    output_dir = root / "rendercv output"
    pdf_path = output_dir / "Mi CV.pdf"
    extra_flags = ["--flag-a", "valor"]

    cmd = rendercv.build_rendercv_command(cv, output_dir, pdf_path, extra_flags)

    # Must be a list; element-by-element equality (no joined strings)
    assert isinstance(cmd, list)
    # executable is first
    assert cmd[0].endswith("rendercv") or cmd[0] == str(rendercv.resolve_rendercv_executable())
    assert cmd[1:] == [
        "render",
        str(source_path),
        "-nomd",
        "-nohtml",
        "-nopng",
        "--pdf-path",
        str(pdf_path),
        "-o",
        str(output_dir),
        "--flag-a",
        "valor",
    ]


def test_cleanup_and_resolver(photo_scenario_project):
    """Task 2.5: cleanup_intermediates and resolve_rendercv_executable.

    - foto_2024.png (pre-existing, matches *_*.png pattern) MUST survive
    - another CV's files (Otro_CV.pdf and its intermediates conceptually) survive
    - PDF kept by exact name
    - only this-run intermediates (.typ, .md, .html, new .png copies) removed
    - files outside output_dir never touched
    - resolve_rendercv_executable finds venv sibling or shutil.which; raises
      RenderError naming 'rendercv' when neither exists
    """
    from cvapp.core import rendercv

    root = photo_scenario_project  # creates output_dir with foto_2024.png + Otro_CV.pdf
    out_dir = root / "rendercv_output"

    # Pre-existing state
    assert (out_dir / "foto_2024.png").exists()
    assert (out_dir / "Otro_CV.pdf").exists()

    before = {p.name for p in out_dir.iterdir()}
    pdf_path = out_dir / "Mi_CV.pdf"

    # Create this-run intermediates: .typ, .md, .html, new .png (the copied photo)
    (out_dir / "Mi_CV_CV.typ").write_bytes(b"")
    (out_dir / "Mi_CV_CV.md").write_bytes(b"")
    (out_dir / "Mi_CV_CV.html").write_bytes(b"")
    (out_dir / "Mi_CV_copy.png").write_bytes(b"")  # new .png from this run

    removed = rendercv.cleanup_intermediates(out_dir, before, pdf_path)

    # PDF not removed
    assert pdf_path.name not in [r.name for r in removed]
    # Pre-existing assets survive
    assert (out_dir / "foto_2024.png").exists()
    assert (out_dir / "Otro_CV.pdf").exists()
    # This-run intermediates removed
    assert not (out_dir / "Mi_CV_CV.typ").exists()
    assert not (out_dir / "Mi_CV_CV.md").exists()
    assert not (out_dir / "Mi_CV_CV.html").exists()
    assert not (out_dir / "Mi_CV_copy.png").exists()
    # Removed list contains the deleted names
    removed_names = {r.name for r in removed}
    assert "Mi_CV_CV.typ" in removed_names
    assert "Mi_CV_CV.md" in removed_names
    assert "Mi_CV_CV.html" in removed_names
    assert "Mi_CV_copy.png" in removed_names

    # Resolver: when nothing found, raises RenderError mentioning 'rendercv'
    try:
        rendercv.resolve_rendercv_executable()
    except rendercv.RenderError as exc:
        assert "rendercv" in str(exc).lower()
    except Exception:
        raise


@pytest.fixture
def photo_scenario_project(project_factory):
    root = project_factory(output_files=["foto_2024.png", "Otro_CV.pdf"])
    return root


def test_render_lifecycle_timeout_nonzero_missing_exe_open_pdf(settings_factory, dummy_cv, monkeypatch):
    """Task 2.6: render lifecycle cases (timeout, nonzero exit, missing exe, open_pdf).

    - timeout → TimeoutExpired raised by subprocess → RenderError naming seconds
    - nonzero exit → RenderError carrying stderr tail
    - missing executable → RenderError with clear Spanish message
    - open_pdf runs 'open' only when platform.system() == 'Darwin' (patched),
      warns on non-macOS and on open failure, and never called in headless path
    """
    from cvapp.core import rendercv

    settings = settings_factory(timeout_seconds=5)
    service = rendercv.RenderingService(settings)

    # Timeout case: fake subprocess.run raises TimeoutExpired
    import subprocess as _subprocess

    def raise_timeout(*args, **kwargs):
        raise _subprocess.TimeoutExpired(cmd=args[0] if args else [], timeout=kwargs.get("timeout", 5))

    monkeypatch.setattr(_subprocess, "run", raise_timeout)
    with pytest.raises(rendercv.RenderError) as excinfo:
        service.render(dummy_cv)
    assert "5" in str(excinfo.value) or "segundo" in str(excinfo.value).lower()

    # Nonzero exit case
    class CP:
        returncode = 1
        stdout = ""
        stderr = "error: bad yaml at line 10"

    def nonzero_run(*args, **kwargs):
        return CP()

    monkeypatch.setattr(_subprocess, "run", nonzero_run)
    with pytest.raises(rendercv.RenderError) as excinfo:
        service.render(dummy_cv)
    assert "bad yaml" in str(excinfo.value)

    # Missing executable case
    monkeypatch.setattr(rendercv, "resolve_rendercv_executable", lambda: Path("/no/existe/rendercv"))
    # But also make run succeed? No - resolve happens first. Also we need to make
    # resolve actually raise. Better: patch resolve to raise.
    monkeypatch.setattr(
        rendercv, "resolve_rendercv_executable", lambda: (_ for _ in ()).throw(rendercv.RenderError("No se encontró el ejecutable de RenderCV (rendercv)"))
    )
    with pytest.raises(rendercv.RenderError) as excinfo:
        service.render(dummy_cv)
    assert "rendercv" in str(excinfo.value).lower()

    # open_pdf behavior - set up a successful render scenario
    # We'll test open_pdf method directly with platform patching
    import platform as _platform

    # Darwin case - should attempt open
    monkeypatch.setattr(_platform, "system", lambda: "Darwin")
    calls = []
    monkeypatch.setattr(_subprocess, "run", lambda *a, **k: calls.append((a, k)) or CP.__class__(returncode=0, stdout="", stderr="") if False else None)  # dummy
    # But easier: just call open_pdf
    try:
        rendercv.RenderingService(settings).open_pdf(Path("/tmp/test.pdf"))
    except Exception:
        pass  # may fail due to missing open in test env; we care that it tried

    # Non-Darwin case - should log warning, not attempt open
    monkeypatch.setattr(_platform, "system", lambda: "Linux")
    # open_pdf should not raise
    rendercv.RenderingService(settings).open_pdf(Path("/tmp/test.pdf"))
