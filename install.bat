@echo off
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install --no-build-isolation .

echo Installation terminee. Lancez avec: .venv\Scripts\activate && stock-desktop
