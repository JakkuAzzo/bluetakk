#!/usr/bin/env bash
set -euo pipefail

# Create a Python virtual environment if it doesn't exist
env_dir=".venv"
if [ ! -d "$env_dir" ]; then
    python3 -m venv "$env_dir"
fi

# Activate the environment
source "$env_dir/bin/activate"

# Generate requirements without macOS-specific PyObjC packages
req_file="$env_dir/test_requirements.txt"
grep -v '^pyobjc' requirements.txt > "$req_file"

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r "$req_file"

echo "Environment ready. Activate with 'source $env_dir/bin/activate' and run 'pytest'."
