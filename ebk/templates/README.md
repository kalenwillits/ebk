# {book_title}

An EPUB book project created with [ebk](https://github.com/anthropics/ebk).

## Project Structure

ebk finds your content by file extension, not directory location. Organize however you prefer!

**Suggested structure** (created by scaffolding):
```
.
├── config.yaml              # Book metadata and configuration
├── pages/                 # Markdown chapters (optional - can be anywhere)
│   └── 01-introduction.md
├── context/               # Jinja2 template variables
│   └── global.yaml
├── assets/
│   ├── images/           # Images (optional - can be anywhere)
│   └── css/              # Stylesheets (optional - can be anywhere)
│       └── custom.css
└── README.md
```

**Flat structure** (also works):
```
.
├── config.yaml
├── 01-intro.md           # Chapters in root
├── 02-getting-started.md
├── cover.jpg             # Images in root
├── custom.css            # CSS in root
└── context/
    └── global.yaml
```

**Or any mix** of flat and nested you prefer.

## Building Your Book

Run `ebk` in this directory to build your EPUB:

```bash
ebk
```

The output file will be created as `{output_filename}` in this directory.

## Content Organization

### Markdown Files (.md)
ebk recursively searches for `.md` files throughout your project (except excluded directories).

**Ordering chapters:**
1. **Frontmatter order field** (highest priority): Add `order: 1` in YAML frontmatter
2. **Numeric prefix** (fallback): Use `01-intro.md`, `02-chapter.md`, etc.
3. **Directory depth & alphabetical** (final fallback)

**Special files:**
- `_chapter.md` - Folder introduction (works at any nesting level)

### Images
ebk finds images anywhere in your project: `.jpg`, `.jpeg`, `.png`, `.gif`, `.svg`

Reference images in your markdown:
```markdown
![Cover Image](cover.jpg)
```

### CSS Stylesheets
ebk finds `.css` files anywhere in your project. Specify which to include in `config.yaml`:
```yaml
default_css:
  - "custom.css"
```

### Jinja2 Template Variables (context/)
Add template variables in the `context/` directory:
- `global.yaml` - Variables available in all chapters
- `{chapter-name}.yaml` - Chapter-specific overrides

**Example global.yaml:**
```yaml
product_name: "MyApp"
version: "2.0"
```

**Usage in markdown:**
```markdown
# Welcome to {{ product_name }}

This guide covers version {{ version }}.
```

### Excluding Directories
By default, ebk skips: `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.ebk`, `build`, `dist`, `context`

Customize exclusions in `config.yaml`:
```yaml
discovery:
  exclude:
    - ".git"
    - "drafts"       # Add your own
    - "archive"
```

## Configuration (config.yaml)

Edit `config.yaml` to set:
- Book metadata (title, author, language, etc.)
- Cover image location (optional)
- CSS files to include
- Chapter discovery mode (auto or manual)
- Output filename

## Tips

1. **Organize however you prefer**: ebk finds files by extension, so use the structure that makes sense for your project
2. **Preview your book**: Build frequently to see changes
3. **Use context files**: Keep variables separate from content for easier maintenance
4. **Use numeric prefixes or frontmatter order**: Control chapter order explicitly
5. **Test your templates**: Make sure Jinja2 syntax is correct before building
6. **Exclude draft directories**: Add `drafts/` or `archive/` to discovery.exclude in config.yaml

## Getting Help

Run `ebk --help` for usage information.

Happy writing!
