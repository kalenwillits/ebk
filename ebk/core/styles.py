"""Centralized CSS discovery, layering, and rendering shared by the EPUB,
HTML, and PDF builders.

A "layer" is one named stylesheet (ebk's shipped default.css, compiled
Tailwind output, or a project's own CSS file). Layers are returned in cascade
order: earlier layers are meant to be overridden by later ones, either via
linked <link> tags (EPUB/HTML) or by text concatenation into one inline
<style> block (PDF).
"""

import os
from dataclasses import dataclass
from pathlib import Path

from ebk.core.markdown_processor import discover_files_by_extension


def get_all_filenames(dir_path, extensions):
    """
    Get all files with specified extensions in directory (legacy function).

    NOTE: This function is kept for backward compatibility but only searches
    a single directory non-recursively. New code should use
    get_all_files_with_paths() or get_all_filenames_recursive().
    """
    if not os.path.exists(dir_path):
        return []

    files = []
    for item in os.listdir(dir_path):
        full_path = os.path.join(dir_path, item)
        if os.path.isfile(full_path):
            if any(item.lower().endswith(ext) for ext in extensions):
                files.append(item)
    return sorted(files)


def get_all_files_with_paths(project_root, extensions, exclude_dirs=None):
    """
    Get all files with full paths for reading during a build.

    Args:
        project_root: Root directory to search recursively
        extensions: List of file extensions to match (e.g., ['.css', '.jpg'])
        exclude_dirs: List of directory names to exclude

    Returns:
        dict: Mapping of filename -> full path

    Note: If duplicate filenames exist in different directories,
    the last one in sorted order wins.
    """
    full_paths = discover_files_by_extension(project_root, extensions, exclude_dirs)

    # Create mapping: filename -> full path
    # If duplicate filenames exist, last one wins (sorted order)
    file_map = {}
    duplicates = set()

    for path in sorted(full_paths):
        filename = os.path.basename(path)
        if filename in file_map:
            duplicates.add(filename)
        file_map[filename] = path

    # Warn about duplicates
    if duplicates:
        print(f"  Warning: Found duplicate filenames (using last in sorted order):")
        for dup in sorted(duplicates):
            print(f"    - {dup}")

    return file_map


def get_all_filenames_recursive(project_root, extensions, exclude_dirs=None):
    """
    Get all files with specified extensions recursively from project root.

    Args:
        project_root: Root directory to search
        extensions: List of file extensions to match
        exclude_dirs: List of directory names to exclude

    Returns:
        list: Filenames only (without paths) sorted alphabetically
    """
    file_map = get_all_files_with_paths(project_root, extensions, exclude_dirs)
    return sorted(file_map.keys())


@dataclass
class CssLayer:
    """One named stylesheet layer.

    name: filename used when written standalone (EPUB/HTML), e.g. "default.css"
    text: raw CSS content
    source: 'default' | 'tailwind' | 'project' -- diagnostics only
    """
    name: str
    text: str
    source: str = 'project'


def default_css_enabled(config):
    """Whether ebk's shipped default.css base layer should be applied.

    Controlled by an optional `styles.include_default` key in config.yaml;
    defaults to True (the base layer is applied unless explicitly disabled).
    """
    if not isinstance(config, dict):
        return True
    styles_config = config.get('styles') or {}
    return bool(styles_config.get('include_default', True))


def load_default_css():
    """Read ebk's shipped resources/default.css as a CssLayer."""
    default_css_path = Path(__file__).parent.parent / 'resources' / 'default.css'
    text = default_css_path.read_text(encoding='utf-8')
    return CssLayer(name='default.css', text=text, source='default')


def copy_default_fonts(dest_dir):
    """Copy ebk's shipped fonts (referenced by default.css's @font-face
    rules via a relative '../fonts/...' URL) into dest_dir. No-op if the
    resources/fonts directory doesn't exist."""
    fonts_dir = Path(__file__).parent.parent / 'resources' / 'fonts'
    if not fonts_dir.exists():
        return
    os.makedirs(dest_dir, exist_ok=True)
    for font_file in fonts_dir.glob('*'):
        if font_file.suffix.lower() in ('.ttf', '.otf', '.woff', '.woff2'):
            with open(font_file, 'rb') as src:
                data = src.read()
            with open(os.path.join(dest_dir, font_file.name), 'wb') as dst:
                dst.write(data)


def resolve_css_layers(project_root, config, exclude_dirs=None, css_extensions=None,
                        include_default=True, tailwind_css=None):
    """
    Build the ordered list of CSS layers for a build, in cascade order:
      1. ebk's default.css (base) -- unless include_default=False, or
         config.yaml sets styles.include_default: false
      2. compiled Tailwind CSS, if `tailwind_css` (a pre-compiled CssLayer)
         is given -- this function does not invoke Tailwind itself
      3. project CSS: every CSS file discovered recursively under
         project_root, plus any config.yaml `default_css:` entries not
         already found (resolved via a legacy `assets/css/<name>` fallback),
         with a warning printed for an entry that still can't be found

    Later layers override earlier ones for same-specificity selectors.
    """
    exclude_dirs = exclude_dirs or []
    css_extensions = css_extensions or ['.css']
    config = config or {}

    layers = []

    if include_default and default_css_enabled(config):
        layers.append(load_default_css())

    if tailwind_css is not None:
        layers.append(tailwind_css)

    css_files_map = get_all_files_with_paths(project_root, css_extensions, exclude_dirs)
    css_names = list(css_files_map.keys())

    for css in config.get('default_css', []) or []:
        if css not in css_names:
            if css in css_files_map:
                css_names.append(css)
            else:
                legacy_path = os.path.join(project_root, 'assets', 'css', css)
                if os.path.exists(legacy_path):
                    css_names.append(css)
                    css_files_map[css] = legacy_path
                else:
                    print(f"  Warning: CSS file '{css}' not found")

    for name in css_names:
        path = css_files_map.get(name)
        if path and os.path.exists(path):
            with open(path, 'r') as f:
                layers.append(CssLayer(name=name, text=f.read(), source='project'))
        else:
            print(f"  Warning: CSS file '{name}' not found, skipping")

    return layers


def render_css_links(css_names, href_prefix='css/', xhtml=False):
    """Build the '<link rel="stylesheet" ...>' block for the given ordered
    list of CSS filenames -- self-closing XHTML tags if xhtml=True, plain
    HTML5 tags otherwise."""
    if xhtml:
        return '\n'.join(
            f'  <link rel="stylesheet" type="text/css" href="{href_prefix}{name}" />'
            for name in css_names
        )
    return '\n'.join(
        f'  <link rel="stylesheet" href="{href_prefix}{name}">'
        for name in css_names
    )


def render_inline_style_block(layers):
    """Concatenate layer text in order, each preceded by a CSS comment
    marker, for PDF's inline <style> block."""
    parts = []
    for layer in layers:
        parts.append(f'/* --- {layer.name} ({layer.source}) --- */')
        parts.append(layer.text)
    return '\n'.join(parts)


def write_css_layers_epub(epub_zipfile, layers, zip_prefix='OPS/css/'):
    """Write each layer as {zip_prefix}{layer.name} into an open zipfile."""
    for layer in layers:
        epub_zipfile.writestr(f'{zip_prefix}{layer.name}', layer.text)


def write_css_layers_dir(layers, css_out_dir):
    """Write each layer as css_out_dir/{layer.name}."""
    os.makedirs(css_out_dir, exist_ok=True)
    for layer in layers:
        with open(os.path.join(css_out_dir, layer.name), 'w', encoding='utf-8') as f:
            f.write(layer.text)
