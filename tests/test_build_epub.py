"""Integration test: build_epub produces a valid, openable EPUB."""

import zipfile
import pytest
from xml.etree import ElementTree as ET
from ebk.core.epub_builder import build_epub


@pytest.fixture
def simple_project(tmp_path):
    """Minimal ebk project with one chapter."""
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'config.yaml').write_text(
        'metadata:\n'
        '  title: Test Book\n'
        '  author: Test Author\n'
        '  language: en-US\n'
        '  identifier: test-123\n'
        'output:\n'
        '  filename: test.epub\n'
    )
    (tmp_path / '01-intro.md').write_text('# Introduction\n\nHello world.')
    return tmp_path


def test_epub_file_is_created(simple_project, tmp_path):
    out = tmp_path / 'out.epub'
    build_epub(str(simple_project), str(out))
    assert out.exists()


def test_epub_is_valid_zip(simple_project, tmp_path):
    out = tmp_path / 'out.epub'
    build_epub(str(simple_project), str(out))
    assert zipfile.is_zipfile(str(out))


def test_epub_mimetype_is_first_and_uncompressed(simple_project, tmp_path):
    out = tmp_path / 'out.epub'
    build_epub(str(simple_project), str(out))
    with zipfile.ZipFile(str(out)) as zf:
        first = zf.infolist()[0]
        assert first.filename == 'mimetype'
        assert first.compress_type == zipfile.ZIP_STORED


def test_epub_contains_required_files(simple_project, tmp_path):
    out = tmp_path / 'out.epub'
    build_epub(str(simple_project), str(out))
    with zipfile.ZipFile(str(out)) as zf:
        names = zf.namelist()
    assert 'META-INF/container.xml' in names
    assert 'OPS/package.opf' in names
    assert 'OPS/TOC.xhtml' in names
    assert 'OPS/toc.ncx' in names
    assert 'OPS/s00000.xhtml' in names


def test_epub_toc_is_valid_xml(simple_project, tmp_path):
    out = tmp_path / 'out.epub'
    build_epub(str(simple_project), str(out))
    with zipfile.ZipFile(str(out)) as zf:
        toc = zf.read('OPS/TOC.xhtml')
    ET.fromstring(toc)  # raises if invalid XML


def test_epub_opf_contains_metadata(simple_project, tmp_path):
    out = tmp_path / 'out.epub'
    build_epub(str(simple_project), str(out))
    with zipfile.ZipFile(str(out)) as zf:
        opf = zf.read('OPS/package.opf').decode()
    assert 'Test Book' in opf
    assert 'Test Author' in opf
    assert 'dcterms:modified' in opf


def test_epub_with_flags(simple_project, tmp_path):
    (simple_project / '01-intro.md').write_text(
        "# Intro\n\n{% if 'present' in flags %}SLIDE{% endif %}"
    )
    out = tmp_path / 'out.epub'
    build_epub(str(simple_project), str(out), flags=['present'])
    with zipfile.ZipFile(str(out)) as zf:
        chapter = zf.read('OPS/s00000.xhtml').decode()
    assert 'SLIDE' in chapter


def test_epub_flags_absent_by_default(simple_project, tmp_path):
    (simple_project / '01-intro.md').write_text(
        "# Intro\n\n{% if 'present' in flags %}SLIDE{% endif %}"
    )
    out = tmp_path / 'out.epub'
    build_epub(str(simple_project), str(out))
    with zipfile.ZipFile(str(out)) as zf:
        chapter = zf.read('OPS/s00000.xhtml').decode()
    assert 'SLIDE' not in chapter
