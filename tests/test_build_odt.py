"""Integration tests for build_odt."""

import zipfile

import pytest

from ebk.core.odt_builder import build_odt


def _content_xml(path):
    """Read the content.xml stream from an .odt (zip) file as text."""
    with zipfile.ZipFile(path) as z:
        return z.read('content.xml').decode('utf-8')


@pytest.fixture
def simple_project(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'config.yaml').write_text(
        'metadata:\n'
        '  title: Test Book\n'
        '  author: Test Author\n'
    )
    (tmp_path / '01-intro.md').write_text('# Introduction\n\nHello world.')
    (tmp_path / '02-body.md').write_text('# Body\n\nMore content.')
    return tmp_path


def test_odt_creates_valid_file(simple_project, tmp_path):
    out = tmp_path / 'book.odt'
    build_odt(str(simple_project), str(out))
    assert out.exists()
    # An .odt is a zip package
    assert zipfile.is_zipfile(str(out))
    names = zipfile.ZipFile(str(out)).namelist()
    assert 'content.xml' in names
    assert 'mimetype' in names


def test_odt_contains_chapter_text(simple_project, tmp_path):
    out = tmp_path / 'book.odt'
    build_odt(str(simple_project), str(out))
    content = _content_xml(out)
    assert 'Introduction' in content
    assert 'Hello world.' in content
    assert 'Body' in content
    assert 'More content.' in content


def test_odt_includes_toc_and_cover_by_default(simple_project, tmp_path):
    out = tmp_path / 'book.odt'
    build_odt(str(simple_project), str(out))
    content = _content_xml(out)
    # Native TOC field present
    assert 'table-of-content' in content
    # Cover author line present
    assert 'Test Author' in content


def test_odt_no_toc_omits_toc(simple_project, tmp_path):
    out = tmp_path / 'book.odt'
    build_odt(str(simple_project), str(out), no_toc=True)
    content = _content_xml(out)
    assert 'table-of-content' not in content


def test_odt_no_cover_omits_author(simple_project, tmp_path):
    out = tmp_path / 'book.odt'
    build_odt(str(simple_project), str(out), no_cover=True)
    content = _content_xml(out)
    # Author only appears on the cover page; chapters here don't reference it
    assert 'Test Author' not in content


def test_odt_with_flags(simple_project, tmp_path):
    (simple_project / '01-intro.md').write_text(
        "# Intro\n\n{% if 'present' in flags %}SLIDE{% endif %}"
    )
    out = tmp_path / 'book.odt'
    build_odt(str(simple_project), str(out), flags=['present'])
    assert 'SLIDE' in _content_xml(out)


def test_odt_chapter_selection(simple_project, tmp_path):
    out = tmp_path / 'book.odt'
    build_odt(str(simple_project), str(out), chapters=['1'])
    content = _content_xml(out)
    assert 'Introduction' in content
    assert 'More content.' not in content


def test_odt_converts_rich_markdown(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'config.yaml').write_text('metadata:\n  title: Rich\n')
    (tmp_path / '01-rich.md').write_text(
        '# Rich\n\n'
        'A **bold** and *italic* and `code` line with a [link](http://x.com).\n\n'
        '- one\n- two\n\n'
        '| A | B |\n|---|---|\n| 1 | 2 |\n'
    )
    out = tmp_path / 'rich.odt'
    build_odt(str(tmp_path), str(out))
    content = _content_xml(out)
    assert 'text:list' in content      # list rendered
    assert 'table:table' in content    # table rendered
    assert 'table:table-column' in content  # column defs present (renders correctly)
    assert 'number-columns-repeated="2"' in content  # 2-column table
    assert 'xlink:href="http://x.com"' in content  # link rendered


def test_odt_table_has_borders_and_padding(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'config.yaml').write_text('metadata:\n  title: T\n')
    (tmp_path / '01.md').write_text(
        '# T\n\n| Name | Role |\n|------|------|\n| Alice | Eng |\n| Bob | PM |\n'
    )
    out = tmp_path / 't.odt'
    build_odt(str(tmp_path), str(out))
    content = _content_xml(out)
    # 3 rows (header + 2 body), 6 cells
    assert content.count('<table:table-row') == 3
    assert content.count('<table:table-cell') == 6
    # Cell style with a border is defined
    assert 'fo:border' in content
