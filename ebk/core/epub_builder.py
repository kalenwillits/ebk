"""EPUB generation (adapted from mark2epub)."""

import os
import zipfile
from xml.dom import minidom
import markdown
import yaml
from ebk.core.markdown_processor import get_chapters, get_chapter_title
from ebk.core.template_engine import render_chapter


def get_all_filenames(dir_path, extensions):
    """Get all files with specified extensions in directory."""
    if not os.path.exists(dir_path):
        return []

    files = []
    for item in os.listdir(dir_path):
        full_path = os.path.join(dir_path, item)
        if os.path.isfile(full_path):
            if any(item.lower().endswith(ext) for ext in extensions):
                files.append(item)
    return sorted(files)


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
    css_links = '\n'.join([
        f'  <link rel="stylesheet" type="text/css" href="css/{css}" />'
        for css in css_files
    ])

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
    css_links = '\n'.join([
        f'  <link rel="stylesheet" type="text/css" href="css/{css}" />'
        for css in css_files
    ])

    # Build navigation list
    nav_items = []

    if has_cover:
        nav_items.append('    <li><a href="titlepage.xhtml">Cover</a></li>')

    for i, chapter in enumerate(chapters):
        title = get_chapter_title(chapter)
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


def get_packageOPF_XML(chapters, images, css_files, metadata, has_cover):
    """Generate package.opf (manifest, spine, metadata)."""
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
    ])

    html_content = md.convert(md_content)

    # Wrap in XHTML structure
    css_links = '\n'.join([
        f'  <link rel="stylesheet" type="text/css" href="css/{css}" />'
        for css in css_files
    ])

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


def build_epub(project_root, output_path):
    """
    Build EPUB from ebk project directory.

    Args:
        project_root: Root directory of ebk project
        output_path: Path for output .epub file

    Raises:
        FileNotFoundError: If required files missing
        ValueError: If configuration invalid
    """
    print("Discovering chapters...")

    # Load book.yaml configuration
    book_yaml_path = os.path.join(project_root, 'book.yaml')
    if not os.path.exists(book_yaml_path):
        raise FileNotFoundError("book.yaml not found")

    with open(book_yaml_path, 'r') as f:
        book_config = yaml.safe_load(f)

    metadata = book_config.get('metadata', {})

    # Get chapters
    content_dir = os.path.join(project_root, 'content')
    chapters = get_chapters(content_dir)

    if not chapters:
        raise ValueError("No markdown files found in content/")

    print(f"  Found {len(chapters)} chapters")

    # Get CSS files
    css_dir = os.path.join(project_root, 'assets', 'css')
    css_files = get_all_filenames(css_dir, ['.css'])

    # Add default CSS from book config
    if 'default_css' in book_config:
        for css in book_config['default_css']:
            if css not in css_files:
                css_files.append(css)

    # Get images
    images_dir = os.path.join(project_root, 'assets', 'images')
    images = get_all_filenames(images_dir, ['.jpg', '.jpeg', '.png', '.gif', '.svg'])

    # Check for cover image
    cover_image = book_config.get('cover_image')
    has_cover = False
    if cover_image and cover_image in images:
        has_cover = True
    elif cover_image:
        print(f"  Warning: Cover image '{cover_image}' not found, skipping")

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
        for i, chapter in enumerate(chapters):
            try:
                # Render chapter through Jinja2
                rendered_md = render_chapter(chapter['path'], project_root, book_config)

                # Convert to XHTML
                xhtml = convert_chapter_to_xhtml(rendered_md, css_files)

                # Add to EPUB
                epub.writestr(f'OPS/s{i:05d}.xhtml', xhtml)

            except Exception as e:
                print(f"  Error processing {chapter['name']}: {e}")
                raise

        # Add CSS files
        for css in css_files:
            css_path = os.path.join(css_dir, css)
            if os.path.exists(css_path):
                with open(css_path, 'r') as f:
                    epub.writestr(f'OPS/css/{css}', f.read())

        # Add images
        for img in images:
            img_path = os.path.join(images_dir, img)
            if os.path.exists(img_path):
                with open(img_path, 'rb') as f:
                    epub.writestr(f'OPS/images/{img}', f.read())

        # Add package.opf (must be last to include all manifest items)
        package_opf = get_packageOPF_XML(chapters, images, css_files, metadata, has_cover)
        epub.writestr('OPS/package.opf', package_opf)

    # Get file size
    size_bytes = os.path.getsize(output_path)
    size_mb = size_bytes / (1024 * 1024)

    print(f"  Generated {output_path} ({size_mb:.1f} MB)")
