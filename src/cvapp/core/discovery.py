"""CV source discovery: find YAML CVs and resolve a name to one source.

Design 4.3 (cv-tui-redesign), spec cv-rendering requirement "CV YAML sources
are discovered from the configured directory".

Pure functions: the only I/O is the glob over the source directory, so the
`list` command, the TUI main screen and the `render` command all share one
deterministic ordering — sorted by filename, dotfiles excluded, non-recursive.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Patterns scanned by discovery, in stable order (order does not matter here:
# the result is sorted afterwards, and a file can match only one pattern).
_CV_PATTERNS = ("*.yaml", "*.yml")


@dataclass(frozen=True)
class CVSource:
    """One discoverable CV YAML file.

    ``id`` and ``name`` are both the file stem (e.g. "Pablo_Gramajo"); ``id``
    exists so call sites read "id" where they mean identity and "name" where
    they mean the display label (design 4.3). ``path`` is absolute.
    """

    id: str
    name: str
    path: Path


class UnknownCVError(Exception):
    """No CV source matches the requested name (render <name> -> exit 1)."""

    def __init__(self, name: str) -> None:
        super().__init__(f"No se encontró ningún CV llamado '{name}'.")


class AmbiguousCVError(Exception):
    """More than one CV source matches the requested name (render -> exit 1).

    Reachable only from `cv render <name>`: with both Mi_CV.yaml and Mi_CV.yml
    present, discovery yields two sources and the bare stem names both (design
    4.3) — the TUI avoids this by listing each file as its own row.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"Hay más de un CV llamado '{name}'.")


def find_cv_sources(cvs_dir: Path) -> list[CVSource]:
    """Find CV YAMLs: *.yaml + *.yml, non-recursive, dotfiles excluded.

    The directory is resolved to an absolute path first so every returned
    ``path`` is absolute regardless of how ``cvs_dir`` was spelled (design 4.3:
    "path: absolute path to the YAML"). Results are sorted by filename, which
    for distinct stems is the same order as sorting by name.
    """
    base = Path(cvs_dir).resolve()
    sources: list[CVSource] = []
    seen: set[Path] = set()
    for pattern in _CV_PATTERNS:
        for candidate in base.glob(pattern):
            # glob already skips dotfiles; the leading-dot check documents the
            # intent and guards the two patterns against future drift.
            if candidate.name.startswith(".") or not candidate.is_file():
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            sources.append(CVSource(id=candidate.stem, name=candidate.stem, path=candidate))
    sources.sort(key=lambda source: source.path.name)
    return sources


def resolve_cv_by_name(sources: list[CVSource], name: str) -> CVSource:
    """Return the single source whose stem matches ``name``; else raise.

    Exactly one match, else error: zero matches is an unknown name
    (``UnknownCVError``) and more than one is ambiguous (``AmbiguousCVError``).
    """
    matches = [source for source in sources if source.name == name]
    if not matches:
        raise UnknownCVError(name)
    if len(matches) > 1:
        raise AmbiguousCVError(name)
    return matches[0]
