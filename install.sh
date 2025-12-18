#!/bin/bash
# install.sh - Install ebk to system

set -e

INSTALL_DIR="/usr/local/bin"
BINARY="dist/ebk"

if [ ! -f "$BINARY" ]; then
    echo "Error: Binary not found at $BINARY"
    echo "Run ./build.sh first to build the binary."
    exit 1
fi

echo "Installing ebk to $INSTALL_DIR..."

# Copy binary
sudo cp "$BINARY" "$INSTALL_DIR/ebk"
sudo chmod +x "$INSTALL_DIR/ebk"

echo ""
echo "Installation complete!"
echo "Run 'ebk --help' to get started."
