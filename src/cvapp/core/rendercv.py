"""RenderingService: safe subprocess wrapper around RenderCV (design §4.4–4.5).

Pure helpers are unit-tested without spawning subprocesses; the service maps
subprocess outcomes to RenderError and enforces timeout/cleanup/open-PDF
semantics (no forbidden subprocess patterns).
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from cvapp.config import Settings
from cvapp.core.discovery import CVSource

logger = logging.getLogger("cvapp")


class RenderError(Exception):
    """User-facing render failure; message is safe to show in the TUI/CLI."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def resolve_rendercv_executable() -> Path:
    """Find the RenderCV executable.

    Try venv sibling of sys.executable first, then shutil.which("rendercv").
    Raises RenderError naming 'rendercv' if neither exists.
    """
    # Prefer the venv's rendercv next to the interpreter
    candidate = Path(sys.executable).with_name("rendercv")
    if candidate.exists():
        return candidate

    found = shutil.which("rendercv")
    if found:
        return Path(found)

    raise RenderError("No se encontró el ejecutable de RenderCV (rendercv). Reinstalalo en .venv.")


def build_rendercv_command(
    source: CVSource,
    output_dir: Path,
    pdf_path: Path,
    extra_flags: list[str],
) -> list[str]:
    """Build exact argv for RenderCV (design §5.1).

    Returns: [executable, "render", source.path (abs), -nomd, -nohtml, -nopng,
    --pdf-path (abs), -o (abs output_dir), *extra_flags]
    All paths are absolute; extra_flags appended LAST in order.
    """
    exe = resolve_rendercv_executable()
    cmd: list[str] = [
        str(exe),
        "render",
        str(Path(source.path).resolve()),
        "-nomd",
        "-nohtml",
        "-nopng",
        "--pdf-path",
        str(Path(pdf_path).resolve()),
        "-o",
        str(Path(output_dir).resolve()),
    ]
    cmd.extend(extra_flags)
    return cmd


def snapshot_output_dir(output_dir: Path) -> set[str]:
    """Snapshot filenames present in output_dir before the run."""
    try:
        return {p.name for p in output_dir.iterdir()}
    except FileNotFoundError:
        return set()


def cleanup_intermediates(output_dir: Path, before: set[str], pdf_path: Path) -> list[Path]:
    """Delete ONLY files created by this run with intermediate extensions.

    - Skip anything in 'before' (pre-existing photos/other CVs' files)
    - Never touch the PDF (matched by exact name)
    - Only consider suffixes in {.typ,.md,.html,.png}
    - Iterate only inside output_dir
    """
    removed: list[Path] = []
    pdf_resolved = Path(pdf_path).resolve()
    try:
        out = Path(output_dir).resolve()
    except Exception:
        return removed

    try:
        for candidate in out.iterdir():
            if candidate.name in before:
                continue
            try:
                if candidate.resolve() == pdf_resolved:
                    continue
            except Exception:
                pass
            if candidate.suffix.lower() in {".typ", ".md", ".html", ".png"}:
                try:
                    candidate.unlink(missing_ok=True)
                    removed.append(candidate)
                except Exception:
                    logger.debug("cleanup: no se pudo borrar %s", candidate, exc_info=True)
    except FileNotFoundError:
        pass
    return removed


class RenderingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def render(self, cv: CVSource, *, open_pdf: bool = False) -> Path:
        """Render cv -> <output_dir>/<stem>.pdf. Raises RenderError on failure."""
        output_dir = self.settings.output_dir
        if not output_dir.is_absolute():
            output_dir = self.settings.project_root / output_dir
        pdf_path = output_dir / f"{cv.name}.pdf"

        before = snapshot_output_dir(output_dir)
        try:
            cmd = build_rendercv_command(
                cv, output_dir, pdf_path, list(self.settings.rendercv_extra_flags)
            )
        except RenderError:
            raise

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.settings.timeout_seconds,
            )
        except FileNotFoundError:
            raise RenderError("No se encontró el ejecutable de RenderCV (rendercv).")
        except subprocess.TimeoutExpired:
            raise RenderError(
                f"El render tardó más de {self.settings.timeout_seconds} segundos y se canceló."
            )

        if result.returncode != 0:
            stderr = result.stderr or ""
            # Keep tail for user message
            msg = stderr[-400:] if len(stderr) > 400 else stderr
            if not msg:
                msg = "RenderCV falló sin mensaje de error."
            raise RenderError(msg.strip() or "RenderCV falló.")

        if not pdf_path.is_file():
            raise RenderError(
                "RenderCV terminó sin error pero no generó el PDF en la ruta esperada."
            )

        cleanup_intermediates(output_dir, before, pdf_path)

        if open_pdf and self.settings.open_pdf_after:
            self.open_pdf(pdf_path)

        return pdf_path

    def open_pdf(self, pdf_path: Path) -> None:
        """macOS 'open' only; failure logs warning, never fails render."""
        if platform.system() != "Darwin":
            logger.warning(
                "open_pdf_after está activo pero no estamos en macOS; no se abre el PDF."
            )
            return
        try:
            subprocess.run(["open", str(Path(pdf_path))], check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            logger.warning("No se pudo abrir el PDF con 'open': %s", exc)
