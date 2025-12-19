# ebk - E-Book CLI

A simple, opinionated CLI utility for managing EPUB book projects with markdown, Jinja2 templating, and deep nesting support.

## Features

- **Simple CLI**: Two commands - create new books and build EPUBs
- **Markdown-based**: Write your book in markdown with full GitHub-flavored markdown support
- **Jinja2 templating**: Use variables, conditionals, and loops in your content
- **Deep nesting**: Organize complex books with unlimited folder nesting
- **Opinionated structure**: Clear, consistent project layout
- **Single binary**: Package as standalone executable with PyInstaller
- **Based on proven tech**: Built on mark2epub's EPUB generation logic

## Quick Start

### Installation

#### From Source

```bash
# Clone and install
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
# Create a new book project
ebk "My First Book"

# Navigate to the project
cd my-first-book

# Edit book.yaml with your metadata
# Add your content to pages/
# Run ebk to build

ebk
```

That's it! Your EPUB will be generated in the project root.

## Usage

### Commands

```bash
ebk "Book Name"    # Create new book project
ebk                # Build EPUB from current directory
ebk --version      # Show version
ebk --help         # Show help
```

## Project Structure

When you create a new book with `ebk "My Book"`, this structure is created:

```
my-book/
├── book.yaml              # Book metadata and configuration
├── pages/                 # Your markdown chapters
│   └── 01-introduction.md
├── context/               # Jinja2 context files
│   └── global.yaml
├── assets/
│   ├── images/           # Book images
│   └── css/              # Custom stylesheets
│       └── custom.css
├── .ebk                  # Project marker file
└── README.md             # Project-specific guide
```

## Configuration (book.yaml)

```yaml
metadata:
  title: "My Book"
  author: "Author Name"
  language: "en-US"
  identifier: "unique-id"
  date: "2025-12-18"
  publisher: ""
  description: "Book description"
  subject: ""

# Optional cover image (relative to assets/images/)
# cover_image: "cover.jpg"

# CSS files to include
default_css:
  - "custom.css"

# Chapter discovery: "auto" or "manual"
content:
  discovery: "auto"

# Output filename
output:
  filename: "my-book.epub"
```

## Writing Content

### Organizing Chapters

Use numeric prefixes to control chapter order:

```
pages/
├── 01-introduction.md
├── 02-getting-started.md
├── 03-advanced-topics/
│   ├── _chapter.md        # Folder introduction
│   ├── 01-configuration.md
│   └── 02-deployment.md
└── 99-appendix.md
```

Files named `_chapter.md` serve as introductions for their folder.

### Alternative Ordering

Use YAML frontmatter with `order:` field:

```markdown
---
title: Custom Chapter Title
order: 5
---

# Chapter Content
```

### Markdown Features

Full GitHub-flavored markdown support:

- **Headers**: `# H1` through `###### H6`
- **Emphasis**: `*italic*`, `**bold**`, `***bold italic***`
- **Lists**: Ordered and unordered, with nesting
- **Code blocks**: With syntax highlighting
- **Tables**: GitHub-style tables
- **Images**: `![alt](path)`
- **Links**: `[text](url)`
- **Footnotes**: `[^1]` with `[^1]: Definition`

### Jinja2 Templating

Use variables in your markdown:

```markdown
# Welcome to {{ book.title }}

This guide was written by {{ book.author }}.

Build date: {{ build_date }}
Version: {{ version }}
```

#### Context Files

**context/global.yaml** - Variables for all chapters:

```yaml
product_name: "MyApp"
version: "2.0"
website: "https://example.com"
```

**context/chapter-name.yaml** - Chapter-specific overrides:

```yaml
custom_var: "Chapter-specific value"
```

**Context merge order** (later overrides earlier):
1. Built-in variables (`ebk_version`, `build_date`)
2. Global context (`context/global.yaml`)
3. Chapter-specific context (`context/{chapter-name}.yaml`)
4. Book metadata (`book.title`, `book.author`, etc.)

#### Jinja2 Features

```markdown
# Conditionals
{% if product_name == "MyApp" %}
Special content for MyApp users!
{% endif %}

# Loops
{% for item in items %}
- {{ item }}
{% endfor %}

# Variables
{{ variable_name }}
```

## Building Your Book

```bash
# In your book project directory
ebk
```

The EPUB will be generated in the project root with the name specified in `book.yaml`.

## Advanced Usage

### Custom CSS

Add your own stylesheets to `assets/css/` and reference them in `book.yaml`:

```yaml
default_css:
  - "custom.css"
  - "code-highlighting.css"
```

### Cover Image

Add a cover image to `assets/images/` and reference it in `book.yaml`:

```yaml
cover_image: "cover.jpg"
```

Supported formats: JPG, PNG, GIF, SVG

### Manual Chapter List

For fine-grained control, use manual chapter discovery:

```yaml
content:
  discovery: "manual"
  chapters:
    - path: "01-introduction.md"
    - path: "02-chapter.md"
      css: "special.css"  # Per-chapter CSS override
    - path: "03-nested/_chapter.md"
```

## Building Standalone Binary

```bash
./build.sh
```

This creates a single executable at `dist/ebk`.

### Installing System-Wide

```bash
./install.sh
```

This copies the binary to `/usr/local/bin/ebk`.

## Development

### Requirements

- Python 3.7+
- markdown >= 3.1
- Jinja2 >= 3.0
- PyYAML >= 6.0

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
├── ebk/                  # Main package
│   ├── cli.py           # CLI router
│   ├── core/
│   │   ├── project_structure.py   # Project scaffolding
│   │   ├── markdown_processor.py  # Chapter discovery
│   │   ├── template_engine.py     # Jinja2 integration
│   │   └── epub_builder.py        # EPUB generation
│   ├── templates/       # Default templates
│   └── resources/       # Default CSS
├── ebk.spec            # PyInstaller config
├── build.sh            # Build script
└── install.sh          # Install script
```

## How It Works

1. **Project creation**: `ebk "Book Name"` creates opinionated directory structure
2. **Chapter discovery**: Recursively scans `pages/` for markdown files
3. **Ordering**: Uses numeric prefixes or frontmatter `order:` field
4. **Jinja2 rendering**: Applies templates BEFORE markdown conversion
5. **Markdown conversion**: Converts to XHTML with extensions (tables, code, etc.)
6. **EPUB generation**: Creates valid EPUB 3 with backward compatibility
7. **Output**: Single `.epub` file in project root

## Credits

Built on [mark2epub](https://github.com/AlexPof/mark2epub) by AlexPof for EPUB generation logic.

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or pull request.

## Troubleshooting

### "Error: Not an ebk project"

Make sure you're in a directory with a `.ebk` file and `book.yaml`.

### "No markdown files found"

Check that your markdown files are in the `pages/` directory.

### "Error parsing book.yaml"

Verify your YAML syntax. Use a YAML validator if needed.

### Template errors

Check your Jinja2 syntax. The error message will include the line number.

### Cover image not showing

Ensure the cover image path in `book.yaml` matches the filename in `assets/images/`.

## Examples

See the `examples/` directory for sample projects demonstrating various features.

## FAQ

**Q: Can I use custom fonts?**
A: Not in v1.0. Use CSS to reference system fonts.

**Q: Can I export to PDF or other formats?**
A: Not currently. EPUB only for now.

**Q: Can I use HTML in my markdown?**
A: Yes, markdown supports inline HTML.

**Q: How do I add a table of contents?**
A: The TOC is automatically generated from your chapters.

**Q: Can I customize the TOC?**
A: Not in v1.0. The TOC is auto-generated.

**Q: What Python version do I need?**
A: Python 3.7 or higher.

## Roadmap

Future enhancements (not in v1.0):

- PDF export
- Live preview mode
- Custom fonts
- Math notation support
- Plugin system
- Multiple output formats

## Support

- GitHub Issues: [github.com/anthropics/ebk/issues](https://github.com/anthropics/ebk/issues)
- Documentation: [github.com/anthropics/ebk](https://github.com/anthropics/ebk)
