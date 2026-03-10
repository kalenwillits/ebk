"""Tests for EPUB generation utilities."""

import zipfile
from xml.etree import ElementTree as ET
from ebk.core.epub_builder import (
    get_container_XML,
    get_TOC_XML,
    get_packageOPF_XML,
    get_TOCNCX_XML,
)


def _make_chapter(title, index=0):
    return {
        'path': f'/fake/s{index:05d}.md',
        'name': f's{index:05d}.md',
        'metadata': {'title': title},
        'order': index,
        'depth': 0,
        'relative_path': f's{index:05d}.md',
        'is_intro': False,
    }


# --- container.xml ---

def test_container_xml_is_valid():
    xml = get_container_XML()
    root = ET.fromstring(xml)
    assert root.tag is not None

def test_container_xml_points_to_opf():
    xml = get_container_XML()
    assert 'OPS/package.opf' in xml


# --- TOC.xhtml ---

def test_toc_xml_is_valid_xml():
    chapters = [_make_chapter('Intro', 0), _make_chapter('Chapter Two', 1)]
    xml = get_TOC_XML([], chapters, has_cover=False)
    ET.fromstring(xml)  # raises if invalid

def test_toc_xml_escapes_ampersand():
    chapters = [_make_chapter('A & B', 0)]
    xml = get_TOC_XML([], chapters, has_cover=False)
    assert '&amp;' in xml
    assert '&' not in xml.replace('&amp;', '')

def test_toc_xml_contains_chapter_titles():
    chapters = [_make_chapter('Introduction', 0), _make_chapter('Conclusion', 1)]
    xml = get_TOC_XML([], chapters, has_cover=False)
    assert 'Introduction' in xml
    assert 'Conclusion' in xml

def test_toc_xml_cover_link_when_present():
    xml = get_TOC_XML([], [], has_cover=True)
    assert 'titlepage.xhtml' in xml

def test_toc_xml_no_cover_link_when_absent():
    xml = get_TOC_XML([], [], has_cover=False)
    assert 'titlepage.xhtml' not in xml


# --- package.opf ---

def test_opf_contains_dc_metadata():
    metadata = {'dc:title': 'My Book', 'dc:creator': 'Jane Doe', 'dc:language': 'en-US'}
    xml = get_packageOPF_XML([], [], [], metadata, has_cover=False)
    assert 'My Book' in xml
    assert 'Jane Doe' in xml

def test_opf_contains_dcterms_modified():
    xml = get_packageOPF_XML([], [], [], {}, has_cover=False)
    assert 'dcterms:modified' in xml

def test_opf_is_valid_xml():
    metadata = {'dc:title': 'Test', 'dc:identifier': 'test-id'}
    xml = get_packageOPF_XML([], [], [], metadata, has_cover=False)
    ET.fromstring(xml)  # raises if invalid

def test_opf_lists_chapters_in_manifest():
    chapters = [_make_chapter('Ch1', 0), _make_chapter('Ch2', 1)]
    xml = get_packageOPF_XML(chapters, [], [], {}, has_cover=False)
    assert 's00000' in xml
    assert 's00001' in xml


# --- toc.ncx ---

def test_ncx_is_valid_xml():
    chapters = [_make_chapter('Intro', 0)]
    xml = get_TOCNCX_XML(chapters, {'dc:identifier': 'test-id', 'dc:title': 'Test'}, has_cover=False)
    ET.fromstring(xml)

def test_ncx_contains_chapter_title():
    chapters = [_make_chapter('My Chapter', 0)]
    xml = get_TOCNCX_XML(chapters, {}, has_cover=False)
    assert 'My Chapter' in xml
