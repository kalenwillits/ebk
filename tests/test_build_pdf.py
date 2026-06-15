"""Integration tests for build_pdf options."""

import pytest
from ebk.core.pdf_builder import build_pdf

pytest.importorskip("weasyprint", reason="weasyprint not installed")


@pytest.fixture
def simple_project(tmp_path):
    (tmp_path / '.ebk').write_text('')
    (tmp_path / 'book.yaml').write_text(
        'metadata:\n'
        '  title: Test Book\n'
        '  author: Test Author\n'
        '  language: en-US\n'
        '  identifier: test-123\n'
        'output:\n'
        '  pdf_filename: test.pdf\n'
    )
    (tmp_path / '01-intro.md').write_text('# Introduction\n\nHello world.')
    return tmp_path


def test_pdf_created(simple_project, tmp_path):
    out = tmp_path / 'out.pdf'
    build_pdf(str(simple_project), str(out))
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_default_has_cover(simple_project, tmp_path):
    """Default build includes cover div."""
    # We inspect the intermediate HTML by monkey-patching weasyprint
    captured = {}
    import ebk.core.pdf_builder as mod
    from weasyprint import HTML as RealHTML

    original = RealHTML

    class CapturingHTML:
        def __init__(self, string=None, base_url=None):
            captured['html'] = string
        def write_pdf(self, path):
            # Write a minimal valid PDF so the file exists
            import pathlib
            pathlib.Path(path).write_bytes(b'%PDF-1.4 fake')

    mod_html = mod.__dict__.get('HTML')
    try:
        import weasyprint
        weasyprint.HTML = CapturingHTML
        out = tmp_path / 'out.pdf'
        build_pdf(str(simple_project), str(out))
        assert 'id="cover"' in captured['html']
        assert 'id="toc"' in captured['html']
    finally:
        weasyprint.HTML = RealHTML


def test_pdf_no_cover(simple_project, tmp_path):
    import weasyprint
    from weasyprint import HTML as RealHTML
    captured = {}

    class CapturingHTML:
        def __init__(self, string=None, base_url=None):
            captured['html'] = string
        def write_pdf(self, path):
            import pathlib
            pathlib.Path(path).write_bytes(b'%PDF-1.4 fake')

    try:
        weasyprint.HTML = CapturingHTML
        out = tmp_path / 'out.pdf'
        build_pdf(str(simple_project), str(out), no_cover=True)
        assert 'id="cover"' not in captured['html']
        assert 'id="toc"' in captured['html']
    finally:
        weasyprint.HTML = RealHTML


def test_pdf_no_toc(simple_project, tmp_path):
    import weasyprint
    from weasyprint import HTML as RealHTML
    captured = {}

    class CapturingHTML:
        def __init__(self, string=None, base_url=None):
            captured['html'] = string
        def write_pdf(self, path):
            import pathlib
            pathlib.Path(path).write_bytes(b'%PDF-1.4 fake')

    try:
        weasyprint.HTML = CapturingHTML
        out = tmp_path / 'out.pdf'
        build_pdf(str(simple_project), str(out), no_toc=True)
        assert 'id="toc"' not in captured['html']
        assert 'id="cover"' in captured['html']
    finally:
        weasyprint.HTML = RealHTML


def test_pdf_no_cover_no_toc(simple_project, tmp_path):
    import weasyprint
    from weasyprint import HTML as RealHTML
    captured = {}

    class CapturingHTML:
        def __init__(self, string=None, base_url=None):
            captured['html'] = string
        def write_pdf(self, path):
            import pathlib
            pathlib.Path(path).write_bytes(b'%PDF-1.4 fake')

    try:
        weasyprint.HTML = CapturingHTML
        out = tmp_path / 'out.pdf'
        build_pdf(str(simple_project), str(out), no_cover=True, no_toc=True)
        assert 'id="cover"' not in captured['html']
        assert 'id="toc"' not in captured['html']
    finally:
        weasyprint.HTML = RealHTML


def _capture_css(simple_project, tmp_path, **build_kwargs):
    """Run build_pdf capturing the generated HTML/CSS string.

    Handles both write_pdf signatures: write_pdf(path) for normal builds and
    write_pdf() -> bytes for booklet mode (which then imposes via pypdf).
    """
    import weasyprint
    from weasyprint import HTML as RealHTML
    captured = {}
    real_bytes = RealHTML(string='<html><body>x</body></html>').write_pdf()

    class CapturingHTML:
        def __init__(self, string=None, base_url=None):
            captured['html'] = string

        def write_pdf(self, path=None):
            if path is None:
                return real_bytes  # booklet path expects raw bytes back
            import pathlib
            pathlib.Path(path).write_bytes(b'%PDF-1.4 fake')

    try:
        weasyprint.HTML = CapturingHTML
        build_pdf(str(simple_project), str(tmp_path / 'out.pdf'), **build_kwargs)
    finally:
        weasyprint.HTML = RealHTML
    return captured['html']


def test_pdf_default_margin(simple_project, tmp_path):
    css = _capture_css(simple_project, tmp_path)
    assert 'margin: 2.0cm' in css          # exact total margin on @page
    assert 'line-height: 1.6; margin: 0' in css  # body margin zeroed (no doubling)


def test_pdf_custom_margin(simple_project, tmp_path):
    css = _capture_css(simple_project, tmp_path, margin=3)
    assert 'margin: 3.0cm' in css


def test_pdf_booklet_default_margin(simple_project, tmp_path):
    css = _capture_css(simple_project, tmp_path, booklet=True)
    assert 'margin: 0.5cm' in css          # booklet maximizes content area


def test_pdf_booklet_margin_override(simple_project, tmp_path):
    css = _capture_css(simple_project, tmp_path, booklet=True, margin=1.5)
    assert 'margin: 1.5cm' in css
