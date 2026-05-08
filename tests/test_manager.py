import tempfile
import json
from stock_manager import StockManager


def test_add_and_persist(tmp_path):
    data = tmp_path / "books.json"
    mgr = StockManager(data_file=str(data))
    mgr.add_by_title("My Book", "paperback", 2)
    # find by title
    found = [b for b in mgr.list_books() if b.title == "My Book"]
    assert len(found) == 1
    # reload from disk
    mgr2 = StockManager(data_file=str(data))
    assert "123" in mgr2.books


def test_update_and_remove(tmp_path):
    data = tmp_path / "books.json"
    mgr = StockManager(data_file=str(data))
    mgr.add_by_title("BatchBook", "hardcover", 1)
    # add more
    mgr.add_by_title("BatchBook", "hardcover", 4)
    found = [b for b in mgr.list_books() if b.title == "BatchBook"]
    assert found and found[0].quantity == 5
    # remove by key: find internal key then remove
    key = None
    for k, v in mgr.books.items():
        if v.title == "BatchBook":
            key = k
            break
    assert key is not None
    assert mgr.remove_book(key)
    assert all(b.title != "BatchBook" for b in mgr.list_books())
