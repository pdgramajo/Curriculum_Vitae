"""Configuration: Settings model, cvapp.yaml loading, logging setup.

Design 4.2 / 6 (cv-tui-redesign), spec cv-config.

Why pydantic: it produces field-naming validation errors for free, handles
bool/type coercion (where hand-rolled parsing goes wrong), and is ALREADY
installed in .venv as a RenderCV dependency — zero new dependencies.

Why ruamel.yaml instead of PyYAML: RenderCV 2.8 depends on ruamel.yaml
(0.19.1), not PyYAML — design 4.2's intent ("use the YAML library already
installed, no new import") is honored by loading cvapp.yaml with ruamel's
safe loader, which rejects arbitrary object construction the same way
yaml.safe_load does.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class ConfigError(Exception):
    """User-facing configuration failure.

    The message is plain Spanish and names the file and the offending key,
    so it is safe to show directly in the TUI error screen or headless stderr.
    """


class Settings(BaseModel):
    """Application settings.

    ``project_root`` is set by :func:`load` and never read from cvapp.yaml
    (design 4.2: "never from the file"). It defaults to "." so direct
    construction (e.g. tests or ad-hoc scripts) stays possible.
    """

    model_config = ConfigDict(extra="ignore")  # unknown keys are tolerated (spec)

    cvs_dir: Path = Path(".")
    output_dir: Path = Path("rendercv_output")
    open_pdf_after: bool = True
    cleanup_intermediate: bool = True
    rendercv_extra_flags: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=120, gt=0)  # fail fast on 0/negative
    log_level: LogLevel = "INFO"
    project_root: Path = Path(".")


# Module-level safe loader: reused by every load() call (ruamel YAML objects
# are cheap to keep; constructing one per call is also fine).
_YAML = YAML(typ="safe")


def load(project_root: Path) -> Settings:
    """Read cvapp.yaml (if present) merged over defaults; raise ConfigError.

    ``project_root`` is the launcher-set CVAPP_PROJECT_ROOT, or cwd for a
    bare ``python -m cvapp``. Relative ``cvs_dir``/``output_dir`` resolve
    against it, so every consumer is immune to the caller's cwd (spec).
    """
    project_root = Path(project_root)
    config_path = project_root / "cvapp.yaml"
    data: dict = {}
    if config_path.is_file():
        try:
            with config_path.open("r", encoding="utf-8") as stream:
                loaded = _YAML.load(stream)
        except YAMLError as exc:
            raise ConfigError(f"{config_path.name} no es YAML válido: {exc}") from exc
        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            raise ConfigError(
                f"{config_path.name}: el contenido debe ser un mapa de claves "
                "(un archivo YAML de diccionario)."
            )
        data = dict(loaded)
        data.pop("project_root", None)  # never from the file (design 4.2)
    try:
        settings = Settings(**data)
    except ValidationError as exc:
        first = exc.errors()[0]
        key = ".".join(str(part) for part in first["loc"])
        raise ConfigError(
            f"{config_path.name}: el valor de '{key}' no es válido: {first['msg']}"
        ) from exc
    settings.project_root = project_root
    settings.cvs_dir = _resolve_path(project_root, settings.cvs_dir)
    settings.output_dir = _resolve_path(project_root, settings.output_dir)
    return settings


def _resolve_path(project_root: Path, value: Path) -> Path:
    """Relative config paths resolve against the project root; store absolute."""
    path = value if value.is_absolute() else project_root / value
    return path.resolve()


def setup_logging(settings: Settings) -> None:
    """Configure the single 'cvapp' logger writing to <root>/cvapp.log.

    Append mode, one file, level = CVAPP_LOG_LEVEL env var if set, else the
    config key, else INFO. Handlers are cleared first so repeated calls
    (tests, in-process restarts) never stack duplicate file handlers.
    """
    level = os.environ.get("CVAPP_LOG_LEVEL", settings.log_level)
    logger = logging.getLogger("cvapp")
    logger.setLevel(level)
    logger.handlers.clear()
    handler = logging.FileHandler(settings.project_root / "cvapp.log", mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
    logger.propagate = False  # file-only logging: one writer per channel (design 7)
