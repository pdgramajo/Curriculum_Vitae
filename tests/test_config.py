"""Unit tests for cvapp.config (design 8 matrix; spec cv-config scenarios)."""

from __future__ import annotations

import logging

import pytest

from cvapp.config import ConfigError, load, setup_logging

OUT_DEFAULT = "rendercv_output"


def test_defaults_with_no_file(project_factory):
    """Missing cvapp.yaml -> defaults compatible with today's layout."""
    root = project_factory()
    settings = load(root)
    assert settings.cvs_dir == root.resolve()
    assert settings.output_dir == (root / OUT_DEFAULT).resolve()
    assert settings.open_pdf_after is True
    assert settings.cleanup_intermediate is True
    assert settings.rendercv_extra_flags == []
    assert settings.timeout_seconds == 120
    assert settings.log_level == "INFO"
    assert settings.project_root == root.resolve()


def test_empty_config_file_uses_defaults(project_factory):
    """An empty cvapp.yaml is equivalent to no file at all."""
    root = project_factory(config_text="")
    settings = load(root)
    assert settings.open_pdf_after is True
    assert settings.cvs_dir == root.resolve()
    assert settings.output_dir == (root / OUT_DEFAULT).resolve()


def test_partial_merge_defaults_for_the_rest(project_factory):
    """A config stating only output_dir leaves every other key at its default."""
    root = project_factory(config_text="output_dir: custom_out\n")
    settings = load(root)
    assert settings.output_dir == (root / "custom_out").resolve()
    assert settings.cvs_dir == root.resolve()
    assert settings.open_pdf_after is True
    assert settings.timeout_seconds == 120


def test_unknown_keys_are_ignored(project_factory):
    """A config written for another version must not break the app."""
    root = project_factory(config_text="futuro_ajuste: 42\noutput_dir: out\n")
    settings = load(root)
    assert settings.output_dir == (root / "out").resolve()
    assert settings.open_pdf_after is True  # rest stays default


def test_project_root_never_comes_from_the_file(project_factory, tmp_path):
    """project_root is not a documented key: a file value must be ignored."""
    root = project_factory(config_text=f"project_root: {tmp_path / 'evil'}\n")
    settings = load(root)
    assert settings.project_root == root.resolve()


def test_malformed_yaml_raises_config_error_naming_file(project_factory):
    root = project_factory(config_text="not: [valid\n")
    with pytest.raises(ConfigError, match="cvapp.yaml"):
        load(root)


def test_non_dict_yaml_raises_config_error(project_factory):
    """A YAML list is valid YAML but not a valid config map."""
    root = project_factory(config_text="- a\n- b\n")
    with pytest.raises(ConfigError, match="cvapp.yaml"):
        load(root)


def test_invalid_bool_value_names_the_key(project_factory):
    """open_pdf_after: "si" is a string where a boolean is required."""
    root = project_factory(config_text='open_pdf_after: "si"\n')
    with pytest.raises(ConfigError, match="open_pdf_after"):
        load(root)


def test_timeout_zero_fails_fast(project_factory):
    root = project_factory(config_text="timeout_seconds: 0\n")
    with pytest.raises(ConfigError, match="timeout_seconds"):
        load(root)


def test_invalid_log_level_names_the_key(project_factory):
    root = project_factory(config_text="log_level: CHATY\n")
    with pytest.raises(ConfigError, match="log_level"):
        load(root)


def test_env_log_level_beats_config_key(project_factory, monkeypatch):
    """CVAPP_LOG_LEVEL wins over the cvapp.yaml log_level key (spec scenario)."""
    root = project_factory(config_text="log_level: WARNING\n")
    settings = load(root)
    assert settings.log_level == "WARNING"
    monkeypatch.setenv("CVAPP_LOG_LEVEL", "DEBUG")
    setup_logging(settings)
    logger = logging.getLogger("cvapp")
    assert logger.level == logging.DEBUG


def test_relative_paths_resolve_against_project_root(project_factory):
    root = project_factory(config_text="cvs_dir: cvs\noutput_dir: pdfs\n")
    settings = load(root)
    assert settings.cvs_dir == (root / "cvs").resolve()
    assert settings.output_dir == (root / "pdfs").resolve()


def test_absolute_paths_pass_through(project_factory, tmp_path):
    abs_cvs = tmp_path / "abs-cvs"
    abs_out = tmp_path / "abs-out"
    root = project_factory(config_text=f"cvs_dir: {abs_cvs}\noutput_dir: {abs_out}\n")
    settings = load(root)
    assert settings.cvs_dir == abs_cvs.resolve()
    assert settings.output_dir == abs_out.resolve()
