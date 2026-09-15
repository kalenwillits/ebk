"""EPUB generation (adapted from mark2epub)."""

import os
import zipfile
from xml.dom import minidom
import markdown
import yaml
from ebk.core.markdown_processor import (
    get_chapters,
    get_chapter_title,
    filter_chapters,
)
from ebk.core.template_engine import render_chapter
from ebk.core.links import build_source_index_map, rewrite_cross_links
from ebk.core.styles import (
    get_all_filenames,
    get_all_files_with_paths,
    get_all_filenames_recursive,
    resolve_css_layers,
    render_css_links,
    write_css_layers_epub,
)
from ebk.core.tailwind import try_compile_tailwind_css


_METADATA_KEY_MAP = {
    'title': 'dc:title',
    'author': 'dc:creator',
    'creator': 'dc:creator',
    'language': 'dc:language',
    'identifier': 'dc:identifier',
    'date': 'dc:date',
    'publisher': 'dc:publisher',
    'description': 'dc:description',
    'subject': 'dc:subject',
    'source': 'dc:source',
    'contributor': 'dc:contributor',
    'rights': 'dc:rights',
}


def normalize_metadata(metadata):
    """Map short metadata keys (title, author, ...) to their dc: equivalents."""
    normalized = {}
    for key, value in metadata.items():
        normalized_key = _METADATA_KEY_MAP.get(key, key)
        normalized[normalized_key] = value
    return normalized


def get_container_XML():
    """Generate META-INF/container.xml."""
    return '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''


def get_coverpage_XML(cover_image, css_files):
    """Generate titlepage.xhtml for cover image."""
    css_links = render_css_links(css_files, xhtml=True)

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Cover</title>
{css_links}
</head>
<body>
  <div style="text-align: center;">
    <img src="images/{cover_image}" alt="Cover" style="max-width: 100%;" />
  </div>
</body>
</html>'''


def get_TOC_XML(css_files, chapters, has_cover):
    """Generate TOC.xhtml (EPUB 3 navigation)."""
    from html import escape as html_escape

    css_links = render_css_links(css_files, xhtml=True)

    # Build navigation list
    nav_items = []

    if has_cover:
        nav_items.append('    <li><a href="titlepage.xhtml">Cover</a></li>')

    for i, chapter in enumerate(chapters):
        title = html_escape(get_chapter_title(chapter))
        filename = f's{i:05d}.xhtml'
        nav_items.append(f'    <li><a href="{filename}">{title}</a></li>')

    nav_list = '\n'.join(nav_items)

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Table of Contents</title>
{css_links}
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
{nav_list}
    </ol>
  </nav>
</body>
</html>'''


def get_TOCNCX_XML(chapters, metadata, has_cover):
    """Generate toc.ncx (backward compatibility for EPUB 2)."""
    doc = minidom.Document()

    # Root element
    ncx = doc.createElement('ncx')
    ncx.setAttribute('xmlns', 'http://www.daisy.org/z3986/2005/ncx/')
    ncx.setAttribute('version', '2005-1')
    doc.appendChild(ncx)

    # Head
    head = doc.createElement('head')
    ncx.appendChild(head)

    meta_uid = doc.createElement('meta')
    meta_uid.setAttribute('name', 'dtb:uid')
    meta_uid.setAttribute('content', metadata.get('dc:identifier', 'unknown'))
    head.appendChild(meta_uid)

    # Doc title
    doc_title = doc.createElement('docTitle')
    text = doc.createElement('text')
    text.appendChild(doc.createTextNode(metadata.get('dc:title', 'Untitled')))
    doc_title.appendChild(text)
    ncx.appendChild(doc_title)

    # Nav map
    nav_map = doc.createElement('navMap')
    ncx.appendChild(nav_map)

    play_order = 1

    # Add cover if present
    if has_cover:
        nav_point = doc.createElement('navPoint')
        nav_point.setAttribute('id', 'navpoint-cover')
        nav_point.setAttribute('playOrder', str(play_order))

        nav_label = doc.createElement('navLabel')
        text = doc.createElement('text')
        text.appendChild(doc.createTextNode('Cover'))
        nav_label.appendChild(text)
        nav_point.appendChild(nav_label)

        content = doc.createElement('content')
        content.setAttribute('src', 'titlepage.xhtml')
        nav_point.appendChild(content)

        nav_map.appendChild(nav_point)
        play_order += 1

    # Add chapters
    for i, chapter in enumerate(chapters):
        nav_point = doc.createElement('navPoint')
        nav_point.setAttribute('id', f'navpoint-{i+1}')
        nav_point.setAttribute('playOrder', str(play_order))

        nav_label = doc.createElement('navLabel')
        text = doc.createElement('text')
        title = get_chapter_title(chapter)
        text.appendChild(doc.createTextNode(title))
        nav_label.appendChild(text)
        nav_point.appendChild(nav_label)

        content = doc.createElement('content')
        content.setAttribute('src', f's{i:05d}.xhtml')
        nav_point.appendChild(content)

        nav_map.appendChild(nav_point)
        play_order += 1

    return doc.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')


def get_packageOPF_XML(chapters, images, css_files, metadata, has_cover, fonts=None):
    """Generate package.opf (manifest, spine, metadata)."""
    if fonts is None:
        fonts = []

    doc = minidom.Document()

    # Root package element
    package = doc.createElement('package')
    package.setAttribute('xmlns', 'http://www.idpf.org/2007/opf')
    package.setAttribute('unique-identifier', 'BookID')
    package.setAttribute('version', '3.0')
    doc.appendChild(package)

    # Metadata section
    meta_elem = doc.createElement('metadata')
    meta_elem.setAttribute('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
    meta_elem.setAttribute('xmlns:opf', 'http://www.idpf.org/2007/opf')
    meta_elem.setAttribute('xmlns:dcterms', 'http://purl.org/dc/terms/')
    package.appendChild(meta_elem)

    # Add DC metadata
    dc_fields = [
        'dc:title', 'dc:creator', 'dc:language', 'dc:identifier',
        'dc:date', 'dc:publisher', 'dc:description', 'dc:subject',
        'dc:source', 'dc:contributor', 'dc:rights'
    ]

    for field in dc_fields:
        value = metadata.get(field, '')
        if value:
            elem = doc.createElement(field)
            if field == 'dc:identifier':
                elem.setAttribute('id', 'BookID')
            elem.appendChild(doc.createTextNode(str(value)))
            meta_elem.appendChild(elem)

    # Required by EPUB 3.0: dcterms:modified timestamp
    from datetime import datetime, timezone
    modified = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    meta_modified = doc.createElement('meta')
    meta_modified.setAttribute('property', 'dcterms:modified')
    meta_modified.appendChild(doc.createTextNode(modified))
    meta_elem.appendChild(meta_modified)

    # Manifest section
    manifest = doc.createElement('manifest')
    package.appendChild(manifest)

    # Add TOC files
    item = doc.createElement('item')
    item.setAttribute('id', 'ncx')
    item.setAttribute('href', 'toc.ncx')
    item.setAttribute('media-type', 'application/x-dtbncx+xml')
    manifest.appendChild(item)

    item = doc.createElement('item')
    item.setAttribute('id', 'toc')
    item.setAttribute('href', 'TOC.xhtml')
    item.setAttribute('media-type', 'application/xhtml+xml')
    item.setAttribute('properties', 'nav')
    manifest.appendChild(item)

    # Add cover page if present
    if has_cover:
        item = doc.createElement('item')
        item.setAttribute('id', 'titlepage')
        item.setAttribute('href', 'titlepage.xhtml')
        item.setAttribute('media-type', 'application/xhtml+xml')
        manifest.appendChild(item)

    # Add chapters
    for i in range(len(chapters)):
        item = doc.createElement('item')
        item.setAttribute('id', f's{i:05d}')
        item.setAttribute('href', f's{i:05d}.xhtml')
        item.setAttribute('media-type', 'application/xhtml+xml')
        manifest.appendChild(item)

    # Add CSS files
    for css in css_files:
        item = doc.createElement('item')
        item.setAttribute('id', f'css-{css}')
        item.setAttribute('href', f'css/{css}')
        item.setAttribute('media-type', 'text/css')
        manifest.appendChild(item)

    # Add fonts
    for font in fonts:
        item = doc.createElement('item')
        # Sanitize font filename for ID
        font_id = font.replace('.', '-').replace(' ', '-')
        item.setAttribute('id', f'font-{font_id}')
        item.setAttribute('href', f'fonts/{font}')

        # Determine media type based on extension
        if font.lower().endswith('.ttf'):
            media_type = 'application/x-font-ttf'
        elif font.lower().endswith('.otf'):
            media_type = 'application/x-font-otf'
        elif font.lower().endswith('.woff'):
            media_type = 'application/font-woff'
        elif font.lower().endswith('.woff2'):
            media_type = 'font/woff2'
        else:
            media_type = 'application/octet-stream'

        item.setAttribute('media-type', media_type)
        manifest.appendChild(item)

    # Add images
    for img in images:
        item = doc.createElement('item')
        item.setAttribute('id', f'img-{img}')
        item.setAttribute('href', f'images/{img}')

        # Determine media type
        if img.lower().endswith('.jpg') or img.lower().endswith('.jpeg'):
            media_type = 'image/jpeg'
        elif img.lower().endswith('.png'):
            media_type = 'image/png'
        elif img.lower().endswith('.gif'):
            media_type = 'image/gif'
        elif img.lower().endswith('.svg'):
            media_type = 'image/svg+xml'
        else:
            media_type = 'application/octet-stream'

        item.setAttribute('media-type', media_type)
        manifest.appendChild(item)

    # Spine section (reading order)
    spine = doc.createElement('spine')
    spine.setAttribute('toc', 'ncx')
    package.appendChild(spine)

    if has_cover:
        itemref = doc.createElement('itemref')
        itemref.setAttribute('idref', 'titlepage')
        spine.appendChild(itemref)

    for i in range(len(chapters)):
        itemref = doc.createElement('itemref')
        itemref.setAttribute('idref', f's{i:05d}')
        spine.appendChild(itemref)

    # Guide section (optional, for backward compatibility)
    guide = doc.createElement('guide')
    package.appendChild(guide)

    if has_cover:
        reference = doc.createElement('reference')
        reference.setAttribute('type', 'cover')
        reference.setAttribute('title', 'Cover')
        reference.setAttribute('href', 'titlepage.xhtml')
        guide.appendChild(reference)

    reference = doc.createElement('reference')
    reference.setAttribute('type', 'toc')
    reference.setAttribute('title', 'Table of Contents')
    reference.setAttribute('href', 'TOC.xhtml')
    guide.appendChild(reference)

    return doc.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')


def convert_chapter_to_xhtml(md_content, css_files):
    """Convert markdown chapter to XHTML."""
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=[
        'meta',
        'codehilite',
        'tables',
        'fenced_code',
        'footnotes',
        'md_in_html',
    ])

    html_content = md.convert(md_content)

    # Wrap in XHTML structure
    css_links = render_css_links(css_files, xhtml=True)

    xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8" />
  <title>Chapter</title>
{css_links}
</head>
<body>
{html_content}
</body>
</html>'''

    return xhtml


def build_epub(project_root, output_path, flags=None, chapters=None):
    """
    Build EPUB from ebk project directory.

    Args:
        project_root: Root directory of ebk project
        output_path: Path for output .epub file
        flags: List of active feature flag strings for conditional rendering
        chapters: List of chapter selectors (1-based index or filename substring);
                  if empty or None, all chapters are included

    Raises:
        FileNotFoundError: If required files missing
        ValueError: If configuration invalid
    """
    print("Discovering chapters...")

    # Load config.yaml configuration
    book_yaml_path = os.path.join(project_root, 'config.yaml')
    if not os.path.exists(book_yaml_path):
        raise FileNotFoundError("config.yaml not found")

    with open(book_yaml_path, 'r') as f:
        book_config = yaml.safe_load(f)

    book_config['flags'] = flags or []
    metadata = normalize_metadata(book_config.get('metadata', {}))

    # Get discovery configuration with defaults
    discovery_config = book_config.get('discovery', {})
    exclude_dirs = discovery_config.get('exclude', [
        '.git', '.venv', 'venv', 'node_modules', '__pycache__',
        '.ebk', 'build', 'dist', 'context'
    ])

    # Determine content root from discovery config (default: project root)
    content_root_config = discovery_config.get('root', '.')
    if content_root_config == '.':
        content_root = project_root
    else:
        content_root = os.path.join(project_root, content_root_config)

    # Get extension configurations
    content_extensions = discovery_config.get('content_extensions', ['.md'])
    css_extensions = discovery_config.get('css_extensions', ['.css'])
    image_extensions = discovery_config.get('image_extensions',
                                           ['.jpg', '.jpeg', '.png', '.gif', '.svg'])

    # Get chapters with exclusion support
    chapters = filter_chapters(get_chapters(content_root, exclude_dirs), chapters or [])

    if not chapters:
        raise ValueError(f"No markdown files found in {content_root}")

    print(f"  Found {len(chapters)} chapters")

    # Resolve CSS layers: default.css base, then project CSS (default_css: +
    # recursive discovery + legacy assets/css/ fallback)
    tailwind_layer = try_compile_tailwind_css(project_root, book_config)
    css_layers = resolve_css_layers(
        project_root, book_config, exclude_dirs, css_extensions, tailwind_css=tailwind_layer
    )
    css_files = [layer.name for layer in css_layers]

    # Get images with recursive discovery
    images_map = get_all_files_with_paths(project_root, image_extensions, exclude_dirs)
    images = list(images_map.keys())

    # Check for cover image
    cover_image = book_config.get('cover_image')
    has_cover = False
    if cover_image and cover_image in images:
        has_cover = True
    elif cover_image:
        print(f"  Warning: Cover image '{cover_image}' not found")

    print("Processing chapters...")

    # Create EPUB ZIP file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
        # Add mimetype (must be first, uncompressed)
        epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

        # Add container.xml
        epub.writestr('META-INF/container.xml', get_container_XML())

        # Add cover page if present
        if has_cover:
            epub.writestr('OPS/titlepage.xhtml', get_coverpage_XML(cover_image, css_files))

        # Add TOC files
        epub.writestr('OPS/TOC.xhtml', get_TOC_XML(css_files, chapters, has_cover))
        epub.writestr('OPS/toc.ncx', get_TOCNCX_XML(chapters, metadata, has_cover))

        # Convert and add chapters
        src_index_map = build_source_index_map(chapters)
        for i, chapter in enumerate(chapters):
            try:
                # Render chapter through Jinja2
                rendered_md = render_chapter(chapter['path'], project_root, book_config)

                # Convert to XHTML
                xhtml = convert_chapter_to_xhtml(rendered_md, css_files)
                xhtml = rewrite_cross_links(xhtml, src_index_map, 'epub')

                # Add to EPUB
                epub.writestr(f'OPS/s{i:05d}.xhtml', xhtml)

            except Exception as e:
                print(f"  Error processing {chapter['name']}: {e}")
                raise

        # Add CSS files
        write_css_layers_epub(epub, css_layers)

        # Add images
        for img in images:
            img_path = images_map.get(img)
            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as f:
                    epub.writestr(f'OPS/images/{img}', f.read())
            else:
                print(f"  Warning: Image file '{img}' not found, skipping")

        # Add embedded fonts from ebk resources
        from pathlib import Path
        ebk_package_dir = Path(__file__).parent.parent
        fonts_dir = ebk_package_dir / 'resources' / 'fonts'
        fonts = []

        if fonts_dir.exists():
            for font_file in fonts_dir.glob('*'):
                if font_file.suffix.lower() in ['.ttf', '.otf', '.woff', '.woff2']:
                    fonts.append(font_file.name)
                    with open(font_file, 'rb') as f:
                        epub.writestr(f'OPS/fonts/{font_file.name}', f.read())

        # Add package.opf (must be last to include all manifest items)
        package_opf = get_packageOPF_XML(chapters, images, css_files, metadata, has_cover, fonts)
        epub.writestr('OPS/package.opf', package_opf)

    # Get file size
    size_bytes = os.path.getsize(output_path)
    size_mb = size_bytes / (1024 * 1024)

    print(f"  Generated {output_path} ({size_mb:.1f} MB)")
