"""Tests for the ebk linter (--check)."""

import pytest
from ebk.core.linter import lint_project


@pytest.fixture
def minimal_project(tmp_path):
    """Minimal valid ebk project."""
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text(
        'metadata:\n'
        '  title: "Test Book"\n'
        '  author: "Test Author"\n'
        '  language: "en-US"\n'
        '  identifier: "test-123"\n'
        '  description: "A test book"\n'
        '  publisher: "Test Publisher"\n'
        '  date: "2025-01-01"\n'
        'output:\n'
        '  filename: test.epub\n'
    )
    (tmp_path / '01-intro.md').write_text('# Introduction\n\nHello world.')
    return tmp_path


def test_clean_project_has_no_errors(minimal_project):
    result = lint_project(str(minimal_project))
    assert result.ok, [str(d) for d in result.errors]


def test_missing_book_yaml(tmp_path):
    (tmp_path / '.ebk').write_text('')
    result = lint_project(str(tmp_path))
    assert not result.ok
    assert any('book.yaml' in str(d) for d in result.errors)


def test_invalid_yaml_syntax(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text('metadata:\n  title: [unclosed')
    result = lint_project(str(tmp_path))
    # This may parse oddly but not crash — depends on PyYAML behavior
    # The important thing is it doesn't raise


def test_missing_required_metadata(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text('metadata:\n  title: "Test"\n')
    (tmp_path / '01-intro.md').write_text('# Intro\n\nHello.')
    result = lint_project(str(tmp_path))
    errors = [str(d) for d in result.errors]
    assert any('author' in e for e in errors)
    assert any('language' in e for e in errors)
    assert any('identifier' in e for e in errors)


def test_missing_metadata_section(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text('output:\n  filename: test.epub\n')
    (tmp_path / '01-intro.md').write_text('# Intro\n\nHello.')
    result = lint_project(str(tmp_path))
    assert any("Missing 'metadata'" in str(d) for d in result.errors)


def test_jinja_syntax_error(minimal_project):
    (minimal_project / '01-intro.md').write_text('# Intro\n\n{% if broken')
    result = lint_project(str(minimal_project))
    assert not result.ok
    assert any('Jinja2 syntax' in str(d) for d in result.errors)


def test_jinja_undefined_variable(minimal_project):
    (minimal_project / '01-intro.md').write_text('# Intro\n\n{{ nonexistent_var }}')
    result = lint_project(str(minimal_project))
    assert not result.ok
    assert any('render error' in str(d).lower() or 'undefined' in str(d).lower()
               for d in result.errors)


def test_no_chapters_found(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text(
        'metadata:\n'
        '  title: "Test"\n'
        '  author: "Author"\n'
        '  language: "en"\n'
        '  identifier: "x"\n'
    )
    result = lint_project(str(tmp_path))
    assert not result.ok
    assert any('No markdown files' in str(d) for d in result.errors)


def test_heading_level_jump_warning(minimal_project):
    (minimal_project / '01-intro.md').write_text('# Title\n\n#### Jumped to h4\n')
    result = lint_project(str(minimal_project))
    assert any('Heading level jumps' in str(d) for d in result.warnings)


def test_no_heading_warning(minimal_project):
    (minimal_project / '01-intro.md').write_text('Just some text without any heading.\n')
    result = lint_project(str(minimal_project))
    assert any('no headings' in str(d) for d in result.warnings)


def test_unsupported_html_tag_warning(minimal_project):
    (minimal_project / '01-intro.md').write_text('# Intro\n\n<video src="x.mp4"></video>\n')
    result = lint_project(str(minimal_project))
    assert any('video' in str(d) and 'Apple Books' in str(d) for d in result.warnings)


def test_no_cover_image_warning(minimal_project):
    result = lint_project(str(minimal_project))
    assert any('cover_image' in str(d) for d in result.warnings)


def test_cover_image_not_found_error(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text(
        'metadata:\n'
        '  title: "Test"\n'
        '  author: "Author"\n'
        '  language: "en"\n'
        '  identifier: "x"\n'
        'cover_image: "missing.jpg"\n'
    )
    (tmp_path / '01-intro.md').write_text('# Intro\n\nHello.')
    result = lint_project(str(tmp_path))
    assert any('missing.jpg' in str(d) and 'not found' in str(d) for d in result.errors)


def test_css_unmatched_brace(minimal_project):
    (minimal_project / 'bad.css').write_text('body { color: red; }}')
    result = lint_project(str(minimal_project))
    assert any('brace' in str(d).lower() for d in result.errors)


def test_css_unsupported_feature_warning(minimal_project):
    (minimal_project / 'fancy.css').write_text('div { position: fixed; }')
    result = lint_project(str(minimal_project))
    assert any('position:fixed' in str(d) for d in result.warnings)


def test_invalid_context_yaml(minimal_project):
    ctx = minimal_project / 'context'
    ctx.mkdir()
    (ctx / 'global.yaml').write_text(': bad yaml {{{}')
    result = lint_project(str(minimal_project))
    assert any('Invalid YAML' in str(d) for d in result.errors)


def test_invalid_context_json(minimal_project):
    ctx = minimal_project / 'context'
    ctx.mkdir()
    (ctx / 'global.json').write_text('{bad json')
    result = lint_project(str(minimal_project))
    assert any('Invalid JSON' in str(d) for d in result.errors)


def test_missing_ebk_marker(tmp_path):
    (tmp_path / 'book.yaml').write_text(
        'metadata:\n'
        '  title: "Test"\n'
        '  author: "Author"\n'
        '  language: "en"\n'
        '  identifier: "x"\n'
    )
    (tmp_path / '01-intro.md').write_text('# Intro\n\nHello.')
    result = lint_project(str(tmp_path))
    assert any('.ebk' in str(d) for d in result.errors)


def test_flags_passed_to_lint(minimal_project):
    (minimal_project / '01-intro.md').write_text(
        "# Intro\n\n{% if 'draft' in flags %}DRAFT{% endif %}"
    )
    # Without flag — should render fine (empty output for that block)
    result = lint_project(str(minimal_project), flags=['draft'])
    assert result.ok, [str(d) for d in result.errors]


def test_chapter_filter(minimal_project):
    (minimal_project / '02-broken.md').write_text('# Broken\n\n{% if bad')
    # Lint only chapter 1 — should pass
    result = lint_project(str(minimal_project), chapters_filter=['1'])
    assert result.ok, [str(d) for d in result.errors]
    # Lint chapter 2 — should fail
    result2 = lint_project(str(minimal_project), chapters_filter=['2'])
    assert not result2.ok


def test_svg_image_warning(minimal_project):
    img_dir = minimal_project / 'images'
    img_dir.mkdir()
    (img_dir / 'diagram.svg').write_text('<svg></svg>')
    result = lint_project(str(minimal_project))
    assert any('SVG' in str(d) for d in result.warnings)


def test_recommended_metadata_warnings(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text(
        'metadata:\n'
        '  title: "Test"\n'
        '  author: "Author"\n'
        '  language: "en"\n'
        '  identifier: "x"\n'
    )
    (tmp_path / '01-intro.md').write_text('# Intro\n\nHello.')
    result = lint_project(str(tmp_path))
    warnings = [str(d) for d in result.warnings]
    assert any('description' in w for w in warnings)
    assert any('publisher' in w for w in warnings)
    assert any('date' in w for w in warnings)


def test_null_bytes_in_content(minimal_project):
    (minimal_project / '01-intro.md').write_bytes(b'# Intro\n\nHello\x00world')
    result = lint_project(str(minimal_project))
    assert any('null bytes' in str(d) for d in result.errors)
