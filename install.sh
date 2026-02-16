#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --no-build-isolation .

echo "Installation terminée. Lancez avec: source .venv/bin/activate && stock-desktop"
