#!/bin/bash
# build.sh - Build ebk binary with PyInstaller

set -e

echo "Building ebk CLI..."

# Clean previous builds
rm -rf build/ dist/

# Create virtual environment if needed
if [ ! -d "venv" ] || [ ! -f "venv/bin/pip" ]; then
    echo "Creating virtual environment..."
    rm -rf venv  # Clean up any partial venv
    python3 -m venv venv

    # Verify venv was created successfully
    if [ ! -f "venv/bin/pip" ]; then
        echo "Error: Failed to create virtual environment"
        echo "Please ensure python3-venv is installed: sudo apt install python3-venv"
        exit 1
    fi
fi

# Install dependencies using venv's pip
echo "Installing dependencies..."
./venv/bin/pip install -q -r requirements.txt

# Run tests using venv's pytest
echo "Running tests..."
./venv/bin/pytest tests/ -v

# Run PyInstaller using venv's pyinstaller
echo "Running PyInstaller..."
./venv/bin/pyinstaller ebk.spec

echo ""
echo "Build complete!"
echo "Binary location: dist/ebk"
echo ""
echo "Test with: ./dist/ebk --help"
