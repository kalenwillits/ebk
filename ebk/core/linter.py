"""Ebook linter — validates an ebk project for correctness and Apple Books compatibility."""

import os
import re
import sys
import yaml
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from jinja2 import Environment, BaseLoader, TemplateSyntaxError

from ebk.core.markdown_processor import (
    get_chapters,
    filter_chapters,
    get_chapter_title,
    discover_files_by_extension,
)
from ebk.core.template_engine import load_context, render_template
from ebk.core.epub_builder import get_all_files_with_paths, normalize_metadata

import markdown


# ---------------------------------------------------------------------------
# Diagnostic collection
# ---------------------------------------------------------------------------

class Diagnostic:
    """A single lint finding."""

    ERROR = "error"
    WARNING = "warning"

    def __init__(self, level, message, file=None, line=None):
        self.level = level
        self.message = message
        self.file = file
        self.line = line

    def __str__(self):
        prefix = self.file or ""
        if self.line is not None:
            prefix += f":{self.line}"
        if prefix:
            prefix += " — "
        marker = "ERROR" if self.level == self.ERROR else "WARNING"
        return f"  [{marker}] {prefix}{self.message}"


class LintResult:
    """Accumulates diagnostics from a lint run."""

    def __init__(self):
        self.diagnostics: list[Diagnostic] = []

    def error(self, msg, **kw):
        self.diagnostics.append(Diagnostic(Diagnostic.ERROR, msg, **kw))

    def warning(self, msg, **kw):
        self.diagnostics.append(Diagnostic(Diagnostic.WARNING, msg, **kw))

    @property
    def errors(self):
        return [d for d in self.diagnostics if d.level == Diagnostic.ERROR]

    @property
    def warnings(self):
        return [d for d in self.diagnostics if d.level == Diagnostic.WARNING]

    @property
    def ok(self):
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# HTML / XHTML validation helpers
# ---------------------------------------------------------------------------

# Tags that Apple Books is known to render poorly or ignore entirely.
_APPLE_BOOKS_UNSUPPORTED_TAGS = {
    "video", "audio", "canvas", "iframe", "object", "embed",
    "form", "input", "select", "textarea", "button",
    "script", "applet",
}

# Void (self-closing) HTML elements — these must NOT have children or a closing tag.
_VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Tags that must be properly closed in XHTML
_BLOCK_TAGS = {
    "div", "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "table", "tr", "td", "th", "thead", "tbody",
    "blockquote", "pre", "section", "article", "nav", "aside",
    "figure", "figcaption", "details", "summary", "main", "header", "footer",
    "span", "a", "em", "strong", "code", "sup", "sub",
}


class _XHTMLChecker(HTMLParser):
    """Quick structural check over generated XHTML/HTML."""

    def __init__(self, result: LintResult, filename: str):
        super().__init__()
        self._result = result
        self._filename = filename
        self._stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _APPLE_BOOKS_UNSUPPORTED_TAGS:
            self._result.warning(
                f"<{tag}> is unsupported or poorly rendered in Apple Books",
                file=self._filename,
                line=self.getpos()[0],
            )
        attr_dict = dict(attrs)
        # Check for javascript: hrefs
        href = attr_dict.get("href", "")
        if href.lower().startswith("javascript:"):
            self._result.error(
                "javascript: URIs are not allowed in EPUB",
                file=self._filename,
                line=self.getpos()[0],
            )
        # Check img has alt text (Apple Books accessibility requirement)
        if tag == "img" and not attr_dict.get("alt"):
            self._result.warning(
                "<img> missing alt attribute (required for accessibility in Apple Books)",
                file=self._filename,
                line=self.getpos()[0],
            )
        if tag not in _VOID_ELEMENTS:
            self._stack.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _VOID_ELEMENTS:
            return
        if not self._stack:
            self._result.error(
                f"Unexpected closing </{tag}> with no matching open tag",
                file=self._filename,
                line=self.getpos()[0],
            )
            return
        if self._stack[-1] != tag:
            self._result.error(
                f"Mismatched tags: expected </{self._stack[-1]}>, found </{tag}>",
                file=self._filename,
                line=self.getpos()[0],
            )
            # Try to recover
            if tag in self._stack:
                while self._stack and self._stack[-1] != tag:
                    self._stack.pop()
                if self._stack:
                    self._stack.pop()
        else:
            self._stack.pop()

    def finish(self):
        for tag in reversed(self._stack):
            self._result.error(
                f"Unclosed <{tag}> tag",
                file=self._filename,
            )


def _check_xhtml_wellformed(xhtml_str, result, filename):
    """Verify XHTML is well-formed XML (required for EPUB)."""
    try:
        ET.fromstring(xhtml_str)
    except ET.ParseError as e:
        result.error(f"Malformed XHTML/XML: {e}", file=filename)


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_book_yaml(project_root, result):
    """Validate config.yaml structure and required metadata."""
    book_yaml_path = os.path.join(project_root, "config.yaml")
    if not os.path.exists(book_yaml_path):
        result.error("config.yaml not found", file="config.yaml")
        return None

    try:
        with open(book_yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result.error(f"Invalid YAML syntax: {e}", file="config.yaml")
        return None

    if not isinstance(config, dict):
        result.error("config.yaml must be a YAML mapping", file="config.yaml")
        return None

    metadata = config.get("metadata", {})
    if not metadata:
        result.error("Missing 'metadata' section", file="config.yaml")
    else:
        # Required for any EPUB and Apple Books
        required = ["title", "author", "language", "identifier"]
        for key in required:
            if not metadata.get(key):
                result.error(f"Missing required metadata field: {key}", file="config.yaml")

        # Apple Books strongly recommends these
        recommended = ["description", "publisher", "date"]
        for key in recommended:
            if not metadata.get(key):
                result.warning(
                    f"Missing recommended metadata field: {key} (recommended for Apple Books)",
                    file="config.yaml",
                )

        # Validate language tag format (BCP 47)
        lang = metadata.get("language", "")
        if lang and not re.match(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]+)*$", lang):
            result.warning(
                f"Language '{lang}' may not be a valid BCP 47 tag (e.g. 'en', 'en-US')",
                file="config.yaml",
            )

    # Check cover image reference
    cover = config.get("cover_image")
    if cover:
        # Will be validated later against discovered images
        pass
    else:
        result.warning(
            "No cover_image specified — Apple Books requires a cover image for store submissions",
            file="config.yaml",
        )

    return config


def _check_jinja_syntax(content, result, filepath):
    """Validate Jinja2 template syntax without rendering."""
    try:
        env = Environment(loader=BaseLoader())
        env.parse(content)
    except TemplateSyntaxError as e:
        result.error(
            f"Jinja2 syntax error: {e.message}",
            file=filepath,
            line=e.lineno,
        )
        return False
    return True


def _check_jinja_render(content, context, result, filepath):
    """Try to render a Jinja2 template and catch undefined variables, etc."""
    from jinja2 import StrictUndefined
    try:
        env = Environment(loader=BaseLoader(), undefined=StrictUndefined)
        template = env.from_string(content)
        template.render(**context)
    except Exception as e:
        error_str = str(e)
        # Filter out noise — only report clear template errors
        if "UndefinedError" in type(e).__name__ or "TemplateError" in type(e).__name__:
            result.error(f"Jinja2 render error: {error_str}", file=filepath)
        else:
            result.error(f"Template render error: {error_str}", file=filepath)
        return False
    return True


def _check_chapter_content(md_content, rendered_md, result, filepath):
    """Check chapter content for common issues."""

    # Check for excessively long lines (Apple Books can choke on very long paragraphs
    # in some rendering modes — warn over 10 000 chars per line)
    for i, line in enumerate(md_content.split("\n"), 1):
        if len(line) > 10000:
            result.warning(
                f"Line exceeds 10,000 characters — may cause rendering issues",
                file=filepath,
                line=i,
            )

    # Check for BOM characters
    if md_content.startswith("\ufeff"):
        result.warning("File starts with a BOM character — may cause issues in some readers", file=filepath)

    # Check for null bytes
    if "\x00" in md_content:
        result.error("File contains null bytes", file=filepath)

    # Check for common markdown issues that lead to bad EPUB rendering
    # Unmatched heading levels (jumping from h1 to h4, for example)
    headings = re.findall(r"^(#{1,6})\s", md_content, re.MULTILINE)
    if headings:
        levels = [len(h) for h in headings]
        for i in range(1, len(levels)):
            if levels[i] - levels[i - 1] > 1:
                result.warning(
                    f"Heading level jumps from h{levels[i-1]} to h{levels[i]} — "
                    f"may confuse Apple Books navigation",
                    file=filepath,
                )
                break  # one warning per file is enough

    # Check that the chapter has at least one heading (Apple Books uses headings for navigation)
    if not headings:
        result.warning(
            "Chapter has no headings — Apple Books relies on headings for navigation",
            file=filepath,
        )


def _check_inline_html(md_content, result, filepath):
    """Check inline HTML in markdown for issues."""
    # Find inline HTML blocks
    html_pattern = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>", re.MULTILINE)
    for match in html_pattern.finditer(md_content):
        tag = match.group(1).lower()
        if tag in _APPLE_BOOKS_UNSUPPORTED_TAGS:
            line_num = md_content[:match.start()].count("\n") + 1
            result.warning(
                f"<{tag}> is unsupported or poorly rendered in Apple Books",
                file=filepath,
                line=line_num,
            )


def _check_generated_xhtml(rendered_md, css_files, result, filepath):
    """Convert rendered markdown to XHTML and validate it."""
    from ebk.core.epub_builder import convert_chapter_to_xhtml

    xhtml = convert_chapter_to_xhtml(rendered_md, css_files)

    # Check well-formed XML (EPUB requires valid XHTML)
    _check_xhtml_wellformed(xhtml, result, filepath)

    # Structural HTML checks
    checker = _XHTMLChecker(result, filepath)
    try:
        checker.feed(xhtml)
        checker.finish()
    except Exception:
        # HTMLParser can be noisy — XML check above is the authoritative one
        pass

    return xhtml


def _check_css(css_path, result):
    """Basic CSS validation for EPUB/Apple Books compatibility."""
    filename = os.path.basename(css_path)
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
    except Exception as e:
        result.error(f"Cannot read CSS file: {e}", file=filename)
        return

    # Check for features Apple Books doesn't support well
    problematic_patterns = [
        (r"position\s*:\s*fixed", "position:fixed is ignored by most EPUB readers including Apple Books"),
        (r"position\s*:\s*sticky", "position:sticky is ignored by most EPUB readers"),
        (r"@media\s+screen", "@media screen queries may not work as expected in Apple Books"),
        (r"display\s*:\s*grid", "CSS Grid has limited support in Apple Books"),
        (r"display\s*:\s*flex", "Flexbox has limited support in older Apple Books versions"),
        (r"animation\s*:", "CSS animations are unsupported in Apple Books"),
        (r"transition\s*:", "CSS transitions are unsupported in Apple Books"),
        (r"@keyframes", "CSS keyframes are unsupported in Apple Books"),
    ]

    for pattern, msg in problematic_patterns:
        for match in re.finditer(pattern, css, re.IGNORECASE):
            line_num = css[:match.start()].count("\n") + 1
            result.warning(msg, file=filename, line=line_num)

    # Check for unmatched braces
    depth = 0
    for i, ch in enumerate(css):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth < 0:
            line_num = css[:i].count("\n") + 1
            result.error("Unmatched closing brace '}'", file=filename, line=line_num)
            break
    if depth > 0:
        result.error(f"Unclosed brace — {depth} opening '{{' without matching '}}'", file=filename)


def _check_images(project_root, images_map, config, result):
    """Validate images for EPUB / Apple Books."""
    cover = config.get("cover_image")
    if cover and cover not in images_map:
        result.error(f"Cover image '{cover}' referenced in config.yaml but not found", file="config.yaml")

    for img_name, img_path in images_map.items():
        size = os.path.getsize(img_path)
        # Apple Books rejects images larger than ~10 MB
        if size > 10 * 1024 * 1024:
            result.error(
                f"Image exceeds 10 MB ({size / (1024*1024):.1f} MB) — Apple Books will reject this",
                file=img_name,
            )
        elif size > 4 * 1024 * 1024:
            result.warning(
                f"Image is {size / (1024*1024):.1f} MB — consider compressing for better Apple Books performance",
                file=img_name,
            )

        # Check supported formats
        ext = os.path.splitext(img_name)[1].lower()
        if ext == ".svg":
            result.warning(
                "SVG images have limited support in Apple Books — consider using PNG or JPEG",
                file=img_name,
            )
        elif ext == ".gif":
            result.warning(
                "Animated GIFs are not reliably rendered in Apple Books",
                file=img_name,
            )
        elif ext not in {".jpg", ".jpeg", ".png"}:
            result.warning(f"Image format '{ext}' may not be supported by all EPUB readers", file=img_name)


def _check_context_files(project_root, result):
    """Validate context YAML/JSON files."""
    context_dir = os.path.join(project_root, "context")
    if not os.path.isdir(context_dir):
        return

    for item in sorted(os.listdir(context_dir)):
        path = os.path.join(context_dir, item)
        if not os.path.isfile(path):
            continue

        if item.endswith(".yaml") or item.endswith(".yml"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data is not None and not isinstance(data, dict):
                    result.warning(
                        f"Context file should contain a YAML mapping, got {type(data).__name__}",
                        file=f"context/{item}",
                    )
            except yaml.YAMLError as e:
                result.error(f"Invalid YAML: {e}", file=f"context/{item}")

        elif item.endswith(".json"):
            import json
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                result.error(f"Invalid JSON: {e}", file=f"context/{item}")


def _check_epub_structure(project_root, result):
    """Check that the project has the basic structure needed for a valid EPUB."""
    if not os.path.exists(os.path.join(project_root, ".ebk")):
        result.error("Missing .ebk marker file")
    if not os.path.exists(os.path.join(project_root, "config.yaml")):
        result.error("Missing config.yaml")


def _check_total_size(project_root, images_map, css_files_map, result):
    """Warn if total book size might be problematic."""
    total = 0
    for path in images_map.values():
        if os.path.exists(path):
            total += os.path.getsize(path)
    for path in css_files_map.values():
        if os.path.exists(path):
            total += os.path.getsize(path)

    # Apple Books has a 2 GB hard limit; warn at 500 MB
    if total > 500 * 1024 * 1024:
        mb = total / (1024 * 1024)
        result.warning(
            f"Total asset size is {mb:.0f} MB — Apple Books has a 2 GB limit and "
            f"large files cause slow downloads",
        )


# ---------------------------------------------------------------------------
# Main lint entry point
# ---------------------------------------------------------------------------

def lint_project(project_root, flags=None, chapters_filter=None):
    """
    Lint an ebk project and return a LintResult.

    Checks performed:
      - Project structure (.ebk, config.yaml)
      - config.yaml validity and required metadata
      - Context file syntax (YAML / JSON)
      - Jinja2 template syntax in every chapter
      - Jinja2 rendering (catches undefined variables)
      - Markdown content quality (heading levels, empty chapters)
      - Inline HTML compatibility (Apple Books unsupported tags)
      - Generated XHTML well-formedness
      - CSS compatibility with Apple Books
      - Image size and format checks
      - Total asset size

    Args:
        project_root: Path to the ebk project directory
        flags: Feature flags to use during lint (affects Jinja2 rendering)
        chapters_filter: Optional chapter selectors to limit scope

    Returns:
        LintResult with collected diagnostics
    """
    result = LintResult()

    # 1. Project structure
    _check_epub_structure(project_root, result)

    # 2. config.yaml
    config = _check_book_yaml(project_root, result)
    if config is None:
        # Can't proceed without a valid config
        return result

    config["flags"] = flags or []

    # 3. Context files
    _check_context_files(project_root, result)

    # 4. Discover chapters
    discovery_config = config.get("discovery", {})
    exclude_dirs = discovery_config.get("exclude", [
        ".git", ".venv", "venv", "node_modules", "__pycache__",
        ".ebk", "build", "dist", "context",
    ])
    content_root_config = discovery_config.get("root", ".")
    content_root = (
        project_root
        if content_root_config == "."
        else os.path.join(project_root, content_root_config)
    )

    all_chapters = get_chapters(content_root, exclude_dirs)
    chapters = filter_chapters(all_chapters, chapters_filter or [])

    if not chapters:
        result.error(f"No markdown files found in {content_root}")
        return result

    # 5. Discover assets
    css_extensions = discovery_config.get("css_extensions", [".css"])
    image_extensions = discovery_config.get("image_extensions", [".jpg", ".jpeg", ".png", ".gif", ".svg"])

    css_files_map = get_all_files_with_paths(project_root, css_extensions, exclude_dirs)
    css_files = list(css_files_map.keys())

    images_map = get_all_files_with_paths(project_root, image_extensions, exclude_dirs)

    # 6. Validate CSS
    for css_name, css_path in css_files_map.items():
        _check_css(css_path, result)

    # 7. Validate images
    _check_images(project_root, images_map, config, result)

    # 8. Total asset size
    _check_total_size(project_root, images_map, css_files_map, result)

    # 9. Validate each chapter
    for chapter in chapters:
        filepath = chapter.get("relative_path", chapter["name"])
        full_path = chapter["path"]

        # Read raw content
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                md_content = f.read()
        except Exception as e:
            result.error(f"Cannot read file: {e}", file=filepath)
            continue

        # Check Jinja2 syntax (before rendering)
        if not _check_jinja_syntax(md_content, result, filepath):
            continue  # skip further checks if syntax is broken

        # Build context and render
        context = load_context(project_root, full_path, config)
        if not _check_jinja_render(md_content, context, result, filepath):
            continue

        # Re-render to get the output
        try:
            rendered_md = render_template(md_content, context)
        except Exception:
            continue  # already reported above

        # Content-level checks on raw markdown
        _check_chapter_content(md_content, rendered_md, result, filepath)

        # Inline HTML checks on raw markdown
        _check_inline_html(md_content, result, filepath)

        # Generate XHTML and validate
        _check_generated_xhtml(rendered_md, css_files, result, filepath)

    return result


# ---------------------------------------------------------------------------
# CLI-friendly runner
# ---------------------------------------------------------------------------

def run_lint(project_root, flags=None, chapters_filter=None):
    """
    Run the linter and print results. Returns exit code (0 = pass, 1 = errors found).
    """
    print("Linting ebk project...")
    result = lint_project(project_root, flags=flags, chapters_filter=chapters_filter)

    if not result.diagnostics:
        print("\n✓ No issues found.")
        return 0

    # Group by file
    by_file: dict[str | None, list[Diagnostic]] = {}
    for d in result.diagnostics:
        by_file.setdefault(d.file, []).append(d)

    print()
    for file_key in sorted(by_file, key=lambda x: x or ""):
        if file_key:
            print(f"  {file_key}")
        for d in by_file[file_key]:
            loc = ""
            if d.line is not None:
                loc = f":{d.line}"
            marker = "ERROR" if d.level == Diagnostic.ERROR else "warning"
            if file_key:
                print(f"    [{marker}]{loc} {d.message}")
            else:
                print(f"  [{marker}] {d.message}")

    errors = len(result.errors)
    warnings = len(result.warnings)
    parts = []
    if errors:
        parts.append(f"{errors} error{'s' if errors != 1 else ''}")
    if warnings:
        parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")

    print()
    if errors:
        print(f"✗ {', '.join(parts)}")
    else:
        print(f"✓ {', '.join(parts)} (no errors)")

    return 1 if errors else 0
