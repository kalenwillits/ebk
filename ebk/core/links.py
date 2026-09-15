"""Cross-chapter link rewriting.

Chapters are authored to link to each other by *source* filename, e.g.
``[IX.C - Chandelles](../lesson-plans/047-ix-c-chandelles.md)``. At build time
those ``.md`` hrefs are rewritten to the target that resolves in the format
being produced. The chapter index ``i`` (from ``enumerate(chapters)``) is the
same across every builder, so it is a stable, format-independent handle.

Per-format targets:
    epub -> ``s{i:05d}.xhtml``   (one xhtml file per chapter in the spine)
    html -> ``s{i:05d}.html``    (one html file per chapter)
    pdf  -> ``#{i}``             (single doc; ``<section id="{i}">``)
    odt  -> ``#chapter-{i}``     (single doc; bookmark ``chapter-{i}``)
"""
import os
import re

# Matches: href="....md" or href="....md#frag" (single or double quotes).
_HREF_MD = re.compile(r'href=(["\'])([^"\']+?\.md)(#[^"\']*)?\1')


def build_source_index_map(chapters):
    """Map every chapter's source basename to its index.

    ``chapters`` is the finalized, ordered list each builder iterates with
    ``enumerate``; keys are ``os.path.basename(ch['path'])``.
    """
    return {
        os.path.basename(ch['path']): i
        for i, ch in enumerate(chapters)
    }


def _target(fmt, i, frag):
    if fmt == 'epub':
        base = f's{i:05d}.xhtml'
    elif fmt == 'html':
        base = f's{i:05d}.html'
    elif fmt == 'pdf':
        return f'#{i}'
    elif fmt == 'odt':
        return f'#chapter-{i}'
    else:
        raise ValueError(f"unknown link format: {fmt!r}")
    # file-per-chapter formats can carry a sub-fragment through
    return base + (frag or '')


def rewrite_cross_links(html, src_index_map, fmt):
    """Rewrite ``.md`` cross-chapter hrefs in ``html`` for the given ``fmt``.

    Unknown ``.md`` targets are left untouched and reported, so typos surface
    instead of silently producing dead links.
    """
    def repl(m):
        quote, path, frag = m.group(1), m.group(2), m.group(3)
        base = os.path.basename(path)
        if base not in src_index_map:
            print(f"  WARNING: cross-link target not found among chapters: {path}")
            return m.group(0)
        return f'href={quote}{_target(fmt, src_index_map[base], frag)}{quote}'

    return _HREF_MD.sub(repl, html)
