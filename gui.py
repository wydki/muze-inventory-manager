import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import LEFT
from .stock_manager import StockManager

# Subtle blue color palette (matching dashboard_ttk)
SIDEBAR_BG = "#f7fafc"
CONTENT_BG = "#ffffff"
CARD_BG = "#f7fafc"
BORDER_COLOR = "#e2e8f0"
TEXT_COLOR = "#1e293b"
ACCENT_BLUE = "#3b82f6"


class BookstockerApp(tb.Window):
    def __init__(self, data_file: str = None):
        super().__init__(themename="flatly")
        self.title("Bookstocker")
        self.state('zoomed')  # full screen on Windows
        self.mgr = StockManager(data_file=data_file) if data_file else StockManager()

        # Layout frames
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = tb.Frame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="nswe")
        self.sidebar.pack_propagate(False)

        # App title at top-left
        title_label = tb.Label(self.sidebar, text="Amuze Inventory Manager", font=(None, 12, 'bold'), anchor="w")
        title_label.pack(fill="x", padx=8, pady=8)

        self.content = tb.Frame(self)
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
            b = tb.Button(self.sidebar, text=label, command=cmd, bootstyle="light")
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

        tb.Button(self.sidebar, text="Archive Stock", command=on_archive, bootstyle="light").pack(side="bottom", fill="x", padx=8, pady=4)

        def on_clear_stock():
            if messagebox.askyesno("Confirm", "Are you sure you want to clear all stock?"):
                self.mgr.clear_stock()
                self.mgr.clear_batches()
                messagebox.showinfo("Cleared", "All stock and batches cleared")
                self.show_overall()

        tb.Button(self.sidebar, text="Clear Stock", command=on_clear_stock, bootstyle="danger").pack(side="bottom", fill="x", padx=8, pady=8)

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
        lbl = tb.Label(self.content, text="Home", font=(None, 16, 'bold'))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)

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

        # Stat cards grid (4 columns)
        cards_frame = tb.Frame(self.content)
        cards_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        for i in range(4):
            cards_frame.columnconfigure(i, weight=1)

        stats = [
            ("Total Books in Stock", str(total_books)),
            ("Total Batches", str(total_batches)),
            ("Batches in Shipment", str(total_shipments)),
            ("Requested Books", str(total_requests)),
        ]
        for idx, (label, val) in enumerate(stats):
            f = tb.Frame(cards_frame, padding=10, bootstyle="light")
            f.grid(row=0, column=idx, padx=6, sticky="nsew")
            tb.Label(f, text=val, font=(None, 20, "bold")).pack(anchor="w")
            tb.Label(f, text=label, font=(None, 10)).pack(anchor="w")
            tb.Button(f, text="View", bootstyle="info").pack(anchor="w", pady=(6, 0))

        # Quick actions
        actions = tb.Frame(self.content)
        actions.grid(row=2, column=0, sticky="w", padx=16, pady=12)
        tb.Button(actions, text="View Batches", command=self.show_batches, bootstyle="primary").pack(side="left", padx=6)
        tb.Button(actions, text="View Overall Stock", command=self.show_overall, bootstyle="primary").pack(side="left", padx=6)
        tb.Button(actions, text="View Requests", command=self.show_requests, bootstyle="primary").pack(side="left", padx=6)

    def show_overall(self):
        self.clear_content()
        lbl = tb.Label(self.content, text="Overall Books in Stock", font=(None, 14))
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
        lbl = tb.Label(self.content, text="Requests", font=(None, 18, "bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        # Main content frame with list of requests
        main_frame = tb.Frame(self.content)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        self.content.rowconfigure(1, weight=1)

        # Requests list card
        list_card = tb.Frame(main_frame, padding=8, bootstyle="light")
        list_card.pack(fill="both", expand=True)
        list_card.columnconfigure(0, weight=1)
        list_card.rowconfigure(0, weight=1)

        requests_frame = tb.Frame(list_card)
        requests_frame.grid(row=0, column=0, sticky="nsew")
        requests_frame.columnconfigure(0, weight=1)

        def populate_requests():
            """Populate the main requests list."""
            for w in requests_frame.winfo_children():
                w.destroy()

            sorted_requests = sorted(
                enumerate(self.mgr.list_requests()),
                key=lambda pair: pair[1].get('title', '').lower(),
            )

            if not sorted_requests:
                tk.Label(requests_frame, text="No requests yet", bg=CARD_BG, fg="gray", font=(None, 12)).pack(anchor="w", pady=20)
                return

            for idx, req in sorted_requests:
                row = tb.Frame(requests_frame)
                row.pack(fill="x", pady=6)

                # Checkmark button on left
                def on_checkmark(req=req):
                    batch_id = self.mgr.get_latest_batch()
                    if not batch_id:
                        messagebox.showerror("No Batch", "No batch created yet. Create a batch first.")
                        return
                    qty_dialog = tk.Toplevel(self)
                    qty_dialog.title("Enter Quantity")
                    qty_dialog.geometry("300x120")
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
                        batch = self.mgr.batches.get(batch_id, {})
                        found = False
                        for item in batch.get("items", []):
                            if item["title"].lower() == req["title"].lower() and item["book_type"].lower() == req["book_type"].lower():
                                item["quantity"] += qty
                                found = True
                                break
                        if not found:
                            self.mgr.add_item_to_batch(batch_id, req["title"], req["book_type"], qty)
                        else:
                            self.mgr._save_batches()
                        messagebox.showinfo("Added", f"Added {qty}x '{req['title']}' to batch")
                        qty_dialog.destroy()

                    tk.Button(qty_dialog, text="OK", command=on_ok).pack(pady=4)

                # Title and type stacked on left
                text_frame = tb.Frame(row)
                text_frame.pack(side="left", fill="both", expand=True, padx=(8, 12))
                
                tb.Label(text_frame, text=f"{req['title']}", font=(None, 12)).pack(anchor="w", fill="x")
                tb.Label(text_frame, text=f"{req['book_type']}", font=(None, 10)).pack(anchor="w", fill="x")

                # Delete button on right
                def on_delete(idx=idx):
                    self.mgr.remove_request(idx)
                    populate_requests()

                tb.Button(row, text="✕", width=2, command=on_delete, bootstyle="danger-link").pack(side="right", padx=4, pady=8)

                # Checkmark button on right (before x)
                tb.Button(row, text="✓", width=2, command=on_checkmark, bootstyle="success-link").pack(side="right", padx=4, pady=8)

        populate_requests()

        # Bottom-right action buttons (+ and trash)
        button_area = tb.Frame(self.content)
        button_area.grid(row=2, column=0, sticky="se", padx=8, pady=8)

        # Modal form overlay
        modal_frame = None
        modal_vars = {"title_var": None, "type_var": None}

        def show_add_form():
            """Show modal form for adding a request."""
            nonlocal modal_frame
            
            # Create overlay frame
            modal_frame = tb.Frame(self.content, padding=20, bootstyle="light")
            modal_frame.grid(row=1, column=0, sticky="nsew", padx=120, pady=60, in_=self.content)
            modal_frame.columnconfigure(0, weight=1)

            # Title label - no alignment with close button
            tb.Label(modal_frame, text="Add Request", font=(None, 14, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 12))

            # X button in top-right (separate row)
            x_btn = tb.Button(modal_frame, text="✕", width=2, command=lambda: close_form(), bootstyle="link")
            x_btn.grid(row=0, column=1, sticky="ne")

            # Title input
            tb.Label(modal_frame, text="Title:").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 4))
            title_var = tk.StringVar()
            title_entry = tb.Entry(modal_frame, textvariable=title_var, width=35)
            title_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
            title_entry.focus()
            modal_vars["title_var"] = title_var

            # Type input
            tb.Label(modal_frame, text="Type:").grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 4))
            type_var = tk.StringVar(value="paperback")
            type_cb = ttk.Combobox(modal_frame, textvariable=type_var, values=("paperback", "hardcover"), state="readonly", width=32)
            type_cb.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 16))
            modal_vars["type_var"] = type_var

            # Checkmark button
            def on_add_request():
                title = title_var.get().strip()
                btype = type_var.get().strip()
                if not title:
                    messagebox.showerror("Invalid", "Title is required")
                    return
                self.mgr.add_request(title=title, book_type=btype)
                close_form()
                populate_requests()

            check_btn = tb.Button(modal_frame, text="✓", command=on_add_request, bootstyle="success")
            check_btn.grid(row=5, column=1, sticky="se", pady=(8, 0))

        def close_form():
            """Close the modal form."""
            nonlocal modal_frame
            if modal_frame:
                modal_frame.grid_forget()
                modal_frame = None
                modal_vars["title_var"] = None
                modal_vars["type_var"] = None

        def on_clear_all():
            if messagebox.askyesno("Clear All", "Delete all requests?"):
                self.mgr.requests = []
                self.mgr._save_requests()
                populate_requests()

        tb.Button(button_area, text="+", width=3, command=show_add_form, bootstyle="primary").pack(side="right", padx=2)
        tb.Button(button_area, text="🗑", width=3, command=on_clear_all, bootstyle="link").pack(side="right", padx=2)

    def show_in_shipment(self):
        self.clear_content()
        lbl = tb.Label(self.content, text="In Shipment", font=(None, 14))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        # Frame to display batches with shipment status
        list_frame = tb.Frame(self.content)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        tb.Label(list_frame, text="Batch Status:").pack(anchor="w", pady=(0, 8))
        
        batches_container = tb.Frame(list_frame)
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
        lbl = tb.Label(self.content, text="Batches", font=(None, 14))
        lbl.grid(row=0, column=0, sticky="w", padx=8, pady=8)
        # Two-pane layout: left for batches, right for batch details
        # use a PanedWindow so the divider is draggable and panes resize adaptively
        self.content.rowconfigure(1, weight=1)
        paned = ttk.Panedwindow(self.content, orient="horizontal")
        paned.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        left = tb.Frame(paned)
        left.rowconfigure(1, weight=1)
        paned.add(left, weight=1)

        tb.Label(left, text="Batches:").grid(row=0, column=0, sticky="w")
        batch_listbox = tk.Listbox(left, width=30, height=12)
        batch_listbox.grid(row=1, column=0, sticky="nsew")
        lb_scroll = ttk.Scrollbar(left, orient="vertical", command=batch_listbox.yview)
        batch_listbox.configure(yscrollcommand=lb_scroll.set)
        lb_scroll.grid(row=1, column=1, sticky="ns")

        name_var = tk.StringVar()
        tb.Entry(left, textvariable=name_var, width=25).grid(row=2, column=0, sticky="w", pady=6)
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

        tb.Button(left, text="Create Batch", command=on_create_batch, bootstyle="primary").grid(row=3, column=0, sticky="w")
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

        tb.Button(left, text="Delete Batch", command=on_delete_batch, bootstyle="danger").grid(row=4, column=0, sticky="w", pady=4)

        # Right: selected batch details and item form
        right = tb.Frame(paned)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        paned.add(right, weight=3)

        selected_label = tb.Label(right, text="No batch selected", font=(None, 12))
        selected_label.grid(row=0, column=0, sticky="w")

        items_canvas = tk.Canvas(right, highlightthickness=0, bg=CARD_BG)
        items_canvas.grid(row=1, column=0, sticky="nsew")
        items_scroll = ttk.Scrollbar(right, orient="vertical", command=items_canvas.yview)
        items_scroll.grid(row=1, column=1, sticky="ns")
        items_canvas.configure(yscrollcommand=items_scroll.set, bg=CARD_BG)

        items_container = tk.Frame(items_canvas, bg=CARD_BG)
        items_window = items_canvas.create_window((0, 0), window=items_container, anchor="nw")

        def on_items_container_configure(event=None):
            items_canvas.configure(scrollregion=items_canvas.bbox("all"))

        def on_items_canvas_configure(event):
            items_canvas.itemconfigure(items_window, width=event.width)

        items_container.bind("<Configure>", on_items_container_configure)
        items_canvas.bind("<Configure>", on_items_canvas_configure)

        form = tb.Frame(right)
        form.grid(row=2, column=0, sticky="w", pady=8)
        tb.Label(form, text="Title:").grid(row=0, column=0, sticky="w")
        title_var = tk.StringVar()
        tb.Entry(form, textvariable=title_var, width=40).grid(row=0, column=1, sticky="w")

        tb.Label(form, text="Type:").grid(row=1, column=0, sticky="w")
        type_var = tk.StringVar(value="paperback")
        type_cb = ttk.Combobox(form, textvariable=type_var, values=("paperback", "hardcover"), state="readonly", width=20)
        type_cb.grid(row=1, column=1, sticky="w")

        tb.Label(form, text="Quantity:").grid(row=2, column=0, sticky="w")
        qty_var = tk.IntVar(value=1)
        tb.Entry(form, textvariable=qty_var, width=10).grid(row=2, column=1, sticky="w")

        # edit_state keeps track if the user is editing an existing item
        edit_state = {"batch_id": None, "item_index": None}

        def clear_batch_view():
            selected_label.config(text="No batch selected")
            for w in items_container.winfo_children():
                w.destroy()
            # reset edit state and form
            edit_state["batch_id"] = None
            edit_state["item_index"] = None
            title_var.set("")
            type_var.set("paperback")
            qty_var.set(1)

        def refresh_batches():
            batch_listbox.delete(0, "end")
            for b in self.mgr.list_batches():
                status = "[COMMITTED]" if b.get("committed") else "[PENDING]"
                batch_listbox.insert("end", f"{b['name']} ({len(b.get('items',[]))} items) {status}")

        def on_select_batch(event=None):
            sel = batch_listbox.curselection()
            if not sel:
                # ignore transient empty-selection events (e.g. focus changes when editing entries)
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
                row = tk.Frame(items_container, bg="white")
                row.pack(fill="x", pady=2)

                text = f"{item.get('title')} ({item.get('book_type')}) - {item.get('quantity')}"
                lbl = tk.Label(row, text=text, anchor="w", bg="white")
                lbl.pack(side="left", fill="x", expand=True)

                # double-clicking a row loads it into the form for editing
                def start_edit(event=None, batch_id=batch["id"], idx=item_index, it=item):
                    edit_state["batch_id"] = batch_id
                    edit_state["item_index"] = idx
                    title_var.set(it.get("title"))
                    type_var.set(it.get("book_type"))
                    try:
                        qty_var.set(int(it.get("quantity", 1)))
                    except Exception:
                        qty_var.set(1)
                    try:
                        add_button.config(text="Update Item")
                    except Exception:
                        pass

                lbl.bind("<Double-1>", start_edit)

                if not batch.get("committed"):
                    def on_remove_item(batch_id=batch["id"], idx=item_index):
                        if self.mgr.remove_item_from_batch(batch_id, idx):
                            on_select_batch()

                    tk.Button(row, text="Remove", fg="red", command=on_remove_item).pack(side="right", padx=4)

        batch_listbox.bind("<<ListboxSelect>>", on_select_batch)

        def on_add_to_batch():
            sel = batch_listbox.curselection()
            batches = self.mgr.list_batches()
            if not sel:
                # if nothing selected, default to the latest batch (if any)
                latest_bid = self.mgr.get_latest_batch()
                if not latest_bid:
                    messagebox.showerror("No batch", "No batch available. Create a batch first")
                    return
                # find index of latest batch in the list and select it for clarity
                for i, b in enumerate(batches):
                    if b.get("id") == latest_bid:
                        batch_listbox.selection_clear(0, "end")
                        batch_listbox.selection_set(i)
                        batch_listbox.see(i)
                        on_select_batch()
                        idx = i
                        break
            else:
                idx = sel[0]
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
            # if editing, update the existing item instead of appending
            if edit_state.get("batch_id") and edit_state.get("item_index") is not None:
                ebid = edit_state["batch_id"]
                eidx = edit_state["item_index"]
                if ebid == bid and ebid in self.mgr.batches:
                    items = self.mgr.batches[ebid].get("items", [])
                    if 0 <= eidx < len(items):
                        items[eidx] = {"title": title, "book_type": btype, "quantity": qty}
                        self.mgr._save_batches()
                        # clear edit state and update UI
                        edit_state["batch_id"] = None
                        edit_state["item_index"] = None
                        try:
                            add_button.config(text="Add to Batch")
                        except Exception:
                            pass
                        on_select_batch()
                        return
            # otherwise, append a new item
            self.mgr.add_item_to_batch(bid, title, btype, qty)
            on_select_batch()

        add_button = tk.Button(form, text="Add to Batch", command=on_add_to_batch)
        add_button.grid(row=3, column=0, columnspan=1, pady=6, sticky="w")
        def on_cancel_edit():
            edit_state["batch_id"] = None
            edit_state["item_index"] = None
            title_var.set("")
            type_var.set("paperback")
            qty_var.set(1)
            try:
                add_button.config(text="Add to Batch")
            except Exception:
                pass

        tk.Button(form, text="Cancel", command=on_cancel_edit).grid(row=3, column=1, pady=6, sticky="w")

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
        # Auto-select the latest batch when opening the Batches pane
        latest = self.mgr.get_latest_batch()
        if latest:
            for i, b in enumerate(self.mgr.list_batches()):
                if b.get("id") == latest:
                    batch_listbox.selection_clear(0, "end")
                    batch_listbox.selection_set(i)
                    batch_listbox.see(i)
                    on_select_batch()
                    break


if __name__ == "__main__":
    app = BookstockerApp()
    app.mainloop()
