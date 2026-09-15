"""Tests for CLI output-format resolution in ebk.cli.build_current_project."""

import pytest
from ebk import cli


def _init_project(path, config_text="metadata:\n  title: T\n"):
    (path / '.ebk').write_text('')
    (path / 'config.yaml').write_text(config_text)
    (path / '01.md').write_text('# T\n\nHello\n')


def _patch_builders(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, 'build_pdf', lambda *a, **k: calls.append('pdf'))
    monkeypatch.setattr(cli, 'build_html', lambda *a, **k: calls.append('html'))
    monkeypatch.setattr(cli, 'build_odt', lambda *a, **k: calls.append('odt'))
    monkeypatch.setattr(cli, 'build_epub', lambda *a, **k: calls.append('epub'))
    return calls


def test_default_format_is_pdf_when_unset(tmp_path, monkeypatch):
    _init_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = _patch_builders(monkeypatch)

    cli.build_current_project()

    assert calls == ['pdf']


def test_output_format_config_key_selects_format(tmp_path, monkeypatch):
    _init_project(tmp_path, config_text="metadata:\n  title: T\noutput:\n  format: html\n")
    monkeypatch.chdir(tmp_path)
    calls = _patch_builders(monkeypatch)

    cli.build_current_project()

    assert calls == ['html']


def test_explicit_pdf_flag_overrides_config(tmp_path, monkeypatch):
    _init_project(tmp_path, config_text="metadata:\n  title: T\noutput:\n  format: html\n")
    monkeypatch.chdir(tmp_path)
    calls = _patch_builders(monkeypatch)

    cli.build_current_project(pdf=True)

    assert calls == ['pdf']


def test_epub_flag_builds_epub(tmp_path, monkeypatch):
    _init_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = _patch_builders(monkeypatch)

    cli.build_current_project(epub=True)

    assert calls == ['epub']


def test_odt_format_from_config(tmp_path, monkeypatch):
    _init_project(tmp_path, config_text="metadata:\n  title: T\noutput:\n  format: odt\n")
    monkeypatch.chdir(tmp_path)
    calls = _patch_builders(monkeypatch)

    cli.build_current_project()

    assert calls == ['odt']


def test_invalid_output_format_exits_nonzero(tmp_path, monkeypatch, capsys):
    _init_project(tmp_path, config_text="metadata:\n  title: T\noutput:\n  format: docx\n")
    monkeypatch.chdir(tmp_path)
    _patch_builders(monkeypatch)

    with pytest.raises(SystemExit) as exc_info:
        cli.build_current_project()

    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert 'docx' in err
