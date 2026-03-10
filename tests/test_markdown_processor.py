"""Tests for chapter discovery and ordering."""

import os
import pytest
from ebk.core.markdown_processor import (
    extract_numeric_prefix,
    get_chapter_title,
    order_chapters,
    filter_chapters,
    should_exclude_path,
)


# --- extract_numeric_prefix ---

def test_numeric_prefix_extracted():
    assert extract_numeric_prefix('01-intro.md') == 1

def test_numeric_prefix_multi_digit():
    assert extract_numeric_prefix('99-appendix.md') == 99

def test_no_numeric_prefix_returns_none():
    assert extract_numeric_prefix('intro.md') is None

def test_numeric_prefix_requires_dash():
    assert extract_numeric_prefix('01intro.md') is None


# --- order_chapters ---

def test_chapters_sorted_by_order():
    chapters = [
        {'relative_path': 'b.md', 'depth': 0, 'order': 2, 'name': 'b.md', 'path': '/b.md', 'metadata': {}},
        {'relative_path': 'a.md', 'depth': 0, 'order': 1, 'name': 'a.md', 'path': '/a.md', 'metadata': {}},
    ]
    result = order_chapters(chapters)
    assert result[0]['name'] == 'a.md'
    assert result[1]['name'] == 'b.md'

def test_chapters_without_order_sort_last():
    chapters = [
        {'relative_path': 'z.md', 'depth': 0, 'order': None, 'name': 'z.md', 'path': '/z.md', 'metadata': {}},
        {'relative_path': 'a.md', 'depth': 0, 'order': 1,    'name': 'a.md', 'path': '/a.md', 'metadata': {}},
    ]
    result = order_chapters(chapters)
    assert result[0]['name'] == 'a.md'
    assert result[1]['name'] == 'z.md'


# --- get_chapter_title ---

def test_title_from_metadata():
    chapter = {'metadata': {'title': 'My Title'}, 'path': '/nonexistent.md', 'name': 'test.md'}
    assert get_chapter_title(chapter) == 'My Title'

def test_title_fallback_to_filename(tmp_path):
    md_file = tmp_path / 'my-chapter.md'
    md_file.write_text('No heading here.')
    chapter = {'metadata': {}, 'path': str(md_file), 'name': 'my-chapter.md'}
    assert get_chapter_title(chapter) == 'My Chapter'

def test_title_from_first_heading(tmp_path):
    md_file = tmp_path / 'chapter.md'
    md_file.write_text('# The Real Title\n\nSome content.')
    chapter = {'metadata': {}, 'path': str(md_file), 'name': 'chapter.md'}
    assert get_chapter_title(chapter) == 'The Real Title'


# --- filter_chapters ---

def _ch(name, idx):
    return {
        'name': name, 'relative_path': name,
        'path': f'/{name}', 'order': idx, 'depth': 0,
        'metadata': {}, 'is_intro': False,
    }

def test_filter_empty_selectors_returns_all():
    chapters = [_ch('01-intro.md', 1), _ch('02-body.md', 2)]
    assert filter_chapters(chapters, []) == chapters

def test_filter_by_index():
    chapters = [_ch('01-intro.md', 1), _ch('02-body.md', 2), _ch('03-end.md', 3)]
    result = filter_chapters(chapters, ['2'])
    assert len(result) == 1
    assert result[0]['name'] == '02-body.md'

def test_filter_multiple_indexes():
    chapters = [_ch('01-intro.md', 1), _ch('02-body.md', 2), _ch('03-end.md', 3)]
    result = filter_chapters(chapters, ['1', '3'])
    assert [c['name'] for c in result] == ['01-intro.md', '03-end.md']

def test_filter_by_name_substring():
    chapters = [_ch('01-intro.md', 1), _ch('02-runway.md', 2)]
    result = filter_chapters(chapters, ['runway'])
    assert len(result) == 1
    assert result[0]['name'] == '02-runway.md'

def test_filter_preserves_order():
    chapters = [_ch('01-intro.md', 1), _ch('02-body.md', 2), _ch('03-end.md', 3)]
    result = filter_chapters(chapters, ['3', '1'])
    assert [c['name'] for c in result] == ['01-intro.md', '03-end.md']

def test_filter_out_of_range_index_skipped(capsys):
    chapters = [_ch('01-intro.md', 1)]
    result = filter_chapters(chapters, ['99'])
    assert result == []
    assert 'Warning' in capsys.readouterr().out

def test_filter_no_match_skipped(capsys):
    chapters = [_ch('01-intro.md', 1)]
    result = filter_chapters(chapters, ['nonexistent'])
    assert result == []
    assert 'Warning' in capsys.readouterr().out


# --- should_exclude_path ---

def test_excludes_matching_directory(tmp_path):
    path = str(tmp_path / '.git' / 'config')
    assert should_exclude_path(path, ['.git'], str(tmp_path))

def test_does_not_exclude_non_matching(tmp_path):
    path = str(tmp_path / 'content' / 'chapter.md')
    assert not should_exclude_path(path, ['.git'], str(tmp_path))

def test_empty_exclude_list(tmp_path):
    path = str(tmp_path / '.git')
    assert not should_exclude_path(path, [], str(tmp_path))
