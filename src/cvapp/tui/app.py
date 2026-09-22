"""Textual app: thin presentation layer that routes screens and workers.

Design 4.6 (cv-tui-redesign), spec cv-tui. The App owns no business logic:
discovery and rendering live in cvapp.core.* and are reached through a
lazily built RenderingService. Renders run in an exclusive thread worker so
the UI stays responsive (spec: "keeps responding and shows status while
rendering") and a second render can never start while one is in progress
(exclusive=True; spec: "Concurrent renders are prevented").

All user-visible copy is Spanish (Rioplatense) per spec cv-tui and the
project convention; identifiers and comments are English.
"""

from __future__ import annotations

import logging
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import Screen

from cvapp.config import ConfigError, Settings
from cvapp.core.discovery import CVSource, find_cv_sources
from cvapp.core.rendercv import RenderError, RenderingService
from cvapp.tui.screens import (
    EmptyStateScreen,
    ErrorScreen,
    MainScreen,
    ResultScreen,
    StartupErrorScreen,
    StatusScreen,
)

logger = logging.getLogger("cvapp")


class RenderFinished(Message):
    """Posted by the render worker after a successful render."""

    def __init__(self, pdf: Path) -> None:
        super().__init__()
        self.pdf = pdf


class RenderFailed(Message):
    """Posted by the render worker after a failed render."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message


class CVApp(App[None]):
    """The Textual application (design 4.6).

    Routes screens, launches the render worker and owns zero business logic.
    Given a ``ConfigError`` (startup-error mode, from cli.run_tui) the app
    composes only the ErrorScreen with the config message (spec cv-config:
    "the TUI shows the error screen"; no render is attempted).
    """

    TITLE = "Generador de CVs"

    CSS = """
    Screen {
        align: center middle;
    }

    #main-title, #empty-title, #result-title, #error-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #result-title {
        color: $success;
    }

    #error-title {
        color: $error;
    }

    #result-path {
        text-align: center;
        margin-bottom: 1;
    }

    #result-prompt {
        text-align: center;
    }

    #error-message {
        text-align: center;
        color: $text;
        margin-bottom: 1;
    }

    #status-message {
        text-align: center;
        margin-top: 1;
    }

    .hint {
        color: $text-muted;
        text-align: center;
    }

    #cv-list {
        width: 60%;
        min-width: 40;
        height: auto;
        max-height: 80%;
        border: round $primary;
        padding: 1 2;
        margin: 0 0 1 0;
    }

    LoadingIndicator {
        width: 40%;
        min-width: 20;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("q", "quit_app", "Salir", priority=True),
        Binding("Q", "quit_app", "Salir", priority=True, show=False),
        Binding("escape", "quit_app", "Salir", priority=True),
    ]

    def __init__(self, settings_or_error: Settings | ConfigError) -> None:
        super().__init__()
        self._settings: Settings | None = None
        self._startup_error: ConfigError | None = None
        if isinstance(settings_or_error, Settings):
            self._settings = settings_or_error
        else:
            self._startup_error = settings_or_error
        self._rendering: RenderingService | None = None
        self._current_cv: CVSource | None = None

    @property
    def settings(self) -> Settings:
        """The loaded settings; only valid outside startup-error mode."""
        if self._settings is None:
            raise RuntimeError("settings no disponibles en modo error de arranque")
        return self._settings

    @property
    def rendering(self) -> RenderingService:
        """Lazily built RenderingService, shared across every render."""
        if self._rendering is None:
            self._rendering = RenderingService(self.settings)
        return self._rendering

    def compose(self) -> ComposeResult:
        # Intentionally empty: every screen composes its own Header/Footer.
        # App-level chrome is covered by pushed screens in Textual (verified
        # with 8.2.5), and the spec requires header/footer on each screen.
        yield from ()

    def on_mount(self) -> None:
        """Push the initial screen: error screen on config failure, else list."""
        if self._startup_error is not None:
            self.push_screen(StartupErrorScreen(message=str(self._startup_error)))
            return
        self.push_screen(self._make_main_screen())

    def _make_main_screen(self) -> Screen[None]:
        """Re-run discovery and build the list or empty-state screen."""
        settings = self.settings
        sources = find_cv_sources(settings.cvs_dir)
        if not sources:
            return EmptyStateScreen(directory=settings.cvs_dir, on_rescan=self._rescan)
        return MainScreen(sources=sources, on_select=self._start_render)

    def _start_render(self, cv: CVSource) -> None:
        """Enter on a CV: show the status view and run the render worker."""
        self._current_cv = cv
        self.push_screen(StatusScreen(cv_name=cv.name))
        self.render_worker(cv)

    @work(exclusive=True, thread=True)
    def render_worker(self, cv: CVSource) -> None:
        """Render in a background thread; the UI keeps responding meanwhile.

        exclusive=True silently skips a second call while one render is in
        flight (spec: no concurrent renders). Success/failure is reported
        back to the App through post_message (worker -> UI channel).
        """
        try:
            pdf = self.rendering.render(cv, open_pdf=True)
        except RenderError as exc:
            logger.error("RenderError: %s", exc, exc_info=True)
            self.post_message(RenderFailed(str(exc)))
        except Exception as exc:  # unexpected bug: friendly message, log traceback
            logger.error("Error inesperado al renderizar: %s", exc, exc_info=True)
            self.post_message(RenderFailed("Ocurrió un error inesperado. Detalles en cvapp.log."))
        else:
            self.post_message(RenderFinished(pdf))

    def on_render_finished(self, message: RenderFinished) -> None:
        """Route success: replace the status view with the result screen."""
        self.switch_screen(
            ResultScreen(
                pdf_path=message.pdf,
                on_regenerate=self._regenerate_another,
                on_open_pdf=lambda: self.rendering.open_pdf(message.pdf),
            )
        )

    def on_render_failed(self, message: RenderFailed) -> None:
        """Route failure: show the error screen; the app stays alive (spec)."""
        self.switch_screen(
            ErrorScreen(
                message=message.message,
                cv=self._current_cv,
                on_retry=self._retry,
                on_back=self._back_to_list,
            )
        )

    def _regenerate_another(self) -> None:
        """r on the result screen: reloaded list, SAME process (no relaunch)."""
        self.switch_screen(self._make_main_screen())

    def _retry(self) -> None:
        """r on the error screen: re-run the same CV."""
        cv = self._current_cv
        if cv is None:
            return
        self.push_screen(StatusScreen(cv_name=cv.name))
        self.render_worker(cv)

    def _back_to_list(self) -> None:
        """b on the error screen: back to the list, nothing keeps running."""
        self._current_cv = None
        self.switch_screen(self._make_main_screen())

    def _rescan(self) -> None:
        """r on the empty state: re-run discovery (may now land on the list)."""
        self.switch_screen(self._make_main_screen())

    def action_quit_app(self) -> None:
        """q/esc: exit the TUI only, leaving the Terminal open (spec cv-tui)."""
        # App[None] -> exit() with no result; Textual returns None and the
        # process exits with code 0 (spec: "exits with code 0").
        self.exit()
