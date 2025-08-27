#!/bin/bash
# LocalAgent CLI Environment Activation
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_ROOT/.venv/bin/activate"
echo "LocalAgent CLI environment activated!"
echo "Available commands: localagent, la"
echo "Try: localagent --help"
