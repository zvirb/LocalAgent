#!/bin/bash
# LocalAgent Simple CLI Launcher - Works from anywhere

# Get the actual location of this script (following symlinks)
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment and run the CLI
source "$PROJECT_ROOT/.venv/bin/activate"
exec python3 "$PROJECT_ROOT/scripts/localagent_interactive_simple.py" "$@"