"""Jinja2 template engine for markdown rendering."""

import os
import json
from datetime import datetime
from jinja2 import Environment, BaseLoader, TemplateError
import yaml


class StringLoader(BaseLoader):
    """Simple string template loader for Jinja2."""

    def __init__(self, template_string):
        self.template_string = template_string

    def get_source(self, environment, template):
        return self.template_string, None, lambda: True


def load_yaml_context(yaml_path):
    """Load YAML context file."""
    if not os.path.exists(yaml_path):
        return {}

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data if data is not None else {}
    except Exception as e:
        print(f"Warning: Could not load YAML context from {yaml_path}: {e}")
        return {}


def load_json_context(json_path):
    """Load JSON context file."""
    if not os.path.exists(json_path):
        return {}

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load JSON context from {json_path}: {e}")
        return {}


def get_chapter_name_from_path(chapter_path):
    """
    Extract chapter name from path for context file lookup.

    Examples:
        'content/01-introduction.md' -> '01-introduction'
        'content/02-chapter/01-section.md' -> '01-section'
    """
    filename = os.path.basename(chapter_path)
    if filename.endswith('.md'):
        return filename[:-3]
    return filename


def load_context(project_root, chapter_path, book_config):
    """
    Build merged context for a chapter.

    Context merge order (later overrides earlier):
    1. Built-in context (ebk_version, build_date)
    2. Global context (context/global.yaml or context/global.json)
    3. Chapter-specific context (context/{chapter-name}.yaml or .json)
    4. Book metadata (book.title, book.author, etc.)

    Args:
        project_root: Root directory of the ebk project
        chapter_path: Full path to the chapter markdown file
        book_config: Parsed config.yaml configuration

    Returns:
        dict: Merged context dictionary
    """
    from ebk import __version__

    # Start with built-in context
    context = {
        'ebk_version': __version__,
        'build_date': datetime.now().strftime('%Y-%m-%d'),
    }

    context_dir = os.path.join(project_root, 'context')

    # Load global context (try YAML first, then JSON)
    global_yaml = os.path.join(context_dir, 'global.yaml')
    global_json = os.path.join(context_dir, 'global.json')

    if os.path.exists(global_yaml):
        context.update(load_yaml_context(global_yaml))
    elif os.path.exists(global_json):
        context.update(load_json_context(global_json))

    # Load chapter-specific context
    chapter_name = get_chapter_name_from_path(chapter_path)
    chapter_yaml = os.path.join(context_dir, f'{chapter_name}.yaml')
    chapter_json = os.path.join(context_dir, f'{chapter_name}.json')

    if os.path.exists(chapter_yaml):
        context.update(load_yaml_context(chapter_yaml))
    elif os.path.exists(chapter_json):
        context.update(load_json_context(chapter_json))

    # Add book metadata
    if 'metadata' in book_config:
        context['book'] = book_config['metadata']

    # Add Tailwind class aliases
    if 'tw' in book_config:
        context['tw'] = book_config['tw']

    # Add feature flags (set for fast `in` checks in templates)
    context['flags'] = set(book_config.get('flags', []))

    return context


def render_template(md_content, context):
    """
    Render markdown content through Jinja2.

    Applies Jinja2 template rendering BEFORE markdown conversion.
    This allows variables, conditionals, and loops in markdown source.

    Args:
        md_content: Markdown content (possibly with Jinja2 syntax)
        context: Template context dictionary

    Returns:
        str: Rendered markdown (still markdown, not HTML)

    Raises:
        TemplateError: If Jinja2 rendering fails
    """
    try:
        env = Environment(loader=StringLoader(md_content))
        template = env.from_string(md_content)
        return template.render(**context)
    except TemplateError as e:
        # Try to provide helpful error message with line number
        error_msg = str(e)
        raise TemplateError(f"Jinja2 template error: {error_msg}") from e


def render_chapter(chapter_path, project_root, book_config):
    """
    Load and render a chapter with Jinja2 context.

    Args:
        chapter_path: Full path to chapter markdown file
        project_root: Root directory of ebk project
        book_config: Parsed config.yaml configuration

    Returns:
        str: Rendered markdown content (after Jinja2, before markdown->HTML)

    Raises:
        FileNotFoundError: If chapter file doesn't exist
        TemplateError: If Jinja2 rendering fails
    """
    # Read chapter content
    with open(chapter_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Load context
    context = load_context(project_root, chapter_path, book_config)

    # Render through Jinja2
    try:
        return render_template(md_content, context)
    except TemplateError as e:
        # Add chapter path to error message for debugging
        raise TemplateError(f"Error rendering {chapter_path}: {e}") from e
