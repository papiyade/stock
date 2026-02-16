#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install --no-build-isolation .

pyinstaller --name StockDesktop --windowed --onefile -m stock_app

echo "Binaire généré dans dist/StockDesktop"
