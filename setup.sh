#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Upgrading pip..."
.venv/bin/pip install --upgrade pip

echo "Installing dependencies..."
.venv/bin/pip install -r requirements.txt

echo ""
echo "Done."
echo "Activate with: source .venv/bin/activate"
echo "Run server:    .venv/bin/python server.py"
