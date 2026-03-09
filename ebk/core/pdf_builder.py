"""PDF generation from ebk project."""

import os
import re
import markdown
import yaml
from ebk.core.markdown_processor import get_chapters, get_chapter_title
from ebk.core.template_engine import render_chapter
from ebk.core.epub_builder import normalize_metadata


def _rewrite_img_srcs(html, images_map):
    """
    Rewrite <img src="..."> paths to absolute file:// URIs.

    Matches by filename so images are found regardless of the relative path
    used in the markdown source or the chapter's subdirectory depth.
    """
    def replace_src(m):
        src = m.group(1)
        # Skip already-absolute URLs (http://, https://, file://, data:)
        if re.match(r'^(?:https?|file|data):', src):
            return m.group(0)
        basename = os.path.basename(src)
        abs_path = images_map.get(basename)
        if abs_path and os.path.exists(abs_path):
            return f'src="{abs_path}"'
        return m.group(0)

    return re.sub(r'src="([^"]*)"', replace_src, html)


def build_pdf(project_root, output_path):
    """
    Build PDF from ebk project directory.

    Args:
        project_root: Root directory of ebk project
        output_path: Path for output .pdf file

    Raises:
        FileNotFoundError: If required files missing
        ValueError: If configuration invalid
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError(
            "weasyprint is required for PDF export. Install it with: pip install weasyprint"
        )

    print("Discovering chapters...")

    book_yaml_path = os.path.join(project_root, 'book.yaml')
    if not os.path.exists(book_yaml_path):
        raise FileNotFoundError("book.yaml not found")

    with open(book_yaml_path, 'r') as f:
        book_config = yaml.safe_load(f)

    metadata = normalize_metadata(book_config.get('metadata', {}))

    discovery_config = book_config.get('discovery', {})
    exclude_dirs = discovery_config.get('exclude', [
        '.git', '.venv', 'venv', 'node_modules', '__pycache__',
        '.ebk', 'build', 'dist', 'context'
    ])

    content_root_config = discovery_config.get('root', '.')
    content_root = project_root if content_root_config == '.' else os.path.join(project_root, content_root_config)

    chapters = get_chapters(content_root, exclude_dirs)

    if not chapters:
        raise ValueError(f"No markdown files found in {content_root}")

    print(f"  Found {len(chapters)} chapters")

    # Build CSS and image file maps from project files
    from ebk.core.epub_builder import get_all_files_with_paths
    css_extensions = discovery_config.get('css_extensions', ['.css'])
    css_files_map = get_all_files_with_paths(project_root, css_extensions, exclude_dirs)

    image_extensions = discovery_config.get('image_extensions', ['.jpg', '.jpeg', '.png', '.gif', '.svg'])
    images_map = get_all_files_with_paths(project_root, image_extensions, exclude_dirs)

    # Collect CSS content
    css_content = ""
    for css_path in css_files_map.values():
        if os.path.exists(css_path):
            with open(css_path, 'r') as f:
                css_content += f.read() + "\n"

    # Build table of contents HTML
    toc_items = "\n".join(
        f'  <li><a href="#{i}">{get_chapter_title(ch)}</a></li>'
        for i, ch in enumerate(chapters)
    )
    toc_html = f"""
<nav id="toc">
  <h1>Table of Contents</h1>
  <ol>
{toc_items}
  </ol>
</nav>
<div style="page-break-after: always;"></div>
"""

    print("Processing chapters...")

    # Render all chapters to HTML
    chapter_html_parts = []
    for i, chapter in enumerate(chapters):
        try:
            rendered_md = render_chapter(chapter['path'], project_root, book_config)

            md = markdown.Markdown(extensions=[
                'meta', 'codehilite', 'tables', 'fenced_code', 'footnotes',
            ])
            html_body = md.convert(rendered_md)

            html_body = _rewrite_img_srcs(html_body, images_map)
            chapter_html_parts.append(
                f'<section id="{i}" class="chapter">\n{html_body}\n</section>'
            )
        except Exception as e:
            print(f"  Error processing {chapter['name']}: {e}")
            raise

    title = metadata.get('dc:title', os.path.basename(project_root))
    author = metadata.get('dc:creator', '')

    # Assemble full HTML document
    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: Georgia, serif; line-height: 1.6; margin: 2cm; }}
    h1, h2, h3, h4, h5, h6 {{ font-family: Arial, sans-serif; }}
    .chapter {{ page-break-before: always; }}
    .chapter:first-of-type {{ page-break-before: avoid; }}
    pre {{ background: #f4f4f4; padding: 1em; overflow-x: auto; }}
    code {{ font-family: monospace; }}
    #toc ol {{ line-height: 2; }}
    img {{ max-width: 100%; height: auto; }}
    {css_content}
  </style>
</head>
<body>
  <div id="cover">
    <h1>{title}</h1>
    {"<p>" + author + "</p>" if author else ""}
  </div>
  <div style="page-break-after: always;"></div>
  {toc_html}
  {"".join(chapter_html_parts)}
</body>
</html>"""

    HTML(string=full_html, base_url=project_root).write_pdf(output_path)

    size_bytes = os.path.getsize(output_path)
    size_mb = size_bytes / (1024 * 1024)
    print(f"  Generated {output_path} ({size_mb:.1f} MB)")
