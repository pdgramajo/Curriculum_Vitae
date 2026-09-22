#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Static

SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "rendercv_output"

EXIT_CLOSE_TERMINAL = 10


def find_yaml_files():
    yaml_files = []
    for pattern in ["*.yaml", "*.yml"]:
        yaml_files.extend(SCRIPT_DIR.glob(pattern))
    yaml_files = sorted(set(yaml_files))
    return [f for f in yaml_files if f.is_file() and not f.name.startswith(".")]


def generate_cv(filename: str, basename: str) -> bool:
    output_file = OUTPUT_DIR / f"{basename}.pdf"

    if output_file.exists():
        output_file.unlink()

    cmd = f'rendercv render "{filename}" -nomd -nohtml -nopng --pdf-path "rendercv_output/{basename}.pdf"'

    subprocess.run(
        cmd,
        shell=True,
        executable="/bin/zsh",
        capture_output=False
    )

    if output_file.exists():
        for ext in [".typ", ".md", ".html"]:
            for f in OUTPUT_DIR.glob(f"*{ext}"):
                try:
                    f.unlink()
                except:
                    pass
        for f in list(OUTPUT_DIR.glob("*_*.png")):
            try:
                f.unlink()
            except:
                pass

        subprocess.run(["open", str(output_file)], check=True)
        return True
    return False


class CVSelector(App):
    CSS = """
    Screen {
        align: center middle;
    }

    #main-container {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
    }

    #list {
        margin: 1 0;
    }

    .cv-item {
        padding: 0 1;
    }

    .selected {
        background: $primary;
        text-style: bold;
    }

    .hint {
        color: $text-muted;
    }

    .success-msg {
        color: $success;
    }

    .error-msg {
        color: $error;
    }

    .menu-item {
        padding: 0 1;
    }

    .menu-selected {
        background: $primary;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("up", "move_up", "Arriba", show=False),
        Binding("down", "move_down", "Abajo", show=False),
        Binding("enter", "execute", "Ejecutar", show=False),
        Binding("escape", "quit", "Salir", show=False),
    ]

    yaml_files = []
    selected_idx = 0
    is_menu = False
    menu_options = []

    def __init__(self):
        super().__init__()
        self.yaml_files = find_yaml_files()
        self.selected_idx = 0
        self.is_menu = False
        self.menu_options = []

    def compose(self) -> ComposeResult:
        options = [f.stem for f in self.yaml_files]

        yield Container(
            Static("🎯 Seleccioná tu CV", id="title"),
            Vertical(*[Static(f"  {i+1}. {opt}", id=f"cv-{i}") for i, opt in enumerate(options)], id="list"),
            Static("↑↓ para navegar | ENTER para generar", id="hint"),
            Static("[R] Regenerar otro  |  [Q] Salir", id="hint2"),
            id="main-container"
        )

    def on_mount(self) -> None:
        self.update_selection()

    def update_selection(self):
        if self.is_menu:
            for i in range(len(self.menu_options)):
                item = self.query_one(f"#menu-{i}", Static)
                if i == self.selected_idx:
                    item.update(f"▸ {self.menu_options[i]}")
                    item.add_class("menu-selected")
                else:
                    item.update(f"  {self.menu_options[i]}")
                    item.remove_class("menu-selected")
        else:
            for i in range(len(self.yaml_files)):
                item = self.query_one(f"#cv-{i}", Static)
                if i == self.selected_idx:
                    item.update(f"▸ {i+1}. {self.yaml_files[i].stem}")
                    item.add_class("selected")
                else:
                    item.update(f"  {i+1}. {self.yaml_files[i].stem}")
                    item.remove_class("selected")

    def action_move_up(self):
        if self.selected_idx > 0:
            self.selected_idx -= 1
            self.update_selection()

    def action_move_down(self):
        max_idx = len(self.menu_options) - 1 if self.is_menu else len(self.yaml_files) - 1
        if self.selected_idx < max_idx:
            self.selected_idx += 1
            self.update_selection()

    def action_execute(self):
        if self.is_menu:
            if self.selected_idx == 0:
                self.action_restart()
            else:
                self.close_terminal()
        else:
            self.run_cv()

    def close_terminal(self):
        subprocess.run(["osascript", "-e", 'tell app "Terminal" to quit'], check=False)
        self.exit(EXIT_CLOSE_TERMINAL)

    def run_cv(self):
        if self.selected_idx >= len(self.yaml_files):
            return

        selected_file = self.yaml_files[self.selected_idx]
        filename = selected_file.name
        basename = selected_file.stem

        result = generate_cv(filename, basename)

        self.show_result(basename, result)

    def show_result(self, basename: str, success: bool):
        main_container = self.query_one("#main-container")

        for child in list(main_container.children):
            child.remove()

        self.is_menu = True
        self.menu_options = ["[R] Regenerar otro", "[Q] Salir"]
        self.selected_idx = 0

        if success:
            main_container.mount(Static("🎯 Seleccioná tu CV"))
            main_container.mount(Static(f"✅ PDF generado: {basename}.pdf", classes="success-msg"))
            main_container.mount(Static(""))
            main_container.mount(Static("¿Qué hacés ahora?"))
            main_container.mount(Static(""))
            main_container.mount(
                Vertical(
                    Static("▸ [R] Regenerar otro", id="menu-0"),
                    Static("  [Q] Salir", id="menu-1"),
                    id="menu-list"
                )
            )
            main_container.mount(Static("↑↓ para navegar | ENTER para confirmar"))
        else:
            main_container.mount(Static("❌ Error al generar PDF", classes="error-msg"))
            main_container.mount(Static(""))
            main_container.mount(
                Vertical(
                    Static("▸ [R] Volver a intentar", id="menu-0"),
                    Static("  [Q] Salir", id="menu-1"),
                    id="menu-list"
                )
            )

    def action_restart(self):
        self.exit(0)
        os.execv(sys.executable, [sys.executable, __file__])

    def key_r(self):
        if self.is_menu:
            self.action_restart()
        else:
            self.key_q()

    def key_q(self):
        self.close_terminal()

    def on_key(self, event):
        if event.key in ["r", "R"]:
            self.key_r()
        elif event.key in ["q", "Q"]:
            self.key_q()


if __name__ == "__main__":
    app = CVSelector()
    app.run()