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


def is_ebk_project():
    """Check if current directory is an ebk project."""
    return os.path.exists('.ebk') and os.path.exists('book.yaml')


def build_current_project(pdf=False, html=False, font_size=11, landscape=False, flags=None):
    """Build EPUB, PDF, or HTML from current directory."""
    if flags is None:
        flags = []

    if not is_ebk_project():
        print("Error: Not an ebk project directory.", file=sys.stderr)
        print("Run 'ebk <name>' to create a new project.", file=sys.stderr)
        sys.exit(1)

    try:
        import yaml
        with open('book.yaml', 'r') as f:
            config = yaml.safe_load(f)

        if pdf:
            output_filename = config.get('output', {}).get('pdf_filename')
            if not output_filename:
                output_filename = os.path.basename(os.getcwd()) + '.pdf'
            print(f"Building PDF from current directory...")
            build_pdf(os.getcwd(), output_filename, font_size=font_size, landscape=landscape, flags=flags)
            print(f"✓ Created {output_filename}")
        elif html:
            output_dir = config.get('output', {}).get('html_dir', 'html')
            print(f"Building HTML from current directory...")
            build_html(os.getcwd(), output_dir, flags=flags)
            print(f"✓ Created {output_dir}/")
        else:
            output_filename = config.get('output', {}).get('filename')
            if not output_filename:
                output_filename = os.path.basename(os.getcwd()) + '.epub'
            print(f"Building EPUB from current directory...")
            build_epub(os.getcwd(), output_filename, flags=flags)
            print(f"✓ Created {output_filename}")

    except Exception as e:
        print(f"Error building {'PDF' if pdf else 'HTML' if html else 'EPUB'}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='ebk',
        description='ebk - E-Book CLI utility for managing EPUB projects',
        epilog='Run "ebk <name>" to create a new book project, or "ebk" in a project directory to build the EPUB.'
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
        help='Export to PDF instead of EPUB'
    )

    parser.add_argument(
        '--html',
        action='store_true',
        help='Export to HTML directory instead of EPUB'
    )

    parser.add_argument(
        '--font-size',
        type=int,
        default=11,
        metavar='PT',
        help='PDF font size in pt (default: 11)'
    )

    parser.add_argument(
        '--landscape',
        action='store_true',
        help='Export PDF in landscape orientation'
    )

    parser.add_argument(
        '--flag', '-f',
        action='append',
        dest='flags',
        default=[],
        metavar='FLAG',
        help='Enable a feature flag for conditional rendering (repeatable, e.g. -f present)'
    )

    args = parser.parse_args()

    if args.name:
        # Create new book project
        try:
            create_new_book(args.name)
        except Exception as e:
            print(f"Error creating project: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Build current project
        build_current_project(
            pdf=args.pdf,
            html=args.html,
            font_size=args.font_size,
            landscape=args.landscape,
            flags=args.flags,
        )


if __name__ == "__main__":
    main()
