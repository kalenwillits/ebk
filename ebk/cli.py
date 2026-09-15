#!/usr/bin/env python3
"""CLI router for ebk commands."""

import argparse
import os
import sys
from ebk import __version__
from ebk.core.project_structure import create_new_book
from ebk.core.epub_builder import build_epub
from ebk.core.pdf_builder import build_pdf
from ebk.core.html_builder import build_html
from ebk.core.odt_builder import build_odt
from ebk.core.linter import run_lint


def is_ebk_project():
    """Check if current directory is an ebk project."""
    return os.path.exists('.ebk') and os.path.exists('config.yaml')


def _resolve_output(output, default_filename, ext):
    """
    Resolve the final output file path from --output and the default filename.

    - No --output:           use default_filename in cwd
    - --output path/to/file.ext: use as full path (supports renaming)
    - --output path/to/dir:  put default_filename inside that directory
    """
    if not output:
        return default_filename
    if output.lower().endswith(ext):
        # Treat as a full file path; create parent dirs if needed
        parent = os.path.dirname(output)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return output
    # Treat as directory
    os.makedirs(output, exist_ok=True)
    return os.path.join(output, os.path.basename(default_filename))


def check_current_project(flags=None, chapters=None):
    """Lint the current ebk project."""
    if flags is None:
        flags = []

    if not is_ebk_project():
        print("Error: Not an ebk project directory.", file=sys.stderr)
        print("Run 'ebk <name>' to create a new project.", file=sys.stderr)
        sys.exit(1)

    sys.exit(run_lint(os.getcwd(), flags=flags, chapters_filter=chapters))


VALID_FORMATS = ('pdf', 'epub', 'html', 'odt')


def build_current_project(pdf=False, html=False, odt=False, epub=False, font_size=11, landscape=False, flags=None, output=None, chapters=None, no_cover=False, no_toc=False, booklet=False, split=None, paper='letter', margin=None):
    """Build PDF, EPUB, HTML, or ODT from current directory.

    Format resolution: an explicit --pdf/--html/--odt/--epub flag always wins.
    Otherwise, config.yaml's output.format is used. If that key (or the whole
    output: block) is absent, the default format is PDF.
    """
    if flags is None:
        flags = []

    if not is_ebk_project():
        print("Error: Not an ebk project directory.", file=sys.stderr)
        print("Run 'ebk <name>' to create a new project.", file=sys.stderr)
        sys.exit(1)

    fmt = None
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f) or {}

        if pdf:
            fmt = 'pdf'
        elif html:
            fmt = 'html'
        elif odt:
            fmt = 'odt'
        elif epub:
            fmt = 'epub'
        else:
            fmt = config.get('output', {}).get('format', 'pdf')
            if fmt not in VALID_FORMATS:
                print(f"Error: invalid output.format '{fmt}' in config.yaml (must be one of {', '.join(VALID_FORMATS)})", file=sys.stderr)
                sys.exit(1)

        if fmt == 'pdf':
            default = config.get('output', {}).get('pdf_filename') or os.path.basename(os.getcwd()) + '.pdf'
            output_filename = _resolve_output(output, default, '.pdf')
            print(f"Building PDF from current directory...")
            build_pdf(os.getcwd(), output_filename, font_size=font_size, landscape=landscape, flags=flags, chapters=chapters, no_cover=no_cover, no_toc=no_toc, booklet=booklet, split=split, paper=paper, margin=margin)
            print(f"✓ Created {output_filename}")
        elif fmt == 'html':
            output_dir = output or config.get('output', {}).get('html_dir', 'html')
            print(f"Building HTML from current directory...")
            build_html(os.getcwd(), output_dir, flags=flags, chapters=chapters, no_toc=no_toc)
            print(f"✓ Created {output_dir}/")
        elif fmt == 'odt':
            default = config.get('output', {}).get('odt_filename') or os.path.basename(os.getcwd()) + '.odt'
            output_filename = _resolve_output(output, default, '.odt')
            print(f"Building ODT from current directory...")
            build_odt(os.getcwd(), output_filename, flags=flags, chapters=chapters, no_cover=no_cover, no_toc=no_toc)
            print(f"✓ Created {output_filename}")
        else:
            default = config.get('output', {}).get('filename') or os.path.basename(os.getcwd()) + '.epub'
            output_filename = _resolve_output(output, default, '.epub')
            print(f"Building EPUB from current directory...")
            build_epub(os.getcwd(), output_filename, flags=flags, chapters=chapters)
            print(f"✓ Created {output_filename}")

    except Exception as e:
        print(f"Error building {fmt.upper() if fmt else 'project'}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='ebk',
        description='ebk - CLI utility for building documents (PDF, EPUB, HTML, ODT) from plain text',
        epilog='Run "ebk <name>" to create a new project, or "ebk" in a project directory to build it (PDF by default, or per output.format in config.yaml).'
    )

    parser.add_argument(
        'name',
        nargs='?',
        help='Name of the new book to create'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'ebk {__version__}'
    )

    parser.add_argument(
        '--pdf',
        action='store_true',
        help="Export to PDF (default output format; overrides output.format in config.yaml)"
    )

    parser.add_argument(
        '--html',
        action='store_true',
        help='Export to HTML directory (overrides output.format in config.yaml)'
    )

    parser.add_argument(
        '--odt',
        action='store_true',
        help='Export to ODT (OpenDocument Text, for LibreOffice) (overrides output.format in config.yaml)'
    )

    parser.add_argument(
        '--epub',
        action='store_true',
        help='Export to EPUB (overrides output.format in config.yaml)'
    )

    parser.add_argument(
        '--font-size',
        type=int,
        default=None,
        metavar='PT',
        help='PDF body font size in pt (default: 11). Overrides any font-size set in the project CSS.'
    )

    parser.add_argument(
        '--landscape',
        action='store_true',
        help='Export PDF in landscape orientation'
    )

    parser.add_argument(
        '--booklet',
        action='store_true',
        help='Impose PDF pages 2-up for saddle-stitch booklet printing (duplex, flip on short edge)'
    )

    parser.add_argument(
        '--split',
        type=int,
        default=None,
        metavar='N',
        help='Booklet signature size: split the book into N-page folded bundles (N must be a multiple of 4; requires --booklet)'
    )

    parser.add_argument(
        '--paper',
        choices=['letter', 'a4'],
        default='letter',
        help='Sheet size for booklet imposition (default: letter)'
    )

    parser.add_argument(
        '--margin',
        type=float,
        default=None,
        metavar='CM',
        help='PDF page margin in cm on all edges (default: 2 normally, 0.5 in --booklet mode)'
    )

    parser.add_argument(
        '--flag', '-f',
        action='append',
        dest='flags',
        default=[],
        metavar='FLAG',
        help='Enable a feature flag for conditional rendering (repeatable, e.g. -f present)'
    )

    parser.add_argument(
        '--output', '-o',
        metavar='PATH',
        help='Output path: a directory (places file inside it) or a full filename to rename the output'
    )

    parser.add_argument(
        '--no-cover',
        action='store_true',
        help='Omit the title/author cover page from PDF output'
    )

    parser.add_argument(
        '--no-toc',
        action='store_true',
        help='Omit the table of contents from PDF and HTML output'
    )

    parser.add_argument(
        '--chapter', '-c',
        action='append',
        dest='chapters',
        default=[],
        metavar='CHAPTER',
        help='Include only this chapter (repeatable). Accepts a 1-based index or a filename substring. E.g. -c 2 or -c intro'
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Lint the project for errors: validates Jinja2 syntax, XHTML well-formedness, metadata, CSS, images, and Apple Books compatibility'
    )

    args = parser.parse_args()

    # Booklet option validation
    if args.split is not None and not args.booklet:
        parser.error("--split requires --booklet")
    if args.booklet and args.split is not None and args.split % 4 != 0:
        parser.error("--split N must be a multiple of 4 (each folded sheet holds 4 pages)")

    if args.name:
        # Create new book project
        try:
            create_new_book(args.name)
        except Exception as e:
            print(f"Error creating project: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.check:
        # Lint current project
        check_current_project(
            flags=args.flags,
            chapters=args.chapters,
        )
    else:
        # Build current project
        build_current_project(
            pdf=args.pdf,
            html=args.html,
            odt=args.odt,
            epub=args.epub,
            font_size=args.font_size,
            landscape=args.landscape,
            flags=args.flags,
            output=args.output,
            chapters=args.chapters,
            no_cover=args.no_cover,
            no_toc=args.no_toc,
            booklet=args.booklet,
            split=args.split,
            paper=args.paper,
            margin=args.margin,
        )


if __name__ == "__main__":
    main()
