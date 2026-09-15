"""HTML output builder."""

import os
import shutil
import markdown
import yaml

from ebk.core.markdown_processor import get_chapters, get_chapter_title, filter_chapters
from ebk.core.template_engine import render_chapter
from ebk.core.links import build_source_index_map, rewrite_cross_links


def convert_chapter_to_html(md_content, css_files, title=""):
    """Convert rendered markdown to a standalone HTML5 page."""
    md = markdown.Markdown(extensions=[
        'meta',
        'codehilite',
        'tables',
        'fenced_code',
        'footnotes',
        'md_in_html',
    ])

    body = md.convert(md_content)

    css_links = '\n'.join([
        f'  <link rel="stylesheet" href="css/{css}">'
        for css in css_files
    ])

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
{css_links}
</head>
<body>
{body}
</body>
</html>'''


def build_html(project_root, output_dir, flags=None, chapters=None, no_toc=False):
    """
    Build HTML output from an ebk project.

    Writes one HTML file per chapter plus assets into output_dir.

    Args:
        project_root: Root directory of the ebk project
        output_dir: Directory to write HTML output into
        flags: List of active feature flag strings for conditional rendering
    """
    book_yaml_path = os.path.join(project_root, 'config.yaml')
    if not os.path.exists(book_yaml_path):
        raise FileNotFoundError("config.yaml not found")

    with open(book_yaml_path, 'r') as f:
        book_config = yaml.safe_load(f)

    book_config['flags'] = flags or []

    discovery_config = book_config.get('discovery', {})
    exclude_dirs = discovery_config.get('exclude', [
        '.git', '.venv', 'venv', 'node_modules', '__pycache__',
        '.ebk', 'build', 'dist', 'context'
    ])

    content_root_config = discovery_config.get('root', '.')
    content_root = project_root if content_root_config == '.' else os.path.join(project_root, content_root_config)

    chapters = filter_chapters(get_chapters(content_root, exclude_dirs), chapters or [])
    if not chapters:
        raise ValueError(f"No markdown files found in {content_root}")

    print(f"  Found {len(chapters)} chapters")

    # Collect CSS files
    from ebk.core.epub_builder import get_all_files_with_paths
    css_extensions = discovery_config.get('css_extensions', ['.css'])
    image_extensions = discovery_config.get('image_extensions', ['.jpg', '.jpeg', '.png', '.gif', '.svg'])

    css_files_map = get_all_files_with_paths(project_root, css_extensions, exclude_dirs)
    css_files = list(css_files_map.keys())

    if 'default_css' in book_config:
        for css in book_config['default_css']:
            if css not in css_files:
                legacy_path = os.path.join(project_root, 'assets', 'css', css)
                if os.path.exists(legacy_path):
                    css_files.append(css)
                    css_files_map[css] = legacy_path

    images_map = get_all_files_with_paths(project_root, image_extensions, exclude_dirs)

    # Prepare output directory
    os.makedirs(output_dir, exist_ok=True)
    css_out = os.path.join(output_dir, 'css')
    img_out = os.path.join(output_dir, 'images')
    os.makedirs(css_out, exist_ok=True)
    os.makedirs(img_out, exist_ok=True)

    # Build index (TOC)
    book_title = book_config.get('metadata', {}).get('title', 'Table of Contents')
    toc_items = []

    print("Processing chapters...")

    chapter_files = []
    src_index_map = build_source_index_map(chapters)
    for i, chapter in enumerate(chapters):
        slug = f's{i:05d}'
        filename = f'{slug}.html'
        title = get_chapter_title(chapter)
        chapter_files.append((filename, title))

        rendered_md = render_chapter(chapter['path'], project_root, book_config)
        html = convert_chapter_to_html(rendered_md, css_files, title=title)
        html = rewrite_cross_links(html, src_index_map, 'html')

        with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as f:
            f.write(html)

        toc_items.append(f'    <li><a href="{filename}">{title}</a></li>')
        print(f"  {filename}: {title}")

    # Write index.html
    if not no_toc:
        css_links = '\n'.join([
            f'  <link rel="stylesheet" href="css/{css}">'
            for css in css_files
        ])
        toc_list = '\n'.join(toc_items)
        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{book_title}</title>
{css_links}
</head>
<body>
  <nav>
    <h1>{book_title}</h1>
    <ol>
{toc_list}
    </ol>
  </nav>
</body>
</html>'''

        with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(index_html)

    # Copy CSS
    for css, path in css_files_map.items():
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(css_out, css))

    # Copy images
    for img, path in images_map.items():
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(img_out, img))

    print(f"  Output written to {output_dir}/")
