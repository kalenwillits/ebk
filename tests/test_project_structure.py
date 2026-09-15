"""Tests for ebk "Name" project scaffolding."""

import os
import pytest
from ebk.core.project_structure import create_new_book


def test_scaffolds_all_starter_files(tmp_path):
    project_dir = tmp_path / "My Book"
    create_new_book(str(project_dir))

    assert (project_dir / '.ebk').exists()
    assert (project_dir / 'config.yaml').exists()
    assert (project_dir / '01-introduction.md').exists()
    assert (project_dir / 'custom.css').exists()
    assert (project_dir / 'context' / 'global.yaml').exists()
    assert (project_dir / 'README.md').exists()


def test_template_vars_are_substituted(tmp_path):
    project_dir = tmp_path / "My Book"
    create_new_book(str(project_dir))

    config = (project_dir / 'config.yaml').read_text()
    assert 'My Book' in config
    assert '{book_title}' not in config

    chapter = (project_dir / '01-introduction.md').read_text()
    assert 'My Book' in chapter
    assert '{book_title}' not in chapter

    readme = (project_dir / 'README.md').read_text()
    assert 'My Book' in readme
    assert '{book_title}' not in readme


def test_rescaffolding_existing_directory_does_not_clobber_files(tmp_path):
    """Scaffolding into an existing directory with some content already
    present should not overwrite that content (only config.yaml + .ebk are
    always (re)written)."""
    project_dir = tmp_path / "existing"
    project_dir.mkdir()
    (project_dir / '01-introduction.md').write_text("# My own intro\n\nDon't touch this.")
    (project_dir / 'custom.css').write_text("body { color: green; }\n")

    create_new_book(str(project_dir))

    assert (project_dir / '01-introduction.md').read_text() == "# My own intro\n\nDon't touch this."
    assert (project_dir / 'custom.css').read_text() == "body { color: green; }\n"
    # config.yaml and .ebk are still created
    assert (project_dir / 'config.yaml').exists()
    assert (project_dir / '.ebk').exists()


def test_second_scaffold_call_raises_if_already_a_project(tmp_path):
    project_dir = tmp_path / "My Book"
    create_new_book(str(project_dir))
    with pytest.raises(FileExistsError):
        create_new_book(str(project_dir))
