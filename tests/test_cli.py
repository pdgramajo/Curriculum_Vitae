"""Tests for the cvapp CLI (design §4.1, spec cv-cli).

Task 3.1 RED: `cvapp.cli` does not exist yet, so collection fails with
ModuleNotFoundError until 3.2 provides the module. The whole CLI is tested
through typer.testing.CliRunner with config loading, discovery, the rendering
service and run_tui monkeypatched — no real subprocess, no real TUI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import cvapp.cli as cli
from cvapp import __version__
from cvapp.config import ConfigError, Settings
from cvapp.core.discovery import CVSource
from cvapp.core.rendercv import RenderError

runner = CliRunner()


def make_source(name: str) -> CVSource:
    return CVSource(id=name, name=name, path=Path(f"/tmp/cvs/{name}.yaml"))


@pytest.fixture(autouse=True)
def cli_settings(monkeypatch: pytest.MonkeyPatch, project_factory) -> Settings:
    """Every CLI test runs against a tmp project with patched config loading."""
    root = project_factory(cv_stems=["Pablo_Gramajo", "Mi_CV"])
    settings = Settings(project_root=root, cvs_dir=root, output_dir=root / "rendercv_output")
    monkeypatch.setattr(cli, "load", lambda _project_root: settings)
    monkeypatch.setattr(cli, "_project_root", lambda: root)
    return settings


class FakeHolder:
    """Mutable state shared between a test and its patched fake."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []
        self.error: RenderError | None = None
        self.pdf: Path | None = None
        self.tui_calls: int = 0


@pytest.fixture
def fake_service(monkeypatch: pytest.MonkeyPatch):
    """Patches RenderingService with a recording fake (no real subprocess)."""
    holder = FakeHolder()

    class FakeService:
        def __init__(self, settings: Settings) -> None:
            self.settings = settings

        def render(self, cv: CVSource, *, open_pdf: bool = False) -> Path:
            holder.calls.append((cv.name, open_pdf))
            if holder.error is not None:
                raise holder.error
            if holder.pdf is not None:
                return holder.pdf
            return Path(f"/tmp/out/{cv.name}.pdf")

    monkeypatch.setattr(cli, "RenderingService", FakeService)
    return holder


@pytest.fixture
def fake_tui(monkeypatch: pytest.MonkeyPatch):
    """Patches run_tui so the no-args / tui paths never import the TUI module."""
    holder = FakeHolder()

    def _fake_tui() -> None:
        holder.tui_calls += 1

    monkeypatch.setattr(cli, "run_tui", _fake_tui)
    return holder


def test_version_prints_package_version(cli_settings):
    """version prints the single source of truth (cvapp.__version__), exit 0."""
    result = runner.invoke(cli.app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_list_prints_names_in_discovery_order(monkeypatch):
    """list prints names in discovery order (pass-through, no re-sort)."""
    monkeypatch.setattr(
        cli, "find_cv_sources", lambda _dir: [make_source("Beta"), make_source("Alfa")]
    )
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 0
    assert result.stdout == "Beta\nAlfa\n"


def test_list_empty_is_silent_success(monkeypatch):
    """Empty discovery → no output, still exit 0 (spec cv-cli)."""
    monkeypatch.setattr(cli, "find_cv_sources", lambda _dir: [])
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_list_uses_configured_cvs_dir(monkeypatch, cli_settings):
    """list discovers from settings.cvs_dir (resolved against project root)."""
    seen = []

    def _find(cvs_dir: Path) -> list[CVSource]:
        seen.append(cvs_dir)
        return []

    monkeypatch.setattr(cli, "find_cv_sources", _find)
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 0
    assert seen == [cli_settings.cvs_dir]


def test_render_success_prints_pdf_path_and_never_opens(monkeypatch, fake_service):
    """render success: absolute PDF path to stdout, exit 0, open_pdf=False."""
    monkeypatch.setattr(cli, "find_cv_sources", lambda _dir: [make_source("Pablo_Gramajo")])
    result = runner.invoke(cli.app, ["render", "Pablo_Gramajo"])
    assert result.exit_code == 0
    assert result.stdout.strip() == str(Path("/tmp/out/Pablo_Gramajo.pdf"))
    # Headless NEVER opens the PDF, regardless of config (spec cv-rendering).
    assert fake_service.calls == [("Pablo_Gramajo", False)]


def test_render_unknown_name_exits_1(monkeypatch, fake_service):
    """Unknown name → stderr error, exit 1, no render attempted."""
    monkeypatch.setattr(cli, "find_cv_sources", lambda _dir: [make_source("Pablo_Gramajo")])
    result = runner.invoke(cli.app, ["render", "No_Existe"])
    assert result.exit_code == 1
    assert "No se encontró" in result.stderr
    assert "No_Existe" in result.stderr
    assert fake_service.calls == []


def test_render_ambiguous_name_exits_1(monkeypatch, fake_service):
    """Two sources with the same stem → ambiguous error, exit 1, no render."""
    monkeypatch.setattr(
        cli,
        "find_cv_sources",
        lambda _dir: [make_source("Mi_CV"), make_source("Mi_CV")],
    )
    result = runner.invoke(cli.app, ["render", "Mi_CV"])
    assert result.exit_code == 1
    assert "más de un CV" in result.stderr
    assert fake_service.calls == []


def test_render_failure_exits_1(monkeypatch, fake_service):
    """Failed render → RenderError message to stderr, exit 1."""
    monkeypatch.setattr(cli, "find_cv_sources", lambda _dir: [make_source("Pablo_Gramajo")])
    fake_service.error = RenderError("El render tardó más de 120 segundos y se canceló.")
    result = runner.invoke(cli.app, ["render", "Pablo_Gramajo"])
    assert result.exit_code == 1
    assert "120" in result.stderr
    assert "cvapp.log" in result.stderr


def test_config_error_headless_exits_1(monkeypatch):
    """ConfigError on a headless command → stderr naming the file, exit 1."""

    def _raise_config(_root: Path) -> Settings:
        raise ConfigError("cvapp.yaml no es YAML válido: malo")

    monkeypatch.setattr(cli, "load", _raise_config)
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 1
    assert "cvapp.yaml" in result.stderr


def test_no_args_invokes_tui(fake_tui):
    """No arguments → run_tui invoked, TUI quit path exits 0 (spec cv-cli)."""
    result = runner.invoke(cli.app, [])
    assert result.exit_code == 0
    assert fake_tui.tui_calls == 1


def test_tui_subcommand_invokes_tui(fake_tui):
    """Explicit `tui` subcommand behaves identically to no arguments."""
    result = runner.invoke(cli.app, ["tui"])
    assert result.exit_code == 0
    assert fake_tui.tui_calls == 1


def test_unknown_subcommand_is_usage_error():
    """Unknown subcommand → usage error naming it, exit 2 (Click default)."""
    result = runner.invoke(cli.app, ["frobnicate"])
    assert result.exit_code == 2
    assert "frobnicate" in result.stderr


def test_render_missing_argument_is_usage_error():
    """render without a name → usage error (missing argument), non-zero exit."""
    result = runner.invoke(cli.app, ["render"])
    assert result.exit_code == 2
    assert "argument" in result.stderr.lower()
