# Stock Desktop

Application desktop complète de gestion de stock, basée sur **Python + Tkinter + SQLite**.

## Fonctionnalités

- Gestion des produits (CRUD): ajout, modification, suppression.
- Gestion des stocks: entrées/sorties avec validation des quantités.
- Alertes de stock bas (stock <= seuil minimal).
- Recherche multi-critères (SKU, nom, catégorie).
- Export CSV de l'inventaire filtré.
- Base de données SQLite locale créée automatiquement (`stock_manager.db`).

## Installation rapide (Linux/macOS)

```bash
./install.sh
source .venv/bin/activate
stock-desktop
```

## Installation rapide (Windows)

```bat
install.bat
.venv\Scripts\activate
stock-desktop
```

## Développement

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install --no-build-isolation -e .
pytest
python -m stock_app
```

## Générer un exécutable installable

### Linux/macOS

```bash
./build_executable.sh
```

Le binaire est généré dans `dist/StockDesktop`.

### Windows

Vous pouvez lancer l'équivalent avec PyInstaller:

```bat
pyinstaller --name StockDesktop --windowed --onefile -m stock_app
```

## Structure

- `src/stock_app/db.py`: couche SQLite et logique métier stock.
- `src/stock_app/app.py`: interface graphique Tkinter.
- `tests/test_db.py`: tests unitaires sur les opérations critiques.


## Étapes pour un runner (CI/CD ou VM)

Exemple de séquence minimale pour exécuter les vérifications sur un runner Linux:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m py_compile src/stock_app/*.py tests/test_db.py
```

Pour lancer l’application dans le runner:

```bash
PYTHONPATH=src python -m stock_app
```

