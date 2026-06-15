"""ODT (OpenDocument Text / LibreOffice) output builder.

Reuses ebk's shared pipeline (chapter discovery, Jinja2 rendering, markdown ->
HTML) and converts the resulting HTML into ODF elements with the pure-Python
``odfpy`` library, so no external binary (pandoc, LibreOffice) is required.
"""

import os
from html.parser import HTMLParser
from html import unescape

import markdown
import yaml

from ebk.core.markdown_processor import get_chapters, get_chapter_title, filter_chapters
from ebk.core.template_engine import render_chapter
from ebk.core.epub_builder import (
    normalize_metadata,
    get_all_files_with_paths,
)


# Heading tags -> ODF outline level
_HEADING_LEVELS = {'h1': 1, 'h2': 2, 'h3': 3, 'h4': 4, 'h5': 5, 'h6': 6}


def _make_styles(doc, text, style):
    """Register the small set of named styles the converter relies on.

    Returns a dict of style-name -> name string for convenient reference.
    """
    from odf.style import (
        Style, TextProperties, ParagraphProperties,
        TableProperties, TableColumnProperties, TableCellProperties,
    )

    names = {}

    # Inline emphasis styles (text-level / spans)
    bold = Style(name='ebk-bold', family='text')
    bold.addElement(TextProperties(fontweight='bold'))
    doc.automaticstyles.addElement(bold)
    names['bold'] = 'ebk-bold'

    italic = Style(name='ebk-italic', family='text')
    italic.addElement(TextProperties(fontstyle='italic'))
    doc.automaticstyles.addElement(italic)
    names['italic'] = 'ebk-italic'

    code = Style(name='ebk-code', family='text')
    code.addElement(TextProperties(fontname='Courier New', fontfamily='monospace'))
    doc.automaticstyles.addElement(code)
    names['code'] = 'ebk-code'

    # Paragraph-level styles
    pre = Style(name='ebk-pre', family='paragraph')
    pre.addElement(TextProperties(fontname='Courier New', fontfamily='monospace'))
    pre.addElement(ParagraphProperties(
        backgroundcolor='#f4f4f4',
        margintop='0.1cm', marginbottom='0.1cm',
    ))
    doc.styles.addElement(pre)
    names['pre'] = 'ebk-pre'

    quote = Style(name='ebk-quote', family='paragraph')
    quote.addElement(ParagraphProperties(marginleft='1cm', marginright='1cm'))
    quote.addElement(TextProperties(fontstyle='italic'))
    doc.styles.addElement(quote)
    names['quote'] = 'ebk-quote'

    # Page-break-before paragraph style (used to start each chapter on a new page)
    pagebreak = Style(name='ebk-pagebreak', family='paragraph')
    pagebreak.addElement(ParagraphProperties(breakbefore='page'))
    doc.automaticstyles.addElement(pagebreak)
    names['pagebreak'] = 'ebk-pagebreak'

    # Table styles: a sized table, evenly-divided columns, bordered cells.
    tbl = Style(name='ebk-table', family='table')
    tbl.addElement(TableProperties(width='17cm', align='margins'))
    doc.automaticstyles.addElement(tbl)
    names['table'] = 'ebk-table'

    col = Style(name='ebk-table-col', family='table-column')
    col.addElement(TableColumnProperties(columnwidth='4cm'))
    doc.automaticstyles.addElement(col)
    names['table-col'] = 'ebk-table-col'

    cell = Style(name='ebk-table-cell', family='table-cell')
    cell.addElement(TableCellProperties(
        border='0.5pt solid #888888',
        padding='0.1cm',
    ))
    doc.automaticstyles.addElement(cell)
    names['table-cell'] = 'ebk-table-cell'

    return names


class _HTMLToODF(HTMLParser):
    """Walk markdown-generated HTML and emit ODF elements into a container.

    A pragmatic, stack-based converter covering the elements python-markdown
    actually produces. Unrecognised tags degrade to their text content inside
    the current block (or a fresh paragraph at the top level).
    """

    def __init__(self, doc, container, style_names, images_map):
        super().__init__(convert_charrefs=True)
        self.doc = doc
        self.container = container
        self.styles = style_names
        self.images_map = images_map

        # odfpy element classes
        from odf import text, draw, table
        self.text = text
        self.draw = draw
        self.table = table

        self.block = None          # current block element (P / H) or None
        self.span_styles = []      # stack of active inline style names
        self.list_stack = []       # stack of (List element, is_ordered)
        self.list_item_stack = []  # stack of current ListItem elements
        self.in_pre = False
        self.href = None           # active anchor target
        self.table_stack = []      # stack of Table elements
        self.row = None
        self.cell = None
        self.skip_depth = 0        # depth counter for content we drop (e.g. <head>)

    # -- helpers ----------------------------------------------------------
    def _parent(self):
        """Where new block elements should be appended."""
        if self.list_item_stack:
            return self.list_item_stack[-1]
        if self.cell is not None:
            return self.cell
        return self.container

    def _new_block(self, element):
        self.block = element
        self._parent().addElement(element)

    def _add_text(self, data):
        if not data:
            return
        if self.block is None:
            # Start an implicit paragraph for stray text
            self._new_block(self.text.P())

        # Build the (possibly styled / linked) text node
        node = None
        if self.span_styles:
            node = self.text.Span(stylename=self.span_styles[-1], text=data)
        if self.href is not None:
            link = self.text.A(href=self.href)
            if node is not None:
                link.addElement(node)
            else:
                link.addText(data)
            self.block.addElement(link)
            return
        if node is not None:
            self.block.addElement(node)
        else:
            self.block.addText(data)

    # -- parser callbacks -------------------------------------------------
    def handle_starttag(self, tag, attrs):
        if self.skip_depth:
            self.skip_depth += 1
            return
        attrs = dict(attrs)

        if tag in ('html', 'head', 'meta', 'title', 'link', 'style', 'script'):
            # Drop document scaffolding and its content
            if tag in ('head', 'style', 'script', 'title'):
                self.skip_depth = 1
            return

        if tag in _HEADING_LEVELS:
            self._new_block(self.text.H(outlinelevel=_HEADING_LEVELS[tag]))
        elif tag == 'p':
            self._new_block(self.text.P())
        elif tag == 'br':
            if self.block is not None:
                self.block.addElement(self.text.LineBreak())
        elif tag in ('strong', 'b'):
            self.span_styles.append(self.styles['bold'])
        elif tag in ('em', 'i'):
            self.span_styles.append(self.styles['italic'])
        elif tag == 'code' and not self.in_pre:
            self.span_styles.append(self.styles['code'])
        elif tag == 'pre':
            self.in_pre = True
            self._new_block(self.text.P(stylename=self.styles['pre']))
        elif tag == 'a':
            self.href = attrs.get('href')
        elif tag in ('ul', 'ol'):
            lst = self.text.List()
            self._parent().addElement(lst)
            self.list_stack.append((lst, tag == 'ol'))
        elif tag == 'li':
            if self.list_stack:
                item = self.text.ListItem()
                self.list_stack[-1][0].addElement(item)
                self.list_item_stack.append(item)
                self.block = None
        elif tag == 'blockquote':
            self._new_block(self.text.P(stylename=self.styles['quote']))
        elif tag == 'img':
            self._add_image(attrs.get('src', ''), attrs.get('alt', ''))
        elif tag == 'table':
            # Buffer the table: column count isn't known until rows are parsed,
            # so we collect cells and emit the whole table on </table>.
            self.table_stack.append({'parent': self._parent(), 'rows': []})
        elif tag == 'tr':
            if self.table_stack:
                self.row = []
                self.table_stack[-1]['rows'].append(self.row)
        elif tag in ('td', 'th'):
            if self.row is not None:
                self.cell = self.table.TableCell(
                    valuetype='string', stylename=self.styles['table-cell'])
                self.row.append(self.cell)
                self.block = None
                if tag == 'th':
                    # Header cells: bold their text via the existing span style
                    self.span_styles.append(self.styles['bold'])
        # Other tags (div, span, section, etc.) are transparent: their text
        # flows into the current block.

    def handle_endtag(self, tag):
        if self.skip_depth:
            self.skip_depth -= 1
            return

        if tag in _HEADING_LEVELS or tag == 'p':
            self.block = None
        elif tag in ('strong', 'b'):
            self._pop(self.styles['bold'])
        elif tag in ('em', 'i'):
            self._pop(self.styles['italic'])
        elif tag == 'code' and not self.in_pre:
            self._pop(self.styles['code'])
        elif tag == 'pre':
            self.in_pre = False
            self.block = None
        elif tag == 'a':
            self.href = None
        elif tag in ('ul', 'ol'):
            if self.list_stack:
                self.list_stack.pop()
            self.block = None
        elif tag == 'li':
            if self.list_item_stack:
                self.list_item_stack.pop()
            self.block = None
        elif tag == 'blockquote':
            self.block = None
        elif tag == 'table':
            if self.table_stack:
                self._emit_table(self.table_stack.pop())
            self.block = None
        elif tag == 'tr':
            self.row = None
        elif tag in ('td', 'th'):
            if tag == 'th':
                self._pop(self.styles['bold'])
            self.cell = None
            self.block = None

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.in_pre:
            self._add_text(data)
            return
        # Collapse insignificant whitespace between block elements
        if self.block is None and not data.strip():
            return
        self._add_text(data)

    def _pop(self, name):
        if self.span_styles and self.span_styles[-1] == name:
            self.span_styles.pop()

    def _emit_table(self, buf):
        """Build a complete ODF table from a buffered table and add it to its parent.

        ODF requires <table:table-column> elements (one per column) before the
        rows, so the table can only be assembled once the column count is known.
        """
        rows = buf['rows']
        if not rows:
            return
        ncols = max(len(r) for r in rows)
        if ncols == 0:
            return

        tbl = self.table.Table(stylename=self.styles['table'])
        # Column definitions (required for correct layout in LibreOffice)
        tbl.addElement(self.table.TableColumn(
            stylename=self.styles['table-col'], numbercolumnsrepeated=ncols))

        for cells in rows:
            tr = self.table.TableRow()
            for cell in cells:
                # Ensure every cell has at least one paragraph
                if not cell.childNodes:
                    cell.addElement(self.text.P())
                tr.addElement(cell)
            # Pad short rows so every row spans all columns
            for _ in range(ncols - len(cells)):
                empty = self.table.TableCell(
                    valuetype='string', stylename=self.styles['table-cell'])
                empty.addElement(self.text.P())
                tr.addElement(empty)
            tbl.addElement(tr)

        buf['parent'].addElement(tbl)

    def _add_image(self, src, alt):
        if not src:
            return
        # Skip remote / data URIs — only embed local project images
        if src.startswith(('http://', 'https://', 'data:', 'file:')):
            return
        path = self.images_map.get(os.path.basename(src))
        if not path or not os.path.exists(path):
            return
        try:
            href = self.doc.addPictureFromFile(path)
        except Exception:
            return
        # Wrap the image in a paragraph so it has a place in the text flow
        para = self.text.P()
        self._parent().addElement(para)
        frame = self.draw.Frame(
            width='12cm', anchortype='paragraph', name=os.path.basename(src),
        )
        frame.addElement(self.draw.Image(href=href))
        para.addElement(frame)
        self.block = None


def _add_cover(doc, text, metadata, project_root):
    """Add a simple title/author cover page followed by a page break."""
    title = metadata.get('dc:title') or os.path.basename(os.path.abspath(project_root))
    author = metadata.get('dc:creator', '')

    doc.text.addElement(text.H(outlinelevel=1, text=str(title)))
    if author:
        doc.text.addElement(text.P(text=str(author)))


def _add_toc(doc, text):
    """Insert a native, LibreOffice-regenerable table of contents."""
    toc = text.TableOfContent(name='Table of Contents')
    src = text.TableOfContentSource(outlinelevel=6)
    title_tmpl = text.IndexTitleTemplate()
    title_tmpl.addText('Table of Contents')
    src.addElement(title_tmpl)
    toc.addElement(src)
    doc.text.addElement(toc)


def build_odt(project_root, output_path, flags=None, chapters=None,
              no_cover=False, no_toc=False):
    """Build an OpenDocument Text (.odt) file from an ebk project.

    Args:
        project_root: Root directory of the ebk project.
        output_path: Path for the output .odt file.
        flags: List of active feature flag strings for conditional rendering.
        chapters: Optional chapter selectors (see filter_chapters).
        no_cover: If True, omit the title/author cover page.
        no_toc: If True, omit the table of contents.

    Raises:
        ImportError: If odfpy is not installed.
        FileNotFoundError: If book.yaml is missing.
        ValueError: If no chapters are found.
    """
    try:
        from odf.opendocument import OpenDocumentText
        from odf import text, style, draw, table  # noqa: F401 (used via converter)
    except ImportError:
        raise ImportError(
            "odfpy is required for ODT export. Install it with: pip install odfpy"
        )

    print("Discovering chapters...")

    book_yaml_path = os.path.join(project_root, 'book.yaml')
    if not os.path.exists(book_yaml_path):
        raise FileNotFoundError("book.yaml not found")

    with open(book_yaml_path, 'r') as f:
        book_config = yaml.safe_load(f)

    book_config['flags'] = flags or []
    metadata = normalize_metadata(book_config.get('metadata', {}))

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

    image_extensions = discovery_config.get('image_extensions', ['.jpg', '.jpeg', '.png', '.gif', '.svg'])
    images_map = get_all_files_with_paths(project_root, image_extensions, exclude_dirs)

    # Assemble the document
    doc = OpenDocumentText()
    style_names = _make_styles(doc, text, style)

    # Set document title metadata
    title = metadata.get('dc:title')
    if title:
        from odf.dc import Title, Creator
        doc.meta.addElement(Title(text=str(title)))
        if metadata.get('dc:creator'):
            doc.meta.addElement(Creator(text=str(metadata['dc:creator'])))

    if not no_cover:
        _add_cover(doc, text, metadata, project_root)

    if not no_toc:
        _add_toc(doc, text)

    print("Processing chapters...")

    for i, chapter in enumerate(chapters):
        rendered_md = render_chapter(chapter['path'], project_root, book_config)
        md = markdown.Markdown(extensions=[
            'meta', 'codehilite', 'tables', 'fenced_code', 'footnotes', 'md_in_html',
        ])
        html_body = md.convert(rendered_md)

        # Start each chapter (and the cover/TOC follow-on) on a fresh page
        if i > 0 or not no_cover or not no_toc:
            doc.text.addElement(text.P(stylename=style_names['pagebreak']))

        converter = _HTMLToODF(doc, doc.text, style_names, images_map)
        converter.feed(html_body)
        converter.close()
        print(f"  Chapter {i + 1}: {get_chapter_title(chapter)}")

    doc.save(output_path)

    size_bytes = os.path.getsize(output_path)
    size_kb = size_bytes / 1024
    print(f"  Generated {output_path} ({size_kb:.1f} KB)")
