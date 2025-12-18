# Introduction

Welcome to **{book_title}**!

This is a sample chapter to help you get started with ebk.

## Getting Started

1. Edit `book.yaml` to set your book's metadata
2. Add your content as markdown files in the `content/` directory
3. Use numeric prefixes (01-, 02-, etc.) to control chapter ordering
4. Run `ebk` in this directory to build your EPUB

## Using Jinja2 Templates

You can use Jinja2 variables in your markdown files. For example:

- Book title: {{ book.title }}
- Author: {{ book.author }}
- Build date: {{ build_date }}

Add your own variables in `context/global.yaml` to use throughout your book.

## Chapter Ordering

Chapters are automatically discovered and ordered by:
1. Frontmatter `order:` field (if present)
2. Numeric prefix in filename (01-, 02-, etc.)
3. Alphabetical order

## Deep Nesting

You can organize chapters into folders for complex books:

```
content/
├── 01-introduction.md
├── 02-getting-started/
│   ├── _chapter.md        # Folder intro
│   ├── 01-installation.md
│   └── 02-configuration.md
└── 03-advanced/
    └── 01-plugins.md
```

Files prefixed with `_chapter.md` serve as introductions for their folder.

## Next Steps

Replace this content with your own chapters and run `ebk` to build your book!
