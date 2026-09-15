"""Tests for build-time Tailwind CSS compilation in ebk.core.tailwind."""

import os
import pytest

from ebk.core.tailwind import (
    compile_tailwind_css,
    try_compile_tailwind_css,
    tailwind_enabled,
    TailwindUnavailableError,
)


def test_tailwind_enabled_requires_explicit_opt_in():
    assert tailwind_enabled({}) is False
    assert tailwind_enabled({'tailwind': {}}) is False
    assert tailwind_enabled({'tailwind': {'enabled': False}}) is False
    assert tailwind_enabled({'tailwind': {'enabled': True}}) is True


def test_compile_is_a_noop_when_not_enabled(tmp_path, monkeypatch):
    """No subprocess/network call is attempted when tailwind isn't enabled."""
    def _boom(*args, **kwargs):
        raise AssertionError("pytailwindcss.run should not be called")

    import pytailwindcss
    monkeypatch.setattr(pytailwindcss, 'run', _boom)

    result = compile_tailwind_css(str(tmp_path), {})
    assert result is None


def test_compile_returns_css_layer_on_success(tmp_path, monkeypatch):
    def fake_run(args, bin_path=None, auto_install=None, version=None):
        # args: ['-i', entry_css, '-o', output_css, '--cwd', ..., '--minify', '--silent']
        output_css = args[3]
        with open(output_css, 'w') as f:
            f.write('.text-red-500{color:red}')

    import pytailwindcss
    monkeypatch.setattr(pytailwindcss, 'run', fake_run)

    layer = compile_tailwind_css(str(tmp_path), {'tailwind': {'enabled': True}})

    assert layer is not None
    assert layer.name == 'tailwind.css'
    assert layer.source == 'tailwind'
    assert 'text-red-500' in layer.text


def test_compile_raises_tailwind_unavailable_on_failure(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise RuntimeError("network unreachable")

    import pytailwindcss
    monkeypatch.setattr(pytailwindcss, 'run', fake_run)

    with pytest.raises(TailwindUnavailableError):
        compile_tailwind_css(str(tmp_path), {'tailwind': {'enabled': True}})


def test_try_compile_degrades_gracefully_on_failure(tmp_path, monkeypatch, capsys):
    def fake_run(*args, **kwargs):
        raise RuntimeError("network unreachable")

    import pytailwindcss
    monkeypatch.setattr(pytailwindcss, 'run', fake_run)

    result = try_compile_tailwind_css(str(tmp_path), {'tailwind': {'enabled': True}})

    assert result is None
    assert 'Tailwind' in capsys.readouterr().out


def test_try_compile_is_noop_and_silent_when_disabled(tmp_path, monkeypatch, capsys):
    def _boom(*args, **kwargs):
        raise AssertionError("pytailwindcss.run should not be called")

    import pytailwindcss
    monkeypatch.setattr(pytailwindcss, 'run', _boom)

    result = try_compile_tailwind_css(str(tmp_path), {})

    assert result is None
    assert capsys.readouterr().out == ''


@pytest.mark.skipif(
    not os.environ.get('EBK_TEST_TAILWIND_NETWORK'),
    reason="set EBK_TEST_TAILWIND_NETWORK=1 to run the real Tailwind CLI "
           "end-to-end (downloads the standalone binary on first use)",
)
def test_real_tailwind_compiles_classes_from_markdown_and_config(tmp_path):
    """End-to-end with the real Tailwind CLI: a utility class written in a
    markdown file, and one embedded in config.yaml's `tw:` alias map, both
    get compiled -- confirms Tailwind v4's automatic content detection picks
    up both without any content-glob configuration from ebk."""
    (tmp_path / '01.md').write_text(
        '# Hello\n\n<div class="text-purple-700 underline">world</div>\n'
    )
    (tmp_path / 'config.yaml').write_text(
        'tw:\n  hero: "bg-teal-600 rounded-xl"\n'
    )

    layer = compile_tailwind_css(str(tmp_path), {'tailwind': {'enabled': True}})

    assert layer is not None
    assert 'text-purple-700' in layer.text
    assert 'underline' in layer.text
    assert 'bg-teal-600' in layer.text
