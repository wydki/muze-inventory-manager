import argparse
from .stock_manager import StockManager


def main():
    parser = argparse.ArgumentParser(prog="bookstocker", description="Manage book stock")
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Add a book or increase quantity")
    p_add.add_argument("--isbn", required=True)
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--author", required=True)
    p_add.add_argument("--qty", type=int, default=1)

    p_remove = sub.add_parser("remove", help="Remove a book by ISBN")
    p_remove.add_argument("--isbn", required=True)

    p_update = sub.add_parser("update", help="Set exact quantity for ISBN")
    p_update.add_argument("--isbn", required=True)
    p_update.add_argument("--qty", type=int, required=True)

    p_list = sub.add_parser("list", help="List all books")

    p_search = sub.add_parser("search", help="Search books by title/author/isbn")
    p_search.add_argument("--q", required=True)

    args = parser.parse_args()
    mgr = StockManager()

    if args.cmd == "add":
        mgr.add_book(args.isbn, args.title, args.author, args.qty)
        print(f"Added/updated {args.isbn}: {args.title} ({args.qty})")
    elif args.cmd == "remove":
        ok = mgr.remove_book(args.isbn)
        print("Removed" if ok else "Not found")
    elif args.cmd == "update":
        ok = mgr.update_quantity(args.isbn, args.qty)
        print("Updated" if ok else "Not found")
    elif args.cmd == "list":
        books = mgr.list_books()
        if not books:
            print("No books in stock")
            return
        for b in books:
            print(f"{b.isbn} | {b.title} | {b.author} | qty: {b.quantity}")
    elif args.cmd == "search":
        results = mgr.search(args.q)
        if not results:
            print("No matches")
            return
        for b in results:
            print(f"{b.isbn} | {b.title} | {b.author} | qty: {b.quantity}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
