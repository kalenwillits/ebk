"""Project scaffolding for new ebk books."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
import uuid


def slugify(name):
    """Convert 'My Book Name' to 'my-book-name'."""
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def get_author_name():
    """Try to get author name from git config, fallback to 'Author Name'."""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'config', 'user.name'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return "Author Name"


def get_template_path():
    """Get the path to the templates directory."""
    # Get the ebk package directory
    package_dir = Path(__file__).parent.parent
    return package_dir / 'templates'


def get_resources_path():
    """Get the path to the resources directory."""
    package_dir = Path(__file__).parent.parent
    return package_dir / 'resources'


def create_directory_structure(project_dir):
    """Create the opinionated directory structure."""
    dirs = [
        'content',
        'context',
        'assets',
        'assets/images',
        'assets/css',
    ]

    for dir_name in dirs:
        dir_path = os.path.join(project_dir, dir_name)
        os.makedirs(dir_path, exist_ok=True)


def copy_and_populate_templates(project_dir, book_name):
    """Copy template files and populate variables."""
    template_dir = get_template_path()
    resources_dir = get_resources_path()

    # Get values for template variables
    slug = slugify(book_name)
    author_name = get_author_name()
    current_date = datetime.now().strftime("%Y-%m-%d")
    book_identifier = str(uuid.uuid4())
    output_filename = f"{slug}.epub"

    template_vars = {
        'book_title': book_name,
        'author_name': author_name,
        'current_date': current_date,
        'book_identifier': book_identifier,
        'output_filename': output_filename,
    }

    # Copy and populate book.yaml
    with open(template_dir / 'book.yaml', 'r') as f:
        book_yaml_content = f.read()

    for var, value in template_vars.items():
        book_yaml_content = book_yaml_content.replace(f'{{{var}}}', value)

    with open(os.path.join(project_dir, 'book.yaml'), 'w') as f:
        f.write(book_yaml_content)

    # Copy and populate README.md
    with open(template_dir / 'README.md', 'r') as f:
        readme_content = f.read()

    for var, value in template_vars.items():
        readme_content = readme_content.replace(f'{{{var}}}', value)

    with open(os.path.join(project_dir, 'README.md'), 'w') as f:
        f.write(readme_content)

    # Copy and populate chapter.md to content/
    with open(template_dir / 'chapter.md', 'r') as f:
        chapter_content = f.read()

    for var, value in template_vars.items():
        chapter_content = chapter_content.replace(f'{{{var}}}', value)

    with open(os.path.join(project_dir, 'content', '01-introduction.md'), 'w') as f:
        f.write(chapter_content)

    # Copy global.yaml to context/
    shutil.copy(
        template_dir / 'global.yaml',
        os.path.join(project_dir, 'context', 'global.yaml')
    )

    # Copy default.css to assets/css/
    shutil.copy(
        resources_dir / 'default.css',
        os.path.join(project_dir, 'assets', 'css', 'custom.css')
    )

    # Create .ebk marker file
    with open(os.path.join(project_dir, '.ebk'), 'w') as f:
        f.write('')  # Empty marker file


def create_new_book(book_name):
    """Create a new ebk project directory with all scaffolding."""
    if not book_name or not book_name.strip():
        raise ValueError("Book name cannot be empty")

    book_name = book_name.strip()
    slug = slugify(book_name)

    if not slug:
        raise ValueError(f"Invalid book name: '{book_name}'")

    # Create project directory
    project_dir = os.path.join(os.getcwd(), slug)

    if os.path.exists(project_dir):
        raise FileExistsError(f"Directory '{slug}' already exists")

    print(f"Creating new book: {book_name}")
    print(f"  Directory: {project_dir}")

    # Create directory structure
    os.makedirs(project_dir)
    create_directory_structure(project_dir)

    # Copy and populate templates
    copy_and_populate_templates(project_dir, book_name)

    print("  ✓ Created directory structure")
    print("  ✓ Initialized book.yaml")
    print("  ✓ Added sample content")
    print()
    print("Next steps:")
    print(f"  1. cd {slug}")
    print("  2. Edit book.yaml with your book metadata")
    print("  3. Add your content to content/")
    print("  4. Run 'ebk' to build your book")
