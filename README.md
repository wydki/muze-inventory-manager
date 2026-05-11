# Bookstocker

Bookstocker is a Python-based book inventory manager specifically made for my Girlfriend with a GUI, batch tracking, wishlist handling, shipment status updates, and JSON persistence.

## What This Project Includes

- Home dashboard with inventory totals
- Requested books list
- Batch creation, commit, and item removal
- In-shipment tracking with status updates
- Overall inventory view grouped by batch
- JSON persistence for books, batches, requests, and shipments
- Tkinter GUI and a ttkbootstrap dashboard demo

## Requirements

- Python 3.11 or newer recommended
- `ttkbootstrap`
- `Pillow`
- `pytest` if you want to run tests

## Setup

Install dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

If you are using a virtual environment and PowerShell blocks script activation, you can run the venv Python directly:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Run The App

Launch the main Bookstocker GUI:

```bash
python -m Bookstocker
```

Run the ttkbootstrap dashboard demo:

```bash
python dashboard_ttk.py
```


## Data Files

The app stores its data in the `data/` folder:

- `data/books.json`
- `data/batches.json`
- `data/requests.json`
- `data/shipments.json`
- `data/archives/`

These files are created automatically when you use the app.

## Project Layout

- `stock_manager/manager.py` - core inventory and persistence logic
- `gui.py` - main Tkinter GUI
- `dashboard_ttk.py` - ttkbootstrap dashboard demo
- `cli.py` - command-line interface
- `tests/` - automated tests
- `tools/generate_placeholders.py` - creates placeholder UI images

## Notes

- The dashboard demo uses images in `assets/buttons/` for the sidebar button art.
- If you update the assets, restart the app to reload them.
- If you want to run tests, use:

```bash
pytest
```
