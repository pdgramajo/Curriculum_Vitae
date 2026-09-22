"""Unit tests for cvapp.core.discovery (design 8 matrix; spec cv-rendering).

RED contract (task 2.1): the module cvapp.core.discovery does not exist yet,
so this file fails collection with ModuleNotFoundError until 2.2 lands.
"""

from __future__ import annotations

import pytest

from cvapp.core.discovery import (
    AmbiguousCVError,
    CVSource,
    UnknownCVError,
    find_cv_sources,
    resolve_cv_by_name,
)

# The 11 real CV stems in discovery order (sorted by filename) — the explicit
# contract mirrored by the task 2.3 runtime check.
REAL_STEMS_SORTED = [
    "Pablo_Gramajo",
    "Pablo_Gramajo_Analista_Automatizacion_Sr",
    "Pablo_Gramajo_Data_Analist",
    "Pablo_Gramajo_Data_Analist_new",
    "Pablo_Gramajo_FrontEnd2",
    "Pablo_Gramajo_Frontend_CV",
    "Pablo_Gramajo_FullStack_CV",
    "Pablo_Gramajo_FullStack_CV_es",
    "Pablo_Gramajo_Gerente_sistemas",
    "Pablo_Gramajo_Net_CV",
    "Pablo_Gramajo_react_CV",
]


def _write(root, name: str, content: str = "name: dummy\n") -> None:
    (root / name).write_text(content, encoding="utf-8")


def test_finds_yaml_and_yml_sorted_non_recursive(tmp_path):
    """Both extensions are found, sorted by filename; other files ignored."""
    root = tmp_path / "cvs"
    root.mkdir()
    _write(root, "beta.yml")
    _write(root, "alpha.yaml")
    _write(root, "gamma.txt", "not a cv\n")

    sources = find_cv_sources(root)

    assert [s.name for s in sources] == ["alpha", "beta"]
    assert all(s.path.is_file() for s in sources)
    assert all(s.path.is_absolute() for s in sources)
    assert all(s.id == s.name for s in sources)
    assert all(isinstance(s, CVSource) for s in sources)


def test_dotfiles_are_excluded(tmp_path):
    """A hidden .cv_experimental.yaml must not appear in the result."""
    root = tmp_path / "cvs"
    root.mkdir()
    _write(root, ".cv_experimental.yaml", "hidden\n")
    _write(root, "Pablo_Gramajo.yaml")

    sources = find_cv_sources(root)

    assert [s.name for s in sources] == ["Pablo_Gramajo"]


def test_subdirectories_are_not_scanned(tmp_path):
    root = tmp_path / "cvs"
    (root / "sub").mkdir(parents=True)
    _write(root / "sub", "Otro_CV.yaml")
    _write(root, "Ok.yaml")

    sources = find_cv_sources(root)

    assert [s.name for s in sources] == ["Ok"]


def test_empty_directory_returns_empty_list(tmp_path):
    root = tmp_path / "cvs"
    root.mkdir()

    assert find_cv_sources(root) == []


def test_nonexistent_directory_returns_empty_list(tmp_path):
    """glob over a missing dir yields nothing; no error (lenient by design)."""
    assert find_cv_sources(tmp_path / "no-existe") == []


def test_sample_sources_match_real_glob_order(sample_sources):
    """The 11 real stems come back sorted — same order as today's glob."""
    sources = find_cv_sources(sample_sources)

    assert [s.name for s in sources] == REAL_STEMS_SORTED


def test_resolve_exact_match(sample_sources):
    sources = find_cv_sources(sample_sources)

    cv = resolve_cv_by_name(sources, "Pablo_Gramajo")

    assert cv.name == "Pablo_Gramajo"
    assert cv.path.name == "Pablo_Gramajo.yaml"
    assert cv.path.is_file()


def test_resolve_unknown_name_raises(sample_sources):
    sources = find_cv_sources(sample_sources)

    with pytest.raises(UnknownCVError):
        resolve_cv_by_name(sources, "No_Existe")


def test_resolve_on_empty_list_raises_unknown(tmp_path):
    """0 matches is an unknown-name error, never success."""
    root = tmp_path / "cvs"
    root.mkdir()

    with pytest.raises(UnknownCVError):
        resolve_cv_by_name(find_cv_sources(root), "Cualquiera")


def test_resolve_ambiguous_name_raises(tmp_path):
    """Mi_CV.yaml + Mi_CV.yml -> two sources, the name is ambiguous."""
    root = tmp_path / "cvs"
    root.mkdir()
    _write(root, "Mi_CV.yaml")
    _write(root, "Mi_CV.yml")

    sources = find_cv_sources(root)

    assert len(sources) == 2
    with pytest.raises(AmbiguousCVError):
        resolve_cv_by_name(sources, "Mi_CV")
