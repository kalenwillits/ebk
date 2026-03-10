"""Tests for metadata normalization."""

from ebk.core.epub_builder import normalize_metadata


def test_author_maps_to_dc_creator():
    result = normalize_metadata({'author': 'Jane Doe'})
    assert result['dc:creator'] == 'Jane Doe'


def test_title_maps_to_dc_title():
    result = normalize_metadata({'title': 'My Book'})
    assert result['dc:title'] == 'My Book'


def test_language_maps_to_dc_language():
    result = normalize_metadata({'language': 'en-US'})
    assert result['dc:language'] == 'en-US'


def test_identifier_maps_to_dc_identifier():
    result = normalize_metadata({'identifier': 'abc-123'})
    assert result['dc:identifier'] == 'abc-123'


def test_already_prefixed_keys_pass_through():
    result = normalize_metadata({'dc:creator': 'Jane Doe'})
    assert result['dc:creator'] == 'Jane Doe'


def test_unknown_keys_pass_through():
    result = normalize_metadata({'custom_field': 'value'})
    assert result['custom_field'] == 'value'


def test_empty_metadata():
    assert normalize_metadata({}) == {}


def test_all_common_keys():
    input_meta = {
        'title': 'T',
        'author': 'A',
        'language': 'en',
        'identifier': 'id',
        'date': '2026-01-01',
        'publisher': 'P',
        'description': 'D',
        'subject': 'S',
    }
    result = normalize_metadata(input_meta)
    assert 'dc:title' in result
    assert 'dc:creator' in result
    assert 'dc:language' in result
    assert 'dc:identifier' in result
    assert 'dc:date' in result
    assert 'dc:publisher' in result
    assert 'dc:description' in result
    assert 'dc:subject' in result
    # None of the short keys should remain
    for key in input_meta:
        assert key not in result
