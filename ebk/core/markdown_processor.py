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


def should_exclude_path(path, exclude_patterns, search_root):
    """
    Check if path should be excluded based on exclusion patterns.

    Args:
        path: Full path to check
        exclude_patterns: List of directory names to exclude
        search_root: Root directory being searched

    Returns:
        bool: True if path should be excluded
    """
    if not exclude_patterns:
        return False

    # Get relative path components
    try:
        rel_path = os.path.relpath(path, search_root)
    except ValueError:
        # On Windows, relpath can fail if paths are on different drives
        return False

    # Check if any part of the path matches exclusion patterns.
    # A pattern like "resources" also matches ".resources" (dot-prefixed hidden dirs).
    path_parts = rel_path.split(os.sep)
    for part in path_parts:
        if part in exclude_patterns:
            return True
        # Also match hidden directories: ".resources" matches pattern "resources"
        if part.startswith('.') and part[1:] in exclude_patterns:
            return True

    return False


def discover_files_by_extension(project_root, extensions, exclude_dirs=None):
    """
    Recursively discover files with specified extensions from project root.

    Args:
        project_root: Root directory to search from
        extensions: List of file extensions (e.g., ['.md', '.markdown'])
        exclude_dirs: List of directory names to exclude (e.g., ['.git', 'venv'])

    Returns:
        list: Full paths to discovered files, sorted
    """
    if exclude_dirs is None:
        exclude_dirs = ['.git', '.venv', 'venv', 'node_modules', '__pycache__',
                       '.ebk', 'build', 'dist']

    if not os.path.exists(project_root):
        return []

    discovered_files = []

    def scan_directory(path, depth=0):
        """Recursively scan directory for files with specified extensions."""
        # Check if this directory should be excluded
        if should_exclude_path(path, exclude_dirs, project_root):
            return

        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return

        for item in items:
            full_path = os.path.join(path, item)

            # Skip excluded paths
            if should_exclude_path(full_path, exclude_dirs, project_root):
                continue

            if os.path.isfile(full_path):
                # Check if file has one of the desired extensions (case-insensitive)
                if any(full_path.lower().endswith(ext.lower()) for ext in extensions):
                    discovered_files.append(full_path)
            elif os.path.isdir(full_path):
                # Recurse into subdirectory
                scan_directory(full_path, depth + 1)

    scan_directory(project_root)
    return sorted(discovered_files)


def discover_chapters(content_dir, exclude_dirs=None):
    """
    Recursively discover markdown files in content/ directory.

    Args:
        content_dir: Directory to search (can be project root)
        exclude_dirs: List of directory names to exclude

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
        # Check if this directory should be excluded
        if exclude_dirs and should_exclude_path(path, exclude_dirs, content_dir):
            return

        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return

        for item in items:
            full_path = os.path.join(path, item)

            # Skip excluded paths
            if exclude_dirs and should_exclude_path(full_path, exclude_dirs, content_dir):
                continue

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


def get_chapters(content_dir, exclude_dirs=None):
    """
    Discover and order chapters from content directory.

    Args:
        content_dir: Directory to search (can be project root)
        exclude_dirs: List of directory names to exclude

    Returns:
        list: Ordered list of chapter dictionaries
    """
    chapters = discover_chapters(content_dir, exclude_dirs)
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
