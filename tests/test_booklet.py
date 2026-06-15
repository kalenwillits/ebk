"""Unit tests for booklet imposition."""

import pytest
from pypdf import PdfReader
from weasyprint import HTML

from ebk.core.booklet import (
    impose_booklet, _round_up_4, _signature_order, _signatures,
)


def _make_pdf(n, size='5.5in 8.5in'):
    """Render an n-page half-letter PDF, one labeled page per sheet."""
    pages = ''.join(
        f'<div style="page-break-after:always"><h1>Page {i}</h1></div>'
        for i in range(1, n + 1)
    )
    html = f'<html><head><style>@page{{size:{size};}}</style></head><body>{pages}</body></html>'
    return HTML(string=html).write_pdf()


# -- pure helpers ---------------------------------------------------------

def test_round_up_4():
    assert _round_up_4(0) == 0
    assert _round_up_4(1) == 4
    assert _round_up_4(4) == 4
    assert _round_up_4(6) == 8
    assert _round_up_4(32) == 32


def test_signature_order_8():
    # Canonical 8-page booklet imposition (0-based indices)
    assert _signature_order(8) == [7, 0, 1, 6, 5, 2, 3, 4]


def test_signature_order_4():
    assert _signature_order(4) == [3, 0, 1, 2]


def test_signatures_split():
    assert _signatures(8, 4) == [(0, 4), (4, 4)]
    assert _signatures(10, 4) == [(0, 4), (4, 4), (8, 2)]
    assert _signatures(6, 8) == [(0, 6)]


# -- imposition -----------------------------------------------------------

def test_impose_whole_book(tmp_path):
    pdf = _make_pdf(8)
    out = tmp_path / 'bk.pdf'
    n = impose_booklet(pdf, str(out), sheet='letter')
    assert n == 4  # 8 pages -> 4 landscape sheet-sides
    r = PdfReader(str(out))
    assert len(r.pages) == 4
    mb = r.pages[0].mediabox
    assert round(float(mb.width)) == 792 and round(float(mb.height)) == 612


def test_impose_pads_to_multiple_of_4(tmp_path):
    pdf = _make_pdf(6)  # padded to 8
    out = tmp_path / 'bk.pdf'
    n = impose_booklet(pdf, str(out), sheet='letter')
    assert n == 4


def test_impose_split_signatures(tmp_path):
    pdf = _make_pdf(8)
    out = tmp_path / 'bk.pdf'
    # Two 4-page signatures -> 2 sheet-sides each -> 4 total
    n = impose_booklet(pdf, str(out), sheet='letter', split=4)
    assert n == 4


def test_impose_a4_sheet_size(tmp_path):
    pdf = _make_pdf(4, size='A5')
    out = tmp_path / 'bk.pdf'
    impose_booklet(pdf, str(out), sheet='a4')
    mb = PdfReader(str(out)).pages[0].mediabox
    assert round(float(mb.width)) == 842 and round(float(mb.height)) == 595


def test_impose_rejects_bad_split(tmp_path):
    pdf = _make_pdf(4)
    with pytest.raises(ValueError):
        impose_booklet(pdf, str(tmp_path / 'x.pdf'), split=6)


def test_impose_rejects_unknown_sheet(tmp_path):
    pdf = _make_pdf(4)
    with pytest.raises(ValueError):
        impose_booklet(pdf, str(tmp_path / 'x.pdf'), sheet='foolscap')
