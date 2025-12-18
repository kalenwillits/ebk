#!/usr/bin/env python3
"""CLI router for ebk commands."""

import argparse
import os
import sys
from ebk import __version__
from ebk.core.project_structure import create_new_book
from ebk.core.epub_builder import build_epub


def is_ebk_project():
    """Check if current directory is an ebk project."""
    return os.path.exists('.ebk') and os.path.exists('book.yaml')


def build_current_project():
    """Build EPUB from current directory."""
    if not is_ebk_project():
        print("Error: Not an ebk project directory.", file=sys.stderr)
        print("Run 'ebk <name>' to create a new project.", file=sys.stderr)
        sys.exit(1)

    try:
        # Get output filename from book.yaml or use default
        import yaml
        with open('book.yaml', 'r') as f:
            config = yaml.safe_load(f)

        output_filename = config.get('output', {}).get('filename')
        if not output_filename:
            # Default to directory name + .epub
            output_filename = os.path.basename(os.getcwd()) + '.epub'

        print(f"Building EPUB from current directory...")
        build_epub(os.getcwd(), output_filename)
        print(f"✓ Created {output_filename}")

    except Exception as e:
        print(f"Error building EPUB: {e}", file=sys.stderr)
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
        build_current_project()


if __name__ == "__main__":
    main()
