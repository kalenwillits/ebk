"""Saddle-stitch booklet imposition for PDFs.

Takes a sequential, half-sheet-sized PDF (one book page per PDF page) and
rearranges it into print-ready landscape sheets with two pages side by side, in
the page order required for folding. Optionally splits the book into fixed-size
signatures so each folded bundle stays manageable.

Pure Python via ``pypdf`` so it works inside the frozen PyInstaller binary with
no external tools.
"""

import io
import math


# Landscape sheet dimensions in PostScript points (1pt = 1/72in).
# Each sheet holds two portrait half-pages side by side.
_SHEET_SIZES = {
    'letter': (792.0, 612.0),   # 11in x 8.5in landscape
    'a4': (841.89, 595.28),     # A4 landscape
}


def _round_up_4(n):
    """Smallest multiple of 4 >= n (a folded sheet is always 4 pages)."""
    return ((n + 3) // 4) * 4


def _signature_order(p):
    """Page indices (0-based) for one signature of ``p`` pages, in print order.

    ``p`` must be a multiple of 4. Returns a flat list of source-page indices,
    two per output sheet-side, ordered so that printing duplex (flip on short
    edge) and folding the stack yields pages in reading order. ``None`` marks a
    blank (padding) slot.

    For sheet ``i`` (0-based), using 1-based page numbers:
        outer side: (p - 2i,     1 + 2i)
        inner side: (2 + 2i,     p - 1 - 2i)
    Sides are interleaved outer/inner per sheet for correct duplexing.
    """
    order = []
    for i in range(p // 4):
        # 1-based page numbers, converted to 0-based indices
        order.extend([p - 2 * i - 1, 1 + 2 * i - 1])      # outer side
        order.extend([2 + 2 * i - 1, p - 1 - 2 * i - 1])  # inner side
    return order


def _signatures(total, sig):
    """Split ``total`` source pages into signatures of ``sig`` pages each.

    Returns a list of (start, length) chunks. Every chunk length is padded up to
    a multiple of 4; the source only fills the first ``min(remaining, sig)``
    slots of each, the rest are blanks.
    """
    chunks = []
    start = 0
    while start < total:
        length = min(sig, total - start)
        chunks.append((start, length))
        start += sig
    return chunks


def impose_booklet(pdf_bytes, output_path, sheet='letter', split=None):
    """Impose a sequential half-page PDF into booklet sheets.

    Args:
        pdf_bytes: Bytes of the source PDF (one book page per PDF page, sized to
            half a sheet so two fit side by side).
        output_path: Path to write the imposed PDF.
        sheet: 'letter' or 'a4' — the physical sheet the booklet prints on.
        split: Optional signature size (pages per folded bundle). Must be a
            multiple of 4. When None, the whole book is one signature.

    Raises:
        ImportError: If pypdf is not installed.
        ValueError: If sheet is unknown or split is not a positive multiple of 4.
    """
    try:
        from pypdf import PdfReader, PdfWriter, PageObject, Transformation
    except ImportError:
        raise ImportError(
            "pypdf is required for booklet imposition. Install it with: pip install pypdf"
        )

    if sheet not in _SHEET_SIZES:
        raise ValueError(f"Unknown sheet size '{sheet}' (expected one of {list(_SHEET_SIZES)})")
    if split is not None and (split <= 0 or split % 4 != 0):
        raise ValueError("Signature size (--split) must be a positive multiple of 4")

    sheet_w, sheet_h = _SHEET_SIZES[sheet]
    half_w = sheet_w / 2.0

    reader = PdfReader(io.BytesIO(pdf_bytes))
    src_pages = reader.pages
    total = len(src_pages)
    if total == 0:
        raise ValueError("Source PDF has no pages")

    sig = split if split else _round_up_4(total)

    writer = PdfWriter()

    for start, length in _signatures(total, sig):
        p = _round_up_4(length)
        for left_slot, right_slot in _pairs(_signature_order(p)):
            dest = PageObject.create_blank_page(width=sheet_w, height=sheet_h)
            _place(dest, src_pages, start, length, left_slot, 0.0, half_w, sheet_h, PageObject, Transformation)
            _place(dest, src_pages, start, length, right_slot, half_w, half_w, sheet_h, PageObject, Transformation)
            writer.add_page(dest)

    with open(output_path, 'wb') as f:
        writer.write(f)

    return writer.get_num_pages() if hasattr(writer, 'get_num_pages') else len(writer.pages)


def _pairs(flat):
    """Yield (a, b) two-at-a-time from a flat list."""
    for i in range(0, len(flat), 2):
        yield flat[i], flat[i + 1]


def _place(dest, src_pages, start, length, slot, x_offset, half_w, sheet_h, PageObject, Transformation):
    """Merge one source page (or nothing, for blanks) onto half of ``dest``."""
    if slot is None or slot >= length:
        return  # padding / blank slot
    src = src_pages[start + slot]
    # Scale the half-page to fit its half of the sheet exactly, then translate.
    src_w = float(src.mediabox.width)
    src_h = float(src.mediabox.height)
    sx = half_w / src_w if src_w else 1.0
    sy = sheet_h / src_h if src_h else 1.0
    scale = min(sx, sy)
    # Center within the half horizontally if scaled smaller than the half width.
    tx = x_offset + (half_w - src_w * scale) / 2.0
    ty = (sheet_h - src_h * scale) / 2.0
    transform = Transformation().scale(scale, scale).translate(tx, ty)
    dest.merge_transformed_page(src, transform)
