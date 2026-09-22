"""TUI screens: five thin presentation views (design 4.6, spec cv-tui).

Each screen composes its OWN Header/Footer: an App-level compose chrome is
covered by pushed screens in Textual 8.2.5 (verified empirically), and the
spec requires the header ("application title and current state") and the
footer ("available key bindings") on the visible screen, so the chrome lives
here with the screens.

Screens hold zero business logic: they render data passed at construction
time and call the callbacks provided by the App (design: "screens only call
callbacks passed by the App — they never import services directly").

All user-visible copy is Spanish (Rioplatense) per spec cv-tui and the
project convention; identifiers and comments are English.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, LoadingIndicator, OptionList, Static

from cvapp.core.discovery import CVSource


class MainScreen(Screen[None]):
    """Main screen: pick a CV from the discovered list.

    Navigation (up/down/enter) is built into OptionList; the highlight never
    wraps (Textual's default — cursor_up/down clamp at the ends). q/esc quit
    through the App's priority bindings.
    """

    def __init__(
        self,
        sources: list[CVSource],
        on_select: Callable[[CVSource], None],
    ) -> None:
        super().__init__()
        self._sources = list(sources)
        self._on_select = on_select
        self.sub_title = f"{len(self._sources)} CVs disponibles"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("🎯 Seleccioná tu CV", id="main-title")
        yield OptionList(*(source.name for source in self._sources), id="cv-list")
        yield Footer()

    def on_option_list_option_selected(self, message: OptionList.OptionSelected) -> None:
        """Enter on a row: hand the selected CV to the App (which renders it)."""
        try:
            source = self._sources[message.option_index]
        except IndexError:
            return
        self._on_select(source)


class EmptyStateScreen(Screen[None]):
    """No CVs found: clear Spanish message + re-scan and quit actions (spec)."""

    BINDINGS = [
        Binding("r", "rescan", "Re-escanear"),
        Binding("R", "rescan", "Re-escanear", show=False),
    ]

    def __init__(self, directory: Path, on_rescan: Callable[[], None]) -> None:
        super().__init__()
        self._directory = directory
        self._on_rescan = on_rescan
        self.sub_title = "Sin CVs"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Static(f"No se encontraron CVs en {self._directory}", id="empty-title"),
            Static("Presioná r para volver a buscar.", classes="hint"),
            id="empty-box",
        )
        yield Footer()

    def action_rescan(self) -> None:
        """r: re-run discovery through the App (may land back on this screen)."""
        self._on_rescan()


class StatusScreen(Screen[None]):
    """Render in progress: animated indicator + which CV is being generated.

    Intentionally has no bindings (design 4.6: "none (render in progress)");
    the App's priority q/esc still quit if the user insists.
    """

    def __init__(self, cv_name: str) -> None:
        super().__init__()
        self._cv_name = cv_name
        self.sub_title = "Generando"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            LoadingIndicator(),
            Static(f"Generando {self._cv_name}…", id="status-message"),
            Static("no cierres la terminal", classes="hint"),
            id="status-box",
        )


class ResultScreen(Screen[None]):
    """Success: PDF path + the three next actions (design 4.6, spec).

    Footer shows "Regenerar otro", "Abrir PDF" and "Salir" (q/esc come from
    the App's priority bindings).
    """

    BINDINGS = [
        Binding("r", "regenerate", "Regenerar otro"),
        Binding("R", "regenerate", "Regenerar otro", show=False),
        Binding("o", "open_pdf", "Abrir PDF"),
        Binding("O", "open_pdf", "Abrir PDF", show=False),
    ]

    def __init__(
        self,
        pdf_path: Path,
        on_regenerate: Callable[[], None],
        on_open_pdf: Callable[[], None],
    ) -> None:
        super().__init__()
        self._pdf_path = pdf_path
        self._on_regenerate = on_regenerate
        self._on_open_pdf = on_open_pdf
        self.sub_title = "Listo"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Static("✅ PDF generado", id="result-title"),
            Static(str(self._pdf_path), id="result-path"),
            Static("¿Qué hacés ahora?", id="result-prompt"),
            id="result-box",
        )
        yield Footer()

    def action_regenerate(self) -> None:
        """r: back to a reloaded main list, same process (no relaunch)."""
        self._on_regenerate()

    def action_open_pdf(self) -> None:
        """o: ask the rendering capability to open the PDF (macOS only)."""
        self._on_open_pdf()


class ErrorScreen(Screen[None]):
    """Failure: friendly Spanish message + retry / back / quit (design 4.6).

    esc quits app-wide because the spec makes the quit bindings (q and esc)
    unconditional; "Volver a la lista" is bound to b (design's esc-volver
    would contradict the spec). Startup-error mode (config failure before
    any CV exists) uses StartupErrorScreen instead — retry and back are not
    bound there and only q/esc quit: "composes only the ErrorScreen" (spec
    cv-config).
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("r", "retry", "Reintentar"),
        Binding("R", "retry", "Reintentar", show=False),
        Binding("b", "back", "Volver a la lista"),
        Binding("B", "back", "Volver a la lista", show=False),
    ]

    def __init__(
        self,
        message: str,
        cv: CVSource | None,
        on_retry: Callable[[], None] | None,
        on_back: Callable[[], None] | None,
    ) -> None:
        super().__init__()
        self._message = message
        self._cv = cv
        self._on_retry = on_retry
        self._on_back = on_back
        self.sub_title = "Error"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Static("❌ No se pudo generar el PDF", id="error-title"),
            Static(self._message, id="error-message"),
            Static("Detalles en cvapp.log", classes="hint"),
            id="error-box",
        )
        yield Footer()

    def action_retry(self) -> None:
        """r: re-run the same CV through the App."""
        if self._on_retry is not None:
            self._on_retry()

    def action_back(self) -> None:
        """b: return to the main list; no render keeps running."""
        if self._on_back is not None:
            self._on_back()


class StartupErrorScreen(Screen[None]):
    """Error screen in startup-error mode: NO retry/back (spec cv-config).

    There is no CV yet when the configuration failed (Settings could not be
    built), so the only actions are the App's quit bindings (q and esc).

    Deliberately NOT a subclass of ErrorScreen: Textual merges base-class
    BINDINGS over the MRO, and an override of `[]` cannot remove inherited
    r/b keys, so a subclass would keep showing Reintentar/Volver. A plain
    Screen with an empty BINDINGS list is the only way to guarantee only the
    quit bindings appear.
    """

    BINDINGS: ClassVar[list[BindingType]] = []

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message
        self.sub_title = "Error"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Static("❌ No se pudo generar el PDF", id="error-title"),
            Static(self._message, id="error-message"),
            Static("Detalles en cvapp.log", classes="hint"),
            id="error-box",
        )
        yield Footer()
