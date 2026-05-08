<<<<<<< HEAD
# muze-inventory-manager
Book Inventory Manager for Amuze
=======
Bookstocker
=============

Simple Book Stock Manager (CLI + JSON persistence).

Requirements
- Python 3.8+
- (optional) `pytest` to run tests

Quick start

Install deps (optional):

```bash
python -m pip install -r requirements.txt
```

Run CLI:

```bash
python -m Bookstocker.cli add --isbn 9780143127741 --title "Sapiens" --author "Yuval Noah Harari" --qty 3
python -m Bookstocker.cli list
python -m Bookstocker.cli search --q sapiens
```

Project layout

- `stock_manager/manager.py`: core logic
- `cli.py`: command-line interface
- `data/books.json`: persisted store (created on demand)
>>>>>>> 8792a71 (Initial commit for Muze Inventory Manager UI updates)
