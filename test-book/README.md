# Test Book

An EPUB book project created with [ebk](https://github.com/anthropics/ebk).

## Project Structure

```
.
├── config.yaml              # Book metadata and configuration
├── pages/                 # Your markdown chapters (supports deep nesting)
│   └── 01-introduction.md
├── context/               # Jinja2 context files for template variables
│   └── global.yaml
├── assets/
│   ├── images/           # Book images
│   └── css/              # Custom stylesheets
│       └── custom.css
└── README.md             # This file
```

## Building Your Book

Run `ebk` in this directory to build your EPUB:

```bash
ebk
```

The output file will be created as `test-book.epub` in this directory.

## Directory Guidelines

### pages/
Place all your markdown chapters here. You can use deep nesting to organize complex books.

**Ordering chapters:**
- Use numeric prefixes: `01-intro.md`, `02-chapter.md`, etc.
- Or use frontmatter: Add `order: 1` in YAML frontmatter
- Files named `_chapter.md` serve as folder introductions

### context/
Add Jinja2 template variables here:
- `global.yaml` - Variables available in all chapters
- `{chapter-name}.yaml` - Chapter-specific overrides

**Example global.yaml:**
```yaml
product_name: "MyApp"
version: "2.0"
author_bio: "About the author..."
```

**Usage in markdown:**
```markdown
# Welcome to {{ product_name }}

This guide covers version {{ version }}.
```

### assets/images/
Place all book images here. Reference them in markdown:
```markdown
![Cover Image](../assets/images/cover.jpg)
```

### assets/css/
Add custom stylesheets here. Specify them in `config.yaml`:
```yaml
default_css:
  - "custom.css"
```

## Configuration (config.yaml)

Edit `config.yaml` to set:
- Book metadata (title, author, language, etc.)
- Cover image location (optional)
- CSS files to include
- Chapter discovery mode (auto or manual)
- Output filename

## Tips

1. **Preview your book**: Build frequently to see changes
2. **Use context files**: Keep variables separate from content for easier maintenance
3. **Organize with folders**: Use nested folders for multi-part books
4. **Test your templates**: Make sure Jinja2 syntax is correct before building

## Getting Help

Run `ebk --help` for usage information.

Happy writing!
