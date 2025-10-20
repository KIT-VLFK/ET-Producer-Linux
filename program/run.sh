#!/bin/bash
# ET-Producer Launcher for Linux

# Get the parent directory (go up from program/ to root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Install dependencies if needed
python3 -c "import customtkinter" 2>/dev/null || pip3 install customtkinter python-magic

# Run application
cd "$SCRIPT_DIR/src"
python3 ET_Producer.py
