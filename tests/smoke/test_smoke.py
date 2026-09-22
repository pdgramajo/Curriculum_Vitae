"""Opt-in real RenderCV smoke test (task 5.6, design 8).

Runs ONLY with `pytest -m smoke` — never in the default suite (real RenderCV
work). Copies a real CV YAML from the repo root (read-only), pre-creates a
photo tripwire (foto_2024.png, which matches the old destructive `*_*.png`
cleanup pattern), renders through the real RenderingService, and asserts:
PDF exists at `<output_dir>/<stem>.pdf`, the run succeeds (exit-0 flow), the
`.typ` intermediate was removed, and the photo survives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cvapp.config import Settings
from cvapp.core.discovery import find_cv_sources
from cvapp.core.rendercv import RenderingService

pytestmark = pytest.mark.smoke

_SOURCE_CV = Path(__file__).resolve().parents[2] / "Pablo_Gramajo.yaml"


def test_real_rendercv_render_is_clean_and_photo_safe(tmp_path: Path) -> None:
    """Real render of a copied CV: PDF produced, intermediates gone, photo intact."""
    if not _SOURCE_CV.is_file():
        pytest.skip(
            "Pablo_Gramajo.yaml no está en la raíz del repo; "
            "este smoke test corre desde el proyecto."
        )

    cvs_dir = tmp_path / "cvs"
    output_dir = tmp_path / "out"
    cvs_dir.mkdir()
    output_dir.mkdir()
    # Photo tripwire: pre-existing file that matches the old *_*.png glob and
    # MUST survive cleanup (spec cv-rendering, design 4.5).
    (output_dir / "foto_2024.png").write_bytes(b"tripwire")

    (cvs_dir / _SOURCE_CV.name).write_bytes(_SOURCE_CV.read_bytes())

    settings = Settings(
        project_root=tmp_path,
        cvs_dir=cvs_dir,
        output_dir=output_dir,
        open_pdf_after=False,  # headless: never opens (spec cv-rendering)
    )

    sources = find_cv_sources(settings.cvs_dir)
    assert [s.name for s in sources] == ["Pablo_Gramajo"]

    pdf = RenderingService(settings).render(sources[0], open_pdf=False)

    expected_pdf = output_dir / "Pablo_Gramajo.pdf"
    assert pdf == expected_pdf
    assert expected_pdf.is_file()
    assert expected_pdf.stat().st_size > 0

    # This-run intermediates (.typ/.md/.html) must be gone; the deliverable
    # and the pre-existing photo must remain.
    leftovers = [
        p.name for p in output_dir.iterdir() if p.suffix.lower() in {".typ", ".md", ".html"}
    ]
    assert leftovers == [], f"intermediates left behind: {leftovers}"
    assert (output_dir / "foto_2024.png").exists(), "photo tripwire was deleted"
