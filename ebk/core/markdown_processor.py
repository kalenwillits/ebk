"""Markdown processing: chapter discovery, ordering, and frontmatter parsing."""

import os
import re
from pathlib import Path
import markdown


def extract_numeric_prefix(filename):
    """Extract numeric prefix from filename (e.g., '01-intro.md' -> 1)."""
    match = re.match(r'^(\d+)-', filename)
    if match:
        return int(match.group(1))
    return None


def parse_frontmatter(md_content):
    """
    Extract YAML frontmatter from markdown content.

    Returns:
        tuple: (content_without_frontmatter, metadata_dict)
    """
    md = markdown.Markdown(extensions=['meta'])
    html = md.convert(md_content)

    # Get metadata from the meta extension
    metadata = {}
    if hasattr(md, 'Meta'):
        # Meta extension stores values as lists, get first item
        for key, value in md.Meta.items():
            if isinstance(value, list) and len(value) > 0:
                metadata[key] = value[0]
            else:
                metadata[key] = value

    return md_content, metadata


def discover_chapters(content_dir):
    """
    Recursively discover markdown files in content/ directory.

    Returns:
        list: Ordered list of chapter dictionaries with keys:
            - path: Full path to markdown file
            - relative_path: Path relative to content_dir
            - depth: Nesting depth (0 for root level)
            - name: Filename
            - is_intro: True if this is a _chapter.md file
            - order: Numeric order (from frontmatter, prefix, or None)
            - metadata: Frontmatter metadata
    """
    if not os.path.exists(content_dir):
        return []

    chapters = []

    def scan_directory(path, depth=0):
        """Recursively scan directory for markdown files."""
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return

        for item in items:
            full_path = os.path.join(path, item)

            if os.path.isfile(full_path) and item.endswith('.md'):
                # Read file to get frontmatter
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    _, metadata = parse_frontmatter(content)
                except Exception as e:
                    print(f"Warning: Could not read {full_path}: {e}")
                    metadata = {}

                # Determine order from frontmatter or numeric prefix
                order = None
                if 'order' in metadata:
                    try:
                        order = int(metadata['order'])
                    except (ValueError, TypeError):
                        pass

                if order is None:
                    numeric_prefix = extract_numeric_prefix(item)
                    if numeric_prefix is not None:
                        order = numeric_prefix

                # Get relative path
                relative_path = os.path.relpath(full_path, content_dir)

                chapters.append({
                    'path': full_path,
                    'relative_path': relative_path,
                    'depth': depth,
                    'name': item,
                    'is_intro': item == '_chapter.md',
                    'order': order,
                    'metadata': metadata,
                })

            elif os.path.isdir(full_path):
                # Check for _chapter.md intro file first
                chapter_intro = os.path.join(full_path, '_chapter.md')
                if os.path.exists(chapter_intro):
                    try:
                        with open(chapter_intro, 'r', encoding='utf-8') as f:
                            content = f.read()
                        _, metadata = parse_frontmatter(content)
                    except Exception as e:
                        print(f"Warning: Could not read {chapter_intro}: {e}")
                        metadata = {}

                    # Determine order for intro file
                    order = None
                    if 'order' in metadata:
                        try:
                            order = int(metadata['order'])
                        except (ValueError, TypeError):
                            pass

                    if order is None:
                        numeric_prefix = extract_numeric_prefix(item)
                        if numeric_prefix is not None:
                            order = numeric_prefix

                    relative_path = os.path.relpath(chapter_intro, content_dir)

                    chapters.append({
                        'path': chapter_intro,
                        'relative_path': relative_path,
                        'depth': depth + 1,
                        'name': '_chapter.md',
                        'is_intro': True,
                        'order': order,
                        'metadata': metadata,
                    })

                # Recurse into subdirectory
                scan_directory(full_path, depth + 1)

    scan_directory(content_dir)
    return chapters


def order_chapters(chapters):
    """
    Sort chapters by order field, then by path.

    Sorting strategy:
    1. Primary: order field (if present)
    2. Secondary: depth (to keep hierarchy)
    3. Tertiary: path (alphabetical)
    """
    def sort_key(chapter):
        # Get order (use large number if None to sort to end)
        order = chapter.get('order')
        if order is None:
            order = 999999

        # Get directory path and filename separately for better sorting
        path_parts = chapter['relative_path'].split(os.sep)

        return (order, chapter['depth'], path_parts)

    return sorted(chapters, key=sort_key)


def get_chapters(content_dir):
    """
    Discover and order chapters from content directory.

    Returns:
        list: Ordered list of chapter dictionaries
    """
    chapters = discover_chapters(content_dir)
    return order_chapters(chapters)


def get_chapter_title(chapter):
    """
    Extract chapter title from metadata or first heading.

    Args:
        chapter: Chapter dictionary with 'path' and 'metadata' keys

    Returns:
        str: Chapter title or filename as fallback
    """
    # Try to get title from metadata
    if 'title' in chapter['metadata']:
        return chapter['metadata']['title']

    # Try to read first heading from file
    try:
        with open(chapter['path'], 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
    except:
        pass

    # Fallback to filename without extension
    name = chapter['name']
    if name.endswith('.md'):
        name = name[:-3]

    # Remove numeric prefix
    name = re.sub(r'^\d+-', '', name)

    # Replace hyphens/underscores with spaces and title case
    name = name.replace('-', ' ').replace('_', ' ')
    return name.title()
