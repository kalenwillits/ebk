"""Tests for Jinja2 template rendering and context loading."""

import pytest
from ebk.core.template_engine import render_template, load_context


# --- render_template ---

def test_basic_variable_substitution():
    result = render_template('Hello {{ name }}!', {'name': 'World'})
    assert result == 'Hello World!'

def test_conditional_true():
    result = render_template("{% if show %}yes{% endif %}", {'show': True})
    assert result == 'yes'

def test_conditional_false():
    result = render_template("{% if show %}yes{% endif %}", {'show': False})
    assert result == ''

def test_flags_in_template():
    result = render_template(
        "{% if 'present' in flags %}slide{% endif %}",
        {'flags': {'present'}}
    )
    assert result == 'slide'

def test_flags_absent():
    result = render_template(
        "{% if 'present' in flags %}slide{% endif %}",
        {'flags': set()}
    )
    assert result == ''

def test_no_template_syntax_passes_through():
    content = '# Just plain markdown\n\nNo variables here.'
    assert render_template(content, {}) == content


# --- load_context ---

def test_flags_in_context(tmp_path):
    (tmp_path / 'book.yaml').write_text('metadata:\n  title: Test\n')
    (tmp_path / '.ebk').write_text('')
    chapter = tmp_path / 'ch.md'
    chapter.write_text('# Chapter')

    book_config = {'flags': ['present', 'draft']}
    ctx = load_context(str(tmp_path), str(chapter), book_config)

    assert 'flags' in ctx
    assert 'present' in ctx['flags']
    assert 'draft' in ctx['flags']

def test_empty_flags_in_context(tmp_path):
    chapter = tmp_path / 'ch.md'
    chapter.write_text('# Chapter')

    ctx = load_context(str(tmp_path), str(chapter), {})
    assert ctx['flags'] == set()

def test_book_metadata_in_context(tmp_path):
    chapter = tmp_path / 'ch.md'
    chapter.write_text('# Chapter')

    book_config = {'metadata': {'title': 'My Book', 'author': 'Jane'}}
    ctx = load_context(str(tmp_path), str(chapter), book_config)

    assert ctx['book']['title'] == 'My Book'
    assert ctx['book']['author'] == 'Jane'

def test_builtin_variables_present(tmp_path):
    chapter = tmp_path / 'ch.md'
    chapter.write_text('# Chapter')

    ctx = load_context(str(tmp_path), str(chapter), {})
    assert 'ebk_version' in ctx
    assert 'build_date' in ctx

def test_global_context_loaded(tmp_path):
    context_dir = tmp_path / 'context'
    context_dir.mkdir()
    (context_dir / 'global.yaml').write_text('my_var: hello\n')

    chapter = tmp_path / 'ch.md'
    chapter.write_text('# Chapter')

    ctx = load_context(str(tmp_path), str(chapter), {})
    assert ctx['my_var'] == 'hello'
