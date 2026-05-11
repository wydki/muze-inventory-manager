from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
import json
from pathlib import Path
import uuid
import re
from datetime import datetime


@dataclass
class Book:
    isbn: Optional[str] = ""
    title: str = ""
    author: str = ""
    book_type: str = "Paperback"  # 'paperback' or 'hardcover'
    quantity: int = 0
    batch_id: str = ""
    batch_source: str = ""  # batch name/ID that this item came from


class StockManager:
    def __init__(self, data_file: Optional[str] = None):
        self.data_file = Path(data_file) if data_file else (Path(__file__).resolve().parents[1] / "data" / "books.json")
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.books: Dict[str, Book] = {}
        # batches stored in sibling file 'batches.json'
        self.batches_file = self.data_file.parent / "batches.json"
        self.batches: Dict[str, dict] = {}
        # requests (wishlist) stored in 'requests.json'
        self.requests_file = self.data_file.parent / "requests.json"
        self.requests: List[dict] = []
        # shipments stored in 'shipments.json' (list of batch IDs in shipment)
        self.shipments_file = self.data_file.parent / "shipments.json"
        self.shipments: List[str] = []
        self.load()

    # Batch helpers
    def create_batch(self, name: Optional[str] = None) -> str:
        # if no name provided, generate sequential "Batch N" name
        if not name or not name.strip():
            # find existing Batch numbers
            max_n = 0
            for b in self.batches.values():
                m = re.match(r"^Batch(?:\s*(\d+))?$", b.get("name", ""))
                if m:
                    try:
                        num = int(m.group(1)) if m.group(1) else 1
                        if num > max_n:
                            max_n = num
                    except Exception:
                        pass
            next_n = max_n + 1 if max_n else 1
            name = f"Batch {next_n}"
        batch_id = str(uuid.uuid4())
        self.batches[batch_id] = {"id": batch_id, "name": name, "items": [], "committed": False}
        self._save_batches()
        return batch_id

    def list_batches(self) -> List[dict]:
        return list(self.batches.values())

    def add_item_to_batch(self, batch_id: str, title: str, book_type: str, quantity: int = 1) -> bool:
        if batch_id not in self.batches:
            return False
        self.batches[batch_id]["items"].append({"title": title, "book_type": book_type, "quantity": quantity})
        self._save_batches()
        return True

    def get_batch_items(self, batch_id: str) -> List[dict]:
        return self.batches.get(batch_id, {}).get("items", [])

    def remove_item_from_batch(self, batch_id: str, item_index: int) -> bool:
        if batch_id not in self.batches:
            return False
        items = self.batches[batch_id].get("items", [])
        if 0 <= item_index < len(items):
            items.pop(item_index)
            self._save_batches()
            return True
        return False

    def commit_batch(self, batch_id: str) -> bool:
        """Add all items in the batch to stock and mark batch as committed."""
        if batch_id not in self.batches:
            return False
        batch_name = self.batches[batch_id].get("name", "Unknown")
        for it in list(self.batches[batch_id]["items"]):
            title = it.get("title", "")
            book_type = it.get("book_type", "paperback")
            qty = int(it.get("quantity", 0))
            if title and qty:
                # keep committed stock separate by batch_id, even if title/type matches another batch
                key = self._match_key(None, title, book_type, batch_id=batch_id)
                if key in self.books:
                    self.books[key].quantity += qty
                else:
                    self.books[key] = Book(
                        isbn="",
                        title=title,
                        author="",
                        book_type=book_type,
                        quantity=qty,
                        batch_id=batch_id,
                        batch_source=batch_name,
                    )
        # mark batch as committed instead of deleting
        self.batches[batch_id]["committed"] = True
        self._save_batches()
        self.save()
        return True

    def remove_batch(self, batch_id: str) -> bool:
        if batch_id in self.batches:
            del self.batches[batch_id]
            self._save_batches()
            return True
        return False

    def clear_stock(self) -> None:
        """Remove all books from stock and persist the empty store."""
        self.books = {}
        self.save()

    def clear_batches(self) -> None:
        """Remove all batches and persist."""
        self.batches = {}
        self._save_batches()

    # Request (wishlist) helpers
    def add_request(self, title: str, book_type: str) -> None:
        """Add a request (wishlist item) by title+type."""
        self.requests.append({"title": title, "book_type": book_type})
        self._save_requests()

    def list_requests(self) -> List[dict]:
        return list(self.requests)

    def remove_request(self, index: int) -> bool:
        """Remove a request by index."""
        if 0 <= index < len(self.requests):
            self.requests.pop(index)
            self._save_requests()
            return True
        return False

    def get_latest_batch(self) -> Optional[str]:
        """Get the ID of the most recently created batch, or None."""
        if not self.batches:
            return None
        # dicts preserve insertion order, so the last key is the newest batch
        return next(reversed(self.batches.keys()))

    def _save_requests(self) -> None:
        try:
            with open(self.requests_file, "w", encoding="utf-8") as f:
                json.dump(self.requests, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # Shipment helpers
    def add_to_shipment(self, batch_id: str) -> bool:
        """Mark a batch as in shipment with NOT SHIPPED status."""
        if batch_id in self.batches:
            # check if already in shipments
            for ship in self.shipments:
                if ship.get("batch_id") == batch_id:
                    return False  # already exists
            self.shipments.append({"batch_id": batch_id, "status": "NOT SHIPPED"})
            self._save_shipments()
            return True
        return False

    def list_shipments(self) -> List[dict]:
        """Get all batches currently in shipment with their status."""
        result = []
        for ship in self.shipments:
            bid = ship.get("batch_id")
            if bid in self.batches:
                batch = dict(self.batches[bid])
                batch["ship_status"] = ship.get("status", "NOT SHIPPED")
                result.append(batch)
        return result

    def update_shipment_status(self, batch_id: str, status: str) -> bool:
        """Update shipment status: NOT SHIPPED, SHIPPED OUT, RECEIVED."""
        for ship in self.shipments:
            if ship.get("batch_id") == batch_id:
                ship["status"] = status
                self._save_shipments()
                return True
        return False

    def remove_from_shipment(self, batch_id: str) -> bool:
        """Remove a batch from shipment tracking."""
        self.shipments = [s for s in self.shipments if s.get("batch_id") != batch_id]
        self._save_shipments()
        return True

    def _save_shipments(self) -> None:
        try:
            with open(self.shipments_file, "w", encoding="utf-8") as f:
                json.dump(self.shipments, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def archive_stock(self, clear_after: bool = False) -> str:
        """Archive current books and batches to an `archives/` folder with timestamped filename.

        If `clear_after` is True, clears books and batches after archiving.
        Returns the archive file path as string.
        """
        archives_dir = self.data_file.parent / "archives"
        archives_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "books": [asdict(b) for b in self.books.values()],
            "batches": list(self.batches.values()),
            "archived_at": datetime.utcnow().isoformat() + "Z",
        }
        fname = archives_dir / f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        if clear_after:
            self.clear_stock()
            self.clear_batches()

        return str(fname)

    def _match_key(self, isbn: Optional[str], title: Optional[str], book_type: Optional[str], batch_id: Optional[str] = None) -> str:
        """Create an internal dict key. Prefer ISBN, then batch-specific stock, then title+type."""
        if isbn:
            return isbn
        if batch_id:
            assert title is not None and book_type is not None
            return f"batch::{batch_id}::title::{title.strip().lower()}::type::{book_type.strip().lower()}"
        assert title is not None and book_type is not None
        return f"title::{title.strip().lower()}::type::{book_type.strip().lower()}"

    def add_book(self, isbn: Optional[str], title: str, author: str = "", book_type: str = "paperback", quantity: int = 1) -> None:
        key = self._match_key(isbn, title, book_type)
        if key in self.books:
            self.books[key].quantity += quantity
        else:
            self.books[key] = Book(isbn=isbn or "", title=title, author=author, book_type=book_type, quantity=quantity)
        self.save()

    def add_by_title(self, title: str, book_type: str, quantity: int = 1) -> None:
        """Add stock by title+type. If same title+type exists, increment its quantity."""
        # try to find existing book with same title and type
        for key, b in self.books.items():
            if b.title.strip().lower() == title.strip().lower() and b.book_type.strip().lower() == book_type.strip().lower():
                b.quantity += quantity
                self.save()
                return
        # create new
        key = self._match_key(None, title, book_type)
        self.books[key] = Book(isbn="", title=title, author="", book_type=book_type, quantity=quantity)
        self.save()

    def _save_batches(self) -> None:
        try:
            with open(self.batches_file, "w", encoding="utf-8") as f:
                json.dump(list(self.batches.values()), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def remove_book(self, isbn: str) -> bool:
        if isbn in self.books:
            del self.books[isbn]
            self.save()
            return True
        return False

    def update_quantity(self, isbn: str, quantity: int) -> bool:
        if isbn in self.books:
            self.books[isbn].quantity = quantity
            self.save()
            return True
        return False

    def list_books(self) -> List[Book]:
        return list(self.books.values())

    def search(self, q: str) -> List[Book]:
        q = q.lower()
        return [b for b in self.books.values() if q in b.title.lower() or q in b.author.lower() or q in (b.isbn or "").lower()]

    def save(self) -> None:
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump([asdict(b) for b in self.books.values()], f, ensure_ascii=False, indent=2)
        # also save batches
        self._save_batches()

    def load(self) -> None:
        if not self.data_file.exists():
            self.books = {}
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                arr = json.load(f)
                books: Dict[str, Book] = {}
                for item in arr:
                    # ensure keys exist for backwards compatibility
                    isbn = item.get("isbn", "")
                    title = item.get("title", "")
                    author = item.get("author", "")
                    book_type = item.get("book_type", item.get("type", "paperback"))
                    quantity = item.get("quantity", 0)
                    batch_id = item.get("batch_id", "")
                    batch_source = item.get("batch_source", "")
                    # choose key
                    if isbn:
                        key = isbn
                    elif batch_id:
                        key = f"batch::{batch_id}::title::{title.strip().lower()}::type::{book_type.strip().lower()}"
                    else:
                        key = f"title::{title.strip().lower()}::type::{book_type.strip().lower()}"
                    books[key] = Book(
                        isbn=isbn,
                        title=title,
                        author=author,
                        book_type=book_type,
                        quantity=quantity,
                        batch_id=batch_id,
                        batch_source=batch_source,
                    )
                self.books = books
            # load batches if present
            try:
                if self.batches_file.exists():
                    with open(self.batches_file, "r", encoding="utf-8") as bf:
                        barr = json.load(bf)
                        self.batches = {item.get("id", str(uuid.uuid4())): item for item in barr}
                else:
                    self.batches = {}
            except Exception:
                self.batches = {}

            # Backfill batch_source for older saved books that do not have it yet.
            if self.books and self.batches:
                batch_lookup = {}
                for batch in self.batches.values():
                    batch_name = batch.get("name", "")
                    batch_id = batch.get("id", "")
                    if batch_id:
                        batch_lookup[batch_name] = batch_id

                updated = False
                for book in self.books.values():
                    if not book.batch_id and book.batch_source:
                        inferred_batch_id = batch_lookup.get(book.batch_source, "")
                        if inferred_batch_id:
                            book.batch_id = inferred_batch_id
                            updated = True

                if updated:
                    self.save()

            # load requests if present
            try:
                if self.requests_file.exists():
                    with open(self.requests_file, "r", encoding="utf-8") as rf:
                        self.requests = json.load(rf)
                else:
                    self.requests = []
            except Exception:
                self.requests = []
            # load shipments if present
            try:
                if self.shipments_file.exists():
                    with open(self.shipments_file, "r", encoding="utf-8") as sf:
                        data = json.load(sf)
                        # handle both old format (list of strings) and new format (list of dicts)
                        if data and isinstance(data[0], str):
                            # migrate old format to new
                            self.shipments = [{"batch_id": bid, "status": "NOT SHIPPED"} for bid in data]
                            self._save_shipments()
                        else:
                            self.shipments = data
                else:
                    self.shipments = []
            except Exception:
                self.shipments = []
        except Exception:
            self.books = {}
