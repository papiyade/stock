from __future__ import annotations

import csv
import tkinter as tk
from pathlib import Path
from sqlite3 import IntegrityError
from tkinter import filedialog, messagebox, ttk

from .db import Product, StockDatabase


class StockApp(tk.Tk):
    def __init__(self, database: StockDatabase) -> None:
        super().__init__()
        self.title("Gestion de stock")
        self.geometry("1200x760")
        self.minsize(1000, 620)

        self.db = database
        self.selected_product_id: int | None = None

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(1, weight=1)

        title = ttk.Label(self, text="Application desktop de gestion de stock", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))

        self._build_inventory_panel()
        self._build_right_panel()

    def _build_inventory_panel(self) -> None:
        frame = ttk.LabelFrame(self, text="Inventaire")
        frame.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=8)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        top_controls = ttk.Frame(frame)
        top_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_controls.columnconfigure(1, weight=1)

        ttk.Label(top_controls, text="Recherche:").grid(row=0, column=0, padx=(0, 6))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top_controls, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_products())

        btn_refresh = ttk.Button(top_controls, text="Rafraîchir", command=self.refresh_all)
        btn_refresh.grid(row=0, column=2, padx=(8, 0))

        columns = ("sku", "name", "category", "price", "quantity", "min_stock")
        self.product_tree = ttk.Treeview(frame, columns=columns, show="headings", height=14)
        labels = {
            "sku": "SKU",
            "name": "Nom",
            "category": "Catégorie",
            "price": "Prix",
            "quantity": "Stock",
            "min_stock": "Seuil min",
        }
        widths = {"sku": 100, "name": 240, "category": 130, "price": 100, "quantity": 80, "min_stock": 90}
        for col in columns:
            self.product_tree.heading(col, text=labels[col])
            self.product_tree.column(col, width=widths[col], anchor="center")

        self.product_tree.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.product_tree.bind("<<TreeviewSelect>>", self._on_product_select)

        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        for idx in range(5):
            actions.columnconfigure(idx, weight=1)

        ttk.Button(actions, text="Nouveau", command=self.clear_form).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Button(actions, text="Ajouter", command=self.add_product).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Button(actions, text="Mettre à jour", command=self.update_product).grid(row=0, column=2, sticky="ew", padx=3)
        ttk.Button(actions, text="Supprimer", command=self.delete_product).grid(row=0, column=3, sticky="ew", padx=3)
        ttk.Button(actions, text="Exporter CSV", command=self.export_csv).grid(row=0, column=4, sticky="ew", padx=3)

    def _build_right_panel(self) -> None:
        container = ttk.Frame(self)
        container.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=8)
        container.rowconfigure(0, weight=3)
        container.rowconfigure(1, weight=2)
        container.rowconfigure(2, weight=1)
        container.rowconfigure(3, weight=1)
        container.columnconfigure(0, weight=1)

        self._build_form(container)
        self._build_movements(container)
        self._build_low_stock(container)
        self._build_recent_movements(container)

    def _build_form(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Fiche produit")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        self.sku_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.price_var = tk.StringVar(value="0")
        self.quantity_var = tk.StringVar(value="0")
        self.min_stock_var = tk.StringVar(value="0")

        fields = [
            ("SKU", self.sku_var),
            ("Nom", self.name_var),
            ("Catégorie", self.category_var),
            ("Prix", self.price_var),
            ("Stock initial", self.quantity_var),
            ("Seuil minimum", self.min_stock_var),
        ]

        for row, (label, var) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=5)
            ttk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky="ew", padx=8, pady=5)

    def _build_movements(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Mouvement de stock")
        frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        frame.columnconfigure(1, weight=1)

        self.move_type = tk.StringVar(value="IN")
        self.move_qty = tk.StringVar(value="1")
        self.move_note = tk.StringVar()

        ttk.Label(frame, text="Type").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        type_combo = ttk.Combobox(frame, values=["IN", "OUT"], textvariable=self.move_type, state="readonly")
        type_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(frame, text="Quantité").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(frame, textvariable=self.move_qty).grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(frame, text="Note").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(frame, textvariable=self.move_note).grid(row=2, column=1, sticky="ew", padx=8, pady=4)

        ttk.Button(frame, text="Valider mouvement", command=self.apply_movement).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=8
        )

    def _build_low_stock(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Alertes stock bas")
        frame.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.low_stock_list = tk.Listbox(frame, height=5)
        self.low_stock_list.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def _build_recent_movements(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Historique récent")
        frame.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.movement_list = tk.Listbox(frame, height=6)
        self.movement_list.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def parse_form(self, include_qty: bool) -> tuple[str, str, str, float, int, int]:
        sku = self.sku_var.get().strip()
        name = self.name_var.get().strip()
        category = self.category_var.get().strip()
        if not sku or not name or not category:
            raise ValueError("SKU, Nom et Catégorie sont obligatoires")

        price = float(self.price_var.get())
        if price < 0:
            raise ValueError("Le prix doit être positif")

        quantity = int(self.quantity_var.get()) if include_qty else 0
        if include_qty and quantity < 0:
            raise ValueError("Le stock initial doit être positif")

        min_stock = int(self.min_stock_var.get())
        if min_stock < 0:
            raise ValueError("Le stock minimum doit être positif")

        return sku, name, category, price, quantity, min_stock

    def refresh_products(self) -> None:
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        for product in self.db.list_products(self.search_var.get()):
            self.product_tree.insert(
                "",
                tk.END,
                iid=str(product.id),
                values=(
                    product.sku,
                    product.name,
                    product.category,
                    f"{product.price:.2f}",
                    product.quantity,
                    product.min_stock,
                ),
            )

    def refresh_low_stock(self) -> None:
        self.low_stock_list.delete(0, tk.END)
        for p in self.db.low_stock_products():
            self.low_stock_list.insert(tk.END, f"{p.sku} • {p.name} ({p.quantity}/{p.min_stock})")

    def refresh_recent_movements(self) -> None:
        self.movement_list.delete(0, tk.END)
        for mv in self.db.recent_movements(20):
            line = f"{mv['created_at']} • {mv['sku']} • {mv['movement_type']} {mv['quantity']} ({mv['note']})"
            self.movement_list.insert(tk.END, line)

    def refresh_all(self) -> None:
        self.refresh_products()
        self.refresh_low_stock()
        self.refresh_recent_movements()

    def clear_form(self) -> None:
        self.selected_product_id = None
        self.sku_var.set("")
        self.name_var.set("")
        self.category_var.set("")
        self.price_var.set("0")
        self.quantity_var.set("0")
        self.min_stock_var.set("0")

    def _on_product_select(self, _event: object) -> None:
        selected = self.product_tree.selection()
        if not selected:
            return
        product_id = int(selected[0])
        self.selected_product_id = product_id
        product = self.db.get_product_by_id(product_id)
        if product is None:
            return

        self.populate_form(product)

    def populate_form(self, product: Product) -> None:
        self.sku_var.set(product.sku)
        self.name_var.set(product.name)
        self.category_var.set(product.category)
        self.price_var.set(f"{product.price:.2f}")
        self.quantity_var.set(str(product.quantity))
        self.min_stock_var.set(str(product.min_stock))

    def add_product(self) -> None:
        try:
            sku, name, category, price, quantity, min_stock = self.parse_form(include_qty=True)
            self.db.add_product(sku, name, category, price, quantity, min_stock)
            self.refresh_all()
            self.clear_form()
            messagebox.showinfo("Succès", "Produit ajouté.")
        except IntegrityError:
            messagebox.showerror("Erreur", "SKU déjà existant. Choisissez un SKU unique.")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def update_product(self) -> None:
        if self.selected_product_id is None:
            messagebox.showwarning("Attention", "Sélectionnez un produit à mettre à jour.")
            return

        try:
            sku, name, category, price, _quantity, min_stock = self.parse_form(include_qty=False)
            self.db.update_product(self.selected_product_id, sku, name, category, price, min_stock)
            self.refresh_all()
            messagebox.showinfo("Succès", "Produit mis à jour.")
        except IntegrityError:
            messagebox.showerror("Erreur", "Impossible de sauvegarder: SKU déjà utilisé.")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def delete_product(self) -> None:
        if self.selected_product_id is None:
            messagebox.showwarning("Attention", "Sélectionnez un produit à supprimer.")
            return
        if not messagebox.askyesno("Confirmer", "Supprimer ce produit et ses mouvements ?"):
            return

        try:
            self.db.delete_product(self.selected_product_id)
            self.selected_product_id = None
            self.refresh_all()
            self.clear_form()
            messagebox.showinfo("Succès", "Produit supprimé.")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def apply_movement(self) -> None:
        if self.selected_product_id is None:
            messagebox.showwarning("Attention", "Sélectionnez un produit pour enregistrer un mouvement.")
            return

        try:
            qty = int(self.move_qty.get())
            self.db.adjust_stock(
                self.selected_product_id,
                movement_type=self.move_type.get(),
                quantity=qty,
                note=self.move_note.get(),
            )
            self.refresh_all()
            self.move_qty.set("1")
            self.move_note.set("")
            messagebox.showinfo("Succès", "Mouvement enregistré.")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def export_csv(self) -> None:
        products = self.db.list_products(self.search_var.get())
        target = filedialog.asksaveasfilename(
            title="Exporter le stock",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="stock_export.csv",
        )
        if not target:
            return

        with Path(target).open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["SKU", "Nom", "Catégorie", "Prix", "Stock", "Seuil minimum"])
            for p in products:
                writer.writerow([p.sku, p.name, p.category, f"{p.price:.2f}", p.quantity, p.min_stock])

        messagebox.showinfo("Export terminé", f"Fichier créé: {target}")


def run_app() -> None:
    db = StockDatabase()
    app = StockApp(db)
    app.mainloop()
