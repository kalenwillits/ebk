# ebk - E-Book CLI

A simple, opinionated CLI utility for building EPUB, PDF, and HTML books from markdown with Jinja2 templating.

## Features

- **Simple CLI**: Two commands — create new books and build output
- **Markdown-based**: Write your book in markdown with full GitHub-flavored markdown support
- **Jinja2 templating**: Use variables, conditionals, and loops in your content
- **Feature flags**: Conditionally render content based on build flags (e.g. presentation vs. print mode)
- **Deep nesting**: Organize complex books with unlimited folder nesting
- **Multiple output formats**: EPUB, PDF, and HTML
- **Built-in linter**: Validate Jinja2 syntax, XHTML, metadata, CSS, and Apple Books compatibility
- **Single binary**: Package as standalone executable with PyInstaller

## Quick Start

### Installation

#### From Source

```bash
git clone https://github.com/anthropics/ebk.git
cd ebk
pip install -r requirements.txt
pip install -e .

# Or build standalone binary
./build.sh
./install.sh
```

#### From PyPI (coming soon)

```bash
pip install ebk
```

### Create Your First Book

```bash
ebk "My First Book"
cd my-first-book
# Add your markdown files, edit book.yaml
ebk
```

Your EPUB will be generated in the project root.

## Usage

### Commands

```bash
ebk "Book Name"    # Create new book project
ebk                # Build EPUB from current directory
ebk --html         # Build HTML output
ebk --pdf          # Build PDF
ebk --check        # Lint project for errors
ebk --version      # Show version
ebk --help         # Show help
```

### PDF Options

```bash
ebk --pdf                        # Default: A4, 11pt
ebk --pdf --font-size 14         # 14pt body text
ebk --pdf --landscape            # A4 landscape orientation
ebk --pdf --no-cover             # Omit the title/author cover page
ebk --pdf --no-toc               # Omit the table of contents page
ebk --pdf --no-cover --no-toc   # Content only, no frontmatter
```

### Output Path

```bash
ebk -o build/                    # Place output in build/ directory
ebk -o build/my-book.epub        # Custom filename
ebk --pdf -o dist/handout.pdf    # PDF with custom path
ebk --html -o dist/html/         # HTML to a specific directory
```

### Chapter Selection

```bash
ebk -c 2                         # Chapter 2 only (1-based index)
ebk -c 1 -c 3                    # Chapters 1 and 3
ebk -c runway                    # Any chapter whose filename contains "runway"
ebk --pdf -c 2 --no-cover --no-toc  # Single chapter PDF, no frontmatter
```

### Linting

Validate your project before building — checks are held to the Apple Books standard (the strictest major EPUB reader):

```bash
ebk --check                      # Lint entire project
ebk --check -c 2                 # Lint only chapter 2
ebk --check -f present           # Lint with feature flag enabled
```

The linter checks:
- **book.yaml**: required and recommended metadata fields, YAML syntax, BCP 47 language tags
- **Jinja2 templates**: syntax errors and undefined variables in every chapter
- **XHTML well-formedness**: generated output is valid XML (required by EPUB spec)
- **HTML compatibility**: flags tags unsupported by Apple Books (`<video>`, `<audio>`, `<iframe>`, `<script>`, `<form>`, etc.)
- **Accessibility**: missing `alt` attributes on images
- **CSS compatibility**: warns about `position:fixed`, CSS Grid, Flexbox, animations, and other features Apple Books ignores
- **CSS syntax**: unmatched braces
- **Images**: size limits (Apple Books rejects >10 MB), format warnings (SVG, GIF)
- **Content quality**: heading level jumps, missing headings, null bytes, BOM characters
- **Context files**: validates YAML/JSON syntax in `context/` directory
- **Cover image**: warns if missing, errors if referenced but not found

Exit code is `0` if no errors (warnings are OK), `1` if errors are found.

### Feature Flags

Pass one or more flags to conditionally render content:

```bash
ebk -f present                   # Enable the "present" flag
ebk --flag present               # Same, long form
ebk -f present -f draft          # Multiple flags
ebk --pdf -f present --landscape # Combine with other options
```

Flags are available in any markdown file as a Jinja2 set:

```markdown
{% if 'present' in flags %}
<div style="page-break-before: always;"></div>
{% endif %}

{% if 'present' not in flags %}
> **Instructor Note:** Detailed explanation for self-study readers.
{% endif %}
```

## Project Structure

```
my-book/
├── book.yaml         # Book metadata and configuration
├── .ebk              # Project marker file
├── README.md         # Project-specific guide
└── custom.css        # Custom stylesheet
```

ebk discovers content recursively — add markdown files anywhere in the project. Use numeric prefixes or frontmatter `order:` to control chapter order.

```
my-book/
├── 01-introduction.md
├── 02-getting-started.md
├── 03-advanced/
│   ├── _chapter.md          # Folder introduction
│   ├── 01-configuration.md
│   └── 02-deployment.md
└── 99-appendix.md
```

Files named `_chapter.md` serve as introductions for their folder.

## Configuration (book.yaml)

```yaml
metadata:
  title: "My Book"
  author: "Author Name"
  language: "en-US"
  identifier: "unique-uuid"
  date: "2025-12-18"
  publisher: ""
  description: "Book description"
  subject: ""

# Optional cover image (ebk finds it by extension anywhere in the project)
# cover_image: "cover.jpg"

# CSS files to include
default_css:
  - "custom.css"

# Content discovery
discovery:
  root: "."             # Search from project root
  exclude:
    - ".git"
    - "build"
    - "dist"
    - "context"

# Output filenames
output:
  filename: "my-book.epub"
  pdf_filename: "my-book.pdf"  # optional, defaults to project dir name
  html_dir: "html"             # optional, defaults to "html"
```

## Writing Content

### Chapter Ordering

Use numeric prefixes:

```
01-introduction.md
02-chapter-two.md
03-conclusion.md
```

Or use YAML frontmatter:

```markdown
---
title: Custom Chapter Title
order: 5
---

# Chapter Content
```

### Markdown Features

Full GitHub-flavored markdown support: headers, emphasis, ordered/unordered lists, fenced code blocks with syntax highlighting, tables, images, links, footnotes, and inline HTML.

### Jinja2 Templating

Variables are rendered in markdown before HTML conversion:

```markdown
# Welcome to {{ book.title }}

Written by {{ book.author }}. Built on {{ build_date }}.
```

#### Context Files

**`context/global.yaml`** — Variables available in all chapters:

```yaml
product_name: "MyApp"
version: "2.0"
website: "https://example.com"
```

**`context/chapter-name.yaml`** — Per-chapter overrides (filename matches the chapter's `.md` filename without extension).

**Context merge order** (later overrides earlier):
1. Built-in: `ebk_version`, `build_date`
2. Global: `context/global.yaml`
3. Chapter-specific: `context/{chapter-name}.yaml`
4. Book metadata: `book.title`, `book.author`, etc.
5. Feature flags: `flags` (set of active flag strings)

#### Jinja2 Features

```markdown
{% if product_name == "MyApp" %}
Special content for MyApp!
{% endif %}

{% for item in items %}
- {{ item }}
{% endfor %}

{{ variable_name }}
```

## Output Formats

### EPUB

```bash
ebk
```

Generates a valid EPUB 3 file with backward-compatible EPUB 2 TOC, embedded fonts, and all images and CSS bundled.

### PDF

```bash
ebk --pdf
ebk --pdf --font-size 14
ebk --pdf --landscape
```

Requires `weasyprint` (`pip install weasyprint`). Uses A4 page size by default.

### HTML

```bash
ebk --html
```

Outputs to `html/` (configurable via `output.html_dir` in `book.yaml`):

```
html/
├── index.html       # Table of contents
├── s00000.html
├── s00001.html
├── css/
└── images/
```

## Advanced Usage

### Feature Flags

Feature flags enable conditional rendering at build time — useful for producing different versions of the same content (e.g. presentation slides vs. print handout, draft vs. published).

Flags are passed via `-f`/`--flag` and are available in templates as a Python set:

```bash
ebk --pdf -f present --landscape --font-size 16
```

```markdown
# {{ book.title }}

{% if 'present' in flags %}
<div class="slide-break"></div>
{% endif %}

{% if 'present' not in flags %}
This section contains detailed background reading not covered in the presentation.
{% endif %}
```

Multiple flags compose naturally:

```bash
ebk -f present -f instructor
```

```markdown
{% if 'instructor' in flags %}
> **Answer key:** The correct response is C.
{% endif %}
```

### Tailwind CSS

Define Tailwind class aliases in `book.yaml` and use them in markdown:

```yaml
tw:
  card: "rounded-lg shadow p-6 bg-white"
  hero: "text-4xl font-bold text-center"
```

```markdown
<div class="{{ tw.card }}">
  <h1 class="{{ tw.hero }}">{{ book.title }}</h1>
</div>
```

Generate the Tailwind CSS file with the Tailwind CLI and include it in `default_css`.

> **Note:** EPUB reader CSS support varies. Tailwind works best with `--html` output. For e-ink readers, use conventional CSS.

### Cover Image

Place an image anywhere in the project and reference it in `book.yaml`:

```yaml
cover_image: "cover.jpg"
```

Supported formats: JPG, PNG, GIF, SVG.

## Building Standalone Binary

```bash
./build.sh    # Creates dist/ebk
./install.sh  # Copies to /usr/local/bin/ebk
```

## Development

### Requirements

- Python 3.7+
- `markdown >= 3.1`
- `Jinja2 >= 3.0`
- `PyYAML >= 6.0`
- `weasyprint` (PDF only)

### Setup

```bash
git clone https://github.com/anthropics/ebk.git
cd ebk
pip install -r requirements.txt
pip install -e .
```

### Running Tests

```bash
pytest
```

### Project Structure

```
ebk/
├── ebk/
│   ├── cli.py                       # CLI entry point
│   └── core/
│       ├── epub_builder.py          # EPUB generation
│       ├── pdf_builder.py           # PDF generation (weasyprint)
│       ├── html_builder.py          # HTML generation
│       ├── linter.py                # Project linter (--check)
│       ├── markdown_processor.py    # Chapter discovery and ordering
│       ├── template_engine.py       # Jinja2 rendering
│       └── project_structure.py     # Project scaffolding
├── ebk.spec                         # PyInstaller config
├── build.sh
└── install.sh
```

## How It Works

1. **Project creation**: `ebk "Book Name"` initializes `book.yaml` and project files
2. **Chapter discovery**: Recursively scans the project for markdown files
3. **Ordering**: Uses numeric prefixes or frontmatter `order:` field
4. **Jinja2 rendering**: Applies templates before markdown conversion; injects `flags`, `book`, context variables
5. **Markdown conversion**: Converts to HTML/XHTML with tables, code highlighting, footnotes
6. **Output generation**: EPUB 3, PDF (weasyprint), or HTML directory

## Troubleshooting

**"Error: Not an ebk project"** — Make sure you're in a directory with `.ebk` and `book.yaml`.

**"No markdown files found"** — Check your `discovery.root` and `discovery.exclude` settings in `book.yaml`.

**"Error parsing book.yaml"** — Verify YAML syntax with a YAML validator.

**Template errors** — Check Jinja2 syntax; the error message includes the line number. Run `ebk --check` to find all template issues before building.

**PDF export fails** — Install weasyprint: `pip install weasyprint`.

## License

MIT License

## Credits

EPUB generation logic based on [mark2epub](https://github.com/AlexPof/mark2epub) by AlexPof.
