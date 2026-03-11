"""Integration tests for build_html options."""

import os
import pytest
from ebk.core.html_builder import build_html


@pytest.fixture
def simple_project(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text(
        'metadata:\n'
        '  title: Test Book\n'
        '  author: Test Author\n'
        'output:\n'
        '  html_dir: html\n'
    )
    (tmp_path / '01-intro.md').write_text('# Introduction\n\nHello world.')
    (tmp_path / '02-body.md').write_text('# Body\n\nMore content.')
    return tmp_path


def test_html_creates_chapter_files(simple_project, tmp_path):
    out = tmp_path / 'html'
    build_html(str(simple_project), str(out))
    assert (out / 's00000.html').exists()
    assert (out / 's00001.html').exists()


def test_html_creates_index_by_default(simple_project, tmp_path):
    out = tmp_path / 'html'
    build_html(str(simple_project), str(out))
    assert (out / 'index.html').exists()
    content = (out / 'index.html').read_text()
    assert 'Introduction' in content
    assert 'Body' in content


def test_html_no_toc_skips_index(simple_project, tmp_path):
    out = tmp_path / 'html'
    build_html(str(simple_project), str(out), no_toc=True)
    assert not (out / 'index.html').exists()
    # Chapter files still generated
    assert (out / 's00000.html').exists()


def test_html_with_flags(simple_project, tmp_path):
    (simple_project / '01-intro.md').write_text(
        "# Intro\n\n{% if 'present' in flags %}SLIDE{% endif %}"
    )
    out = tmp_path / 'html'
    build_html(str(simple_project), str(out), flags=['present'])
    content = (out / 's00000.html').read_text()
    assert 'SLIDE' in content


def test_html_chapter_selection(simple_project, tmp_path):
    out = tmp_path / 'html'
    build_html(str(simple_project), str(out), chapters=['1'])
    assert (out / 's00000.html').exists()
    assert not (out / 's00001.html').exists()
