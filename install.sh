#!/bin/bash
# install.sh - Install ebk to system using venv

set -e

INSTALL_DIR="/usr/local/bin"
VENV_DIR="venv"

echo "Installing ebk..."

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -e .

# Create wrapper script in /usr/local/bin
echo "Creating system-wide command..."
sudo tee "$INSTALL_DIR/ebk" > /dev/null << EOF
#!/bin/bash
# ebk wrapper script
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$PWD"
source "\$PROJECT_DIR/$VENV_DIR/bin/activate"
python3 -m src.cli "\$@"
EOF

sudo chmod +x "$INSTALL_DIR/ebk"

echo ""
echo "Installation complete!"
echo "Run 'ebk --help' to get started."
