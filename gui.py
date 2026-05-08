import tkinter as tk
from tkinter import ttk, messagebox
from .stock_manager import StockManager


class BookstockerApp(tk.Tk):
    def __init__(self, data_file: str = None):
        super().__init__()
        self.title("Bookstocker")
        self.state('zoomed')  # full screen on Windows
        self.mgr = StockManager(data_file=data_file) if data_file else StockManager()

        # Layout frames
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self, width=200, bg="#f0f0f0")
        self.sidebar.grid(row=0, column=0, sticky="nswe")

        # App title at top-left
        title_label = tk.Label(self.sidebar, text="Amuze Inventory Manager", bg="#f0f0f0", font=(None, 12, 'bold'), anchor="w")
        title_label.pack(fill="x", padx=8, pady=8)

        self.content = tk.Frame(self)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(1, weight=1)

        # Sidebar buttons
        btns = [
            ("Home", self.show_home),
            ("Requests", self.show_requests),
            ("In Shipment", self.show_in_shipment),
            ("Batches", self.show_batches),
            ("Overall Books in Stock", self.show_overall),
        ]

        for i, (label, cmd) in enumerate(btns):
            b = tk.Button(self.sidebar, text=label, command=cmd, anchor="w")
            b.pack(fill="x", padx=8, pady=(6 if i == 0 else 4))

        # Archive and Clear stock buttons at the bottom-left
        def on_archive():
            if not messagebox.askyesno("Archive", "Archive current stock and batches?"):
                return
            clear_after = messagebox.askyesno("Also Clear", "Also clear stock and batches after archiving?")
            path = self.mgr.archive_stock(clear_after=clear_after)
            messagebox.showinfo("Archived", f"Archived to: {path}")
            # refresh view
            self.show_overall()

        tk.Button(self.sidebar, text="Archive Stock", command=on_archive).pack(side="bottom", fill="x", padx=8, pady=4)

        def on_clear_stock():
            if messagebox.askyesno("Confirm", "Are you sure you want to clear all stock?"):
                self.mgr.clear_stock()
                self.mgr.clear_batches()
                messagebox.showinfo("Cleared", "All stock and batches cleared")
                self.show_overall()

        tk.Button(self.sidebar, text="Clear Stock", command=on_clear_stock, fg="red").pack(side="bottom", fill="x", padx=8, pady=8)

        # Start with home view
        self.current_tree = None
        self.show_home()

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()
        self.current_tree = None

    def make_tree(self, columns, headings):
        tree = ttk.Treeview(self.content, columns=columns, show="headings")
        for col, hd in zip(columns, headings):
            tree.heading(col, text=hd)
            tree.column(col, anchor="w")
        tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        # add scrollbar
        sb = ttk.Scrollbar(self.content, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.grid(row=1, column=1, sticky="ns")
        self.current_tree = tree
        return tree

    def show_home(self):
        self.clear_content()
        lbl = tk.Label(self.content, text="Home", font=(None, 16, 'bold'))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        stats_frame = tk.Frame(self.content)
        stats_frame.grid(row=1, column=0, sticky="nw", padx=16, pady=8)

        # compute stats
        total_books = 0
        for b in self.mgr.list_books():
            try:
                total_books += int(b.quantity)
            except Exception:
                pass

        batches = self.mgr.list_batches()
        total_batches = len(batches)
        committed = sum(1 for b in batches if b.get("committed"))
        pending = total_batches - committed

        total_shipments = len(self.mgr.list_shipments())
        total_requests = len(self.mgr.list_requests())

        tk.Label(stats_frame, text=f"Total books in stock: {total_books}", font=(None, 12)).pack(anchor="w", pady=4)
        tk.Label(stats_frame, text=f"Total batches: {total_batches} (Committed: {committed}, Pending: {pending})", font=(None, 12)).pack(anchor="w", pady=4)
        tk.Label(stats_frame, text=f"Batches in shipment: {total_shipments}", font=(None, 12)).pack(anchor="w", pady=4)
        tk.Label(stats_frame, text=f"Wishlist requests: {total_requests}", font=(None, 12)).pack(anchor="w", pady=4)

        # Quick actions
        actions = tk.Frame(self.content)
        actions.grid(row=2, column=0, sticky="w", padx=16, pady=12)
        tk.Button(actions, text="View Batches", command=self.show_batches).pack(side="left", padx=6)
        tk.Button(actions, text="View Overall Stock", command=self.show_overall).pack(side="left", padx=6)
        tk.Button(actions, text="View Requests", command=self.show_requests).pack(side="left", padx=6)

    def show_overall(self):
        self.clear_content()
        lbl = tk.Label(self.content, text="Overall Books in Stock", font=(None, 14))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        cols = ("name",)
        tree = self.make_tree(cols, ("Batch / Book",))
        tree.column("name", width=400)
        
        # Group books by batch_id so identical books from different batches stay separate
        books_by_batch = {}
        grand_total = 0
        for b in self.mgr.list_books():
            batch_id = getattr(b, "batch_id", "")
            batch_name = getattr(b, "batch_source", "")
            if not batch_id and not batch_name:
                continue
            group_key = batch_id or batch_name
            if group_key not in books_by_batch:
                books_by_batch[group_key] = {"name": batch_name or group_key, "books": []}
            books_by_batch[group_key]["books"].append(b)
            try:
                grand_total += int(b.quantity)
            except Exception:
                pass

        # Display message if no books
        if not books_by_batch:
            tk.Label(tree, text="No books in stock. Create and commit batches to add books.").pack(anchor="w")
        else:
            # Display batches in order with expandable books
            for group_key in sorted(books_by_batch.keys(), key=lambda x: books_by_batch[x]["name"].lower()):
                batch_info = books_by_batch[group_key]
                batch_name = batch_info["name"]
                books = batch_info["books"]
                batch_qty = sum(int(b.quantity) for b in books)
                batch_id = tree.insert("", "end", values=(f"{batch_name} (Total: {batch_qty})",))
                # Add books sorted alphabetically
                for book in sorted(books, key=lambda x: x.title.lower()):
                    tree.insert(batch_id, "end", values=(f"  • {book.title} ({book.book_type}) - {book.quantity}",))

        # bottom-right small popup showing total books
        total_frame = tk.Frame(self.content)
        total_frame.grid(row=2, column=0, sticky="se", padx=8, pady=8)
        total_label = tk.Label(total_frame, text=f"Total books in stock: {grand_total}", bg="#ffffe0", relief="solid", padx=8, pady=4)
        total_label.pack()

    def show_requests(self):
        self.clear_content()
        lbl = tk.Label(self.content, text="Requests (Wishlist)", font=(None, 14))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        # Form to add requests
        form = tk.Frame(self.content)
        form.grid(row=1, column=0, sticky="nw", padx=8, pady=8)

        tk.Label(form, text="Title:").grid(row=0, column=0, sticky="w")
        title_var = tk.StringVar()
        tk.Entry(form, textvariable=title_var, width=40).grid(row=0, column=1, sticky="w", padx=4)

        tk.Label(form, text="Type:").grid(row=1, column=0, sticky="w")
        type_var = tk.StringVar(value="paperback")
        type_cb = ttk.Combobox(form, textvariable=type_var, values=("paperback", "hardcover"), state="readonly", width=20)
        type_cb.grid(row=1, column=1, sticky="w", padx=4)

        def on_add_request():
            title = title_var.get().strip()
            btype = type_var.get().strip()
            if not title:
                messagebox.showerror("Invalid", "Title is required")
                return
            self.mgr.add_request(title=title, book_type=btype)
            title_var.set("")
            type_var.set("paperback")
            refresh_requests()

        tk.Button(form, text="Add Request", command=on_add_request).grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        # Requests list with checkmark/delete buttons
        list_frame = tk.Frame(self.content)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        tk.Label(list_frame, text="Wishlist:").pack(anchor="w")
        requests_frame = tk.Frame(list_frame)
        requests_frame.pack(fill="both", expand=True)

        def refresh_requests():
            # clear all children in requests_frame
            for w in requests_frame.winfo_children():
                w.destroy()
            # add each request as a row, sorted alphabetically but preserving original indices
            sorted_requests = sorted(
                enumerate(self.mgr.list_requests()),
                key=lambda pair: pair[1].get('title', '').lower(),
            )
            for idx, req in sorted_requests:
                row = tk.Frame(requests_frame)
                row.pack(fill="x", pady=2)
                
                # Title + Type label
                title_text = f"{req['title']} ({req['book_type']})"
                tk.Label(row, text=title_text, anchor="w").pack(side="left", fill="x", expand=True)

                # Checkmark button (add to latest batch)
                def on_checkmark(req=req):
                    # get latest batch
                    batch_id = self.mgr.get_latest_batch()
                    if not batch_id:
                        messagebox.showerror("No Batch", "No batch created yet. Create a batch first.")
                        return
                    # ask for quantity
                    qty_dialog = tk.Toplevel(self)
                    qty_dialog.title("Enter Quantity")
                    qty_dialog.geometry("300x100")
                    tk.Label(qty_dialog, text="How many copies?").pack(pady=8)
                    qty_var = tk.IntVar(value=1)
                    tk.Entry(qty_dialog, textvariable=qty_var, width=10).pack(pady=4)

                    def on_ok():
                        try:
                            qty = int(qty_var.get())
                        except Exception:
                            messagebox.showerror("Invalid", "Quantity must be integer")
                            return
                        if qty <= 0:
                            messagebox.showerror("Invalid", "Quantity must be > 0")
                            return
                        # check if item already in batch
                        batch = self.mgr.batches.get(batch_id, {})
                        found = False
                        for item in batch.get("items", []):
                            if item["title"].lower() == req["title"].lower() and item["book_type"].lower() == req["book_type"].lower():
                                # increment quantity
                                item["quantity"] += qty
                                found = True
                                break
                        if not found:
                            # add new item
                            self.mgr.add_item_to_batch(batch_id, req["title"], req["book_type"], qty)
                        else:
                            # save updated batch
                            self.mgr._save_batches()
                        messagebox.showinfo("Added", f"Added {qty}x '{req['title']}' to batch")
                        qty_dialog.destroy()
                        self.show_requests()  # refresh

                    tk.Button(qty_dialog, text="OK", command=on_ok).pack(pady=4)

                tk.Button(row, text="✓", width=3, command=on_checkmark).pack(side="right", padx=2)

                # Delete button
                def on_delete(idx=idx):
                    self.mgr.remove_request(idx)
                    refresh_requests()

                tk.Button(row, text="✕", width=3, fg="red", command=on_delete).pack(side="right", padx=2)

        refresh_requests()

    def show_in_shipment(self):
        self.clear_content()
        lbl = tk.Label(self.content, text="In Shipment", font=(None, 14))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        # Frame to display batches with shipment status
        list_frame = tk.Frame(self.content)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        tk.Label(list_frame, text="Batch Status:").pack(anchor="w", pady=(0, 8))
        
        batches_container = tk.Frame(list_frame)
        batches_container.pack(fill="both", expand=True)

        def refresh_shipments():
            # clear container
            for w in batches_container.winfo_children():
                w.destroy()
            
            shipment_batches = self.mgr.list_shipments()
            all_committed = [b for b in self.mgr.list_batches() if b.get("committed")]
            
            if not all_committed:
                tk.Label(batches_container, text="No committed batches yet. Create and commit batches in the 'Batches' pane.").pack(anchor="w")
                return

            for batch in all_committed:
                bid = batch["id"]
                # find shipment status for this batch
                ship_status = None
                for ship in shipment_batches:
                    if ship["id"] == bid:
                        ship_status = ship.get("ship_status", "NOT SHIPPED")
                        break
                
                row = tk.Frame(batches_container)
                row.pack(fill="x", pady=4)
                
                # Batch name
                tk.Label(row, text=f"{batch['name']}", anchor="w", width=20).pack(side="left", padx=4)
                
                # Status indicator
                if ship_status:
                    status_color = "orange" if ship_status == "NOT SHIPPED" else ("green" if ship_status == "SHIPPED OUT" else "blue")
                    tk.Label(row, text=f"[{ship_status}]", fg=status_color, width=15).pack(side="left", padx=4)
                else:
                    tk.Label(row, text="[Not in Shipment]", fg="gray", width=15).pack(side="left", padx=4)

                # Right-aligned action area keeps the buttons in a fixed order
                actions = tk.Frame(row)
                actions.pack(side="right", padx=4)

                if not ship_status:
                    def on_add_to_shipment(bid=bid):
                        self.mgr.add_to_shipment(bid)
                        refresh_shipments()

                    tk.Button(actions, text="Mark as In Shipment", width=25, command=on_add_to_shipment).grid(row=0, column=0, padx=2)
                else:
                    def on_mark_shipped_out(bid=bid):
                        self.mgr.update_shipment_status(bid, "SHIPPED OUT")
                        refresh_shipments()

                    def on_mark_received(bid=bid):
                        self.mgr.update_shipment_status(bid, "RECEIVED")
                        refresh_shipments()

                    tk.Button(
                        actions,
                        text="Shipped Out",
                        width=12,
                        bg="#ef6c00",
                        fg="white",
                        activebackground="#e65100",
                        activeforeground="white",
                        command=on_mark_shipped_out,
                    ).grid(row=0, column=0, padx=2)
                    tk.Button(
                        actions,
                        text="Received",
                        width=12,
                        bg="#2e7d32",
                        fg="white",
                        activebackground="#1b5e20",
                        activeforeground="white",
                        command=on_mark_received,
                    ).grid(row=0, column=1, padx=2)
        
        refresh_shipments()

    def show_batches(self):
        self.clear_content()
        lbl = tk.Label(self.content, text="Batches", font=(None, 14))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)
        # Two-column layout: left for batches, right for batch details
        # ensure content columns allocate space appropriately
        self.content.columnconfigure(0, weight=1)
        self.content.columnconfigure(1, weight=3)

        left = tk.Frame(self.content)
        left.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        left.rowconfigure(1, weight=1)

        tk.Label(left, text="Batches:").grid(row=0, column=0, sticky="w")
        batch_listbox = tk.Listbox(left, width=30, height=12)
        batch_listbox.grid(row=1, column=0, sticky="nsew")
        lb_scroll = ttk.Scrollbar(left, orient="vertical", command=batch_listbox.yview)
        batch_listbox.configure(yscrollcommand=lb_scroll.set)
        lb_scroll.grid(row=1, column=1, sticky="ns")

        name_var = tk.StringVar()
        tk.Entry(left, textvariable=name_var, width=25).grid(row=2, column=0, sticky="w", pady=6)
        def on_create_batch():
            name_input = name_var.get().strip()
            # pass None to let manager auto-name sequential batches when empty
            bid = self.mgr.create_batch(name_input if name_input else None)
            refresh_batches()
            # select new batch
            for i, b in enumerate(self.mgr.list_batches()):
                if b["id"] == bid:
                    batch_listbox.selection_clear(0, "end")
                    batch_listbox.selection_set(i)
                    on_select_batch()
                    break

        tk.Button(left, text="Create Batch", command=on_create_batch).grid(row=3, column=0, sticky="w")
        def on_delete_batch():
            sel = batch_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            batches = self.mgr.list_batches()
            bid = batches[idx]["id"]
            if messagebox.askyesno("Delete", "Delete selected batch?"):
                self.mgr.remove_batch(bid)
                refresh_batches()
                clear_batch_view()

        tk.Button(left, text="Delete Batch", command=on_delete_batch).grid(row=4, column=0, sticky="w", pady=4)

        # Right: selected batch details and item form
        right = tk.Frame(self.content)
        right.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        selected_label = tk.Label(right, text="No batch selected", font=(None, 12))
        selected_label.grid(row=0, column=0, sticky="w")

        items_canvas = tk.Canvas(right, highlightthickness=0)
        items_canvas.grid(row=1, column=0, sticky="nsew")
        items_scroll = ttk.Scrollbar(right, orient="vertical", command=items_canvas.yview)
        items_scroll.grid(row=1, column=1, sticky="ns")
        items_canvas.configure(yscrollcommand=items_scroll.set)

        items_container = tk.Frame(items_canvas)
        items_window = items_canvas.create_window((0, 0), window=items_container, anchor="nw")

        def on_items_container_configure(event=None):
            items_canvas.configure(scrollregion=items_canvas.bbox("all"))

        def on_items_canvas_configure(event):
            items_canvas.itemconfigure(items_window, width=event.width)

        items_container.bind("<Configure>", on_items_container_configure)
        items_canvas.bind("<Configure>", on_items_canvas_configure)

        form = tk.Frame(right)
        form.grid(row=2, column=0, sticky="w", pady=8)
        tk.Label(form, text="Title:").grid(row=0, column=0, sticky="w")
        title_var = tk.StringVar()
        tk.Entry(form, textvariable=title_var, width=40).grid(row=0, column=1, sticky="w")

        tk.Label(form, text="Type:").grid(row=1, column=0, sticky="w")
        type_var = tk.StringVar(value="paperback")
        type_cb = ttk.Combobox(form, textvariable=type_var, values=("paperback", "hardcover"), state="readonly", width=20)
        type_cb.grid(row=1, column=1, sticky="w")

        tk.Label(form, text="Quantity:").grid(row=2, column=0, sticky="w")
        qty_var = tk.IntVar(value=1)
        tk.Entry(form, textvariable=qty_var, width=10).grid(row=2, column=1, sticky="w")

        def clear_batch_view():
            selected_label.config(text="No batch selected")
            for w in items_container.winfo_children():
                w.destroy()

        def refresh_batches():
            batch_listbox.delete(0, "end")
            for b in self.mgr.list_batches():
                status = "[COMMITTED]" if b.get("committed") else "[PENDING]"
                batch_listbox.insert("end", f"{b['name']} ({len(b.get('items',[]))} items) {status}")

        def on_select_batch(event=None):
            sel = batch_listbox.curselection()
            if not sel:
                clear_batch_view()
                return
            idx = sel[0]
            batches = self.mgr.list_batches()
            batch = batches[idx]
            selected_label.config(text=f"Batch: {batch.get('name')}")
            # populate rows
            for w in items_container.winfo_children():
                w.destroy()

            indexed_items = list(enumerate(batch.get('items', [])))
            sorted_items = sorted(indexed_items, key=lambda pair: pair[1].get('title', '').lower())
            for item_index, item in sorted_items:
                row = tk.Frame(items_container)
                row.pack(fill="x", pady=2)

                text = f"{item.get('title')} ({item.get('book_type')}) - {item.get('quantity')}"
                tk.Label(row, text=text, anchor="w").pack(side="left", fill="x", expand=True)

                if not batch.get("committed"):
                    def on_remove_item(batch_id=batch["id"], idx=item_index):
                        if self.mgr.remove_item_from_batch(batch_id, idx):
                            on_select_batch()

                    tk.Button(row, text="Remove", fg="red", command=on_remove_item).pack(side="right", padx=4)

        batch_listbox.bind("<<ListboxSelect>>", on_select_batch)

        def on_add_to_batch():
            sel = batch_listbox.curselection()
            if not sel:
                messagebox.showerror("No batch", "Select or create a batch first")
                return
            idx = sel[0]
            batches = self.mgr.list_batches()
            bid = batches[idx]["id"]
            title = title_var.get().strip()
            btype = type_var.get().strip()
            try:
                qty = int(qty_var.get())
            except Exception:
                messagebox.showerror("Invalid", "Quantity must be integer")
                return
            if not title:
                messagebox.showerror("Invalid", "Title required")
                return
            self.mgr.add_item_to_batch(bid, title, btype, qty)
            on_select_batch()

        tk.Button(form, text="Add to Batch", command=on_add_to_batch).grid(row=3, column=0, columnspan=2, pady=6)

        def on_commit_batch():
            sel = batch_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            batches = self.mgr.list_batches()
            batch = batches[idx]
            bid = batch["id"]
            if batch.get("committed"):
                messagebox.showinfo("Already Committed", "This batch is already committed. Mark it as shipped in 'In Shipment' pane.")
                return
            if messagebox.askyesno("Commit", "Commit this batch to stock? This cannot be undone."):
                self.mgr.commit_batch(bid)
                refresh_batches()
                self.show_overall()

        tk.Button(right, text="Commit Batch to Stock", command=on_commit_batch).grid(row=3, column=0, sticky="w", pady=6)

        refresh_batches()


if __name__ == "__main__":
    app = BookstockerApp()
    app.mainloop()
