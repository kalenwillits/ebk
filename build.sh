#!/bin/bash
# build.sh - Build ebk binary with PyInstaller

set -e

echo "Building ebk CLI..."

# Clean previous builds
rm -rf build/ dist/

# Create/activate virtual environment if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run PyInstaller
echo "Running PyInstaller..."
pyinstaller ebk.spec

echo ""
echo "Build complete!"
echo "Binary location: dist/ebk"
echo ""
echo "Test with: ./dist/ebk --version"
