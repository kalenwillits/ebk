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
    """
    No directory structure created - ebk works recursively.

    ebk finds your content by file extension, not directory location,
    so organize your files however you prefer.
    """
    # No longer creating subdirectories
    pass


def copy_and_populate_templates(project_dir, book_name):
    """Copy essential template files and populate variables."""
    template_dir = get_template_path()

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

    # Copy and populate config.yaml
    with open(template_dir / 'config.yaml', 'r') as f:
        book_yaml_content = f.read()

    for var, value in template_vars.items():
        book_yaml_content = book_yaml_content.replace(f'{{{var}}}', value)

    with open(os.path.join(project_dir, 'config.yaml'), 'w') as f:
        f.write(book_yaml_content)

    # Create .ebk marker file
    with open(os.path.join(project_dir, '.ebk'), 'w') as f:
        f.write(f"# ebk project: {book_name}\n")  # Marker file with comment


def create_new_book(project_path):
    """
    Create a new ebk project at the given path.

    Supports:
    - Current directory: '.'
    - Absolute paths: '/home/user/my-book' or '~/books/novel'
    - Relative paths: 'my-book' or '../other-book'
    - Existing directories (will add .ebk marker and config.yaml)

    Args:
        project_path: Path where the project should be created (can be name or path)
    """
    if not project_path or not project_path.strip():
        raise ValueError("Project path cannot be empty")

    project_path = project_path.strip()

    # Expand user home directory and resolve to absolute path
    path = Path(project_path).expanduser().resolve()

    # Determine book name from path or use provided name
    if project_path in ['.', './']:
        # Use current directory name as book name
        book_name = path.name
    else:
        # Use the last component of the path as book name
        book_name = path.name

    # Create directory if it doesn't exist
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
            print(f"Creating new book: {book_name}")
            print(f"  Created directory: {path}")
        except Exception as e:
            raise OSError(f"Could not create directory '{path}': {e}")
    else:
        print(f"Creating new book: {book_name}")
        print(f"  Using existing directory: {path}")

    # Check if already an ebk project
    marker_file = path / ".ebk"
    if marker_file.exists():
        raise FileExistsError(f"Directory is already an ebk project")

    # Copy and populate templates (creates .ebk marker)
    copy_and_populate_templates(str(path), book_name)

    print("  ✓ Initialized ebk project")
    print("  ✓ Created config.yaml")
    print()
    print("Project ready! ebk works recursively, so organize your files however you prefer.")
    print("Next steps:")
    print(f"  1. cd {path.name if path != Path.cwd() else '.'}")
    print("  2. Edit config.yaml with your book metadata")
    print("  3. Add markdown files anywhere in the project")
    print("  4. Run 'ebk' to build your book")
