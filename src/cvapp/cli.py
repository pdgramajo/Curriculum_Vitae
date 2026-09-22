"""Command-line interface: Typer app with tui/list/render/version (design 4.1).

Headless contract (spec cv-cli): application errors (unknown/ambiguous name,
failed render, config error) go to stderr with a plain Spanish message and
exit 1; usage errors exit 2 (Click default); success output goes to stdout and
exits 0. Exit code 10 is never produced anywhere. `render` never opens the
PDF — opening is exclusive to the TUI flow (spec cv-rendering).

Flow (design 3.1): config is loaded once in the callback, before any
subcommand runs, so fail-fast applies uniformly. With no subcommand the
callback opens the TUI instead.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import NoReturn

import typer

from cvapp import __version__
from cvapp.config import ConfigError, Settings, load, setup_logging
from cvapp.core.discovery import (
    AmbiguousCVError,
    UnknownCVError,
    find_cv_sources,
    resolve_cv_by_name,
)
from cvapp.core.rendercv import RenderError, RenderingService

logger = logging.getLogger("cvapp")

app = typer.Typer(help="Generador de CVs con RenderCV.", no_args_is_help=False)


def _project_root() -> Path:
    """CVAPP_PROJECT_ROOT from the launcher, else the current directory.

    The launcher sets the env var; a bare `python -m cvapp` runs from the
    project root (spec: module invocation is equivalent to ./cv).
    """
    env_root = os.environ.get("CVAPP_PROJECT_ROOT")
    return Path(env_root) if env_root else Path.cwd()


def _load_settings_or_exit() -> Settings:
    """Load config + logging for a headless command; fail fast on ConfigError."""
    try:
        settings = load(_project_root())
    except ConfigError as exc:
        logger.error("ConfigError: %s", exc, exc_info=True)
        _fail(str(exc))
    setup_logging(settings)
    return settings


def _fail(message: str) -> NoReturn:
    """Print an application error to stderr and exit 1 (never 10)."""
    typer.echo(f"✗ {message} (detalles en cvapp.log)", err=True)
    raise typer.Exit(1)


def run_tui() -> None:
    """Load config first, then start the Textual TUI (design 3.1).

    On ConfigError the app still starts in a startup-error mode that composes
    only the error screen (spec cv-config); the traceback lands in cvapp.log.
    The TUI module is imported lazily because it exists from Phase 4 on —
    before that, this branch is only reached through tests that patch run_tui.
    """
    try:
        settings = load(_project_root())
    except ConfigError as exc:
        logger.error("ConfigError en el arranque: %s", exc, exc_info=True)
        startup: Settings | ConfigError = exc
    else:
        setup_logging(settings)
        startup = settings

    # Lazy import: cvapp.tui exists from Phase 4 (design 4.6); running this
    # branch before that is impossible unless run_tui is patched in tests.
    from cvapp.tui.app import CVApp  # type: ignore[import-not-found]

    CVApp(startup).run()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Entry point. With no subcommand, opens the interactive TUI."""
    if ctx.invoked_subcommand is None:
        run_tui()
    else:
        ctx.obj = _load_settings_or_exit()


@app.command()
def tui() -> None:
    """Abre la interfaz interactiva (igual que sin argumentos)."""
    run_tui()


@app.command()
def list(ctx: typer.Context) -> None:
    """Lista los CVs disponibles, uno por línea (mismo orden que la TUI)."""
    settings: Settings = ctx.obj
    sources = find_cv_sources(settings.cvs_dir)
    for source in sources:
        typer.echo(source.name)


@app.command()
def render(name: str, ctx: typer.Context) -> None:
    """Genera el PDF del CV indicado y muestra su ruta (no lo abre)."""
    settings: Settings = ctx.obj
    sources = find_cv_sources(settings.cvs_dir)
    try:
        cv = resolve_cv_by_name(sources, name)
    except (UnknownCVError, AmbiguousCVError) as exc:
        _fail(str(exc))
        return
    service = RenderingService(settings)
    try:
        pdf = service.render(cv, open_pdf=False)  # headless never opens (spec)
    except RenderError as exc:
        logger.error("RenderError: %s", exc, exc_info=True)
        _fail(str(exc).strip())
        return
    except Exception as exc:  # unexpected bug: friendly message, log the traceback
        logger.error("Error inesperado al renderizar: %s", exc, exc_info=True)
        _fail("Ocurrió un error inesperado.")
        return
    typer.echo(str(pdf))


@app.command()
def version() -> None:
    """Muestra la versión de la aplicación (cvapp.__version__)."""
    typer.echo(__version__)
