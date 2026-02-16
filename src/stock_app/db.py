from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

DB_FILENAME = "stock_manager.db"


@dataclass(frozen=True)
class Product:
    id: int
    sku: str
    name: str
    category: str
    price: float
    quantity: int
    min_stock: int


class StockDatabase:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or Path.cwd() / DB_FILENAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL CHECK(price >= 0),
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                    min_stock INTEGER NOT NULL DEFAULT 0 CHECK(min_stock >= 0),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    movement_type TEXT NOT NULL CHECK(movement_type IN ('IN', 'OUT')),
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    note TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
                CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
                CREATE INDEX IF NOT EXISTS idx_movements_product_id ON stock_movements(product_id);
                """
            )

    def list_products(self, search: str = "") -> list[Product]:
        pattern = f"%{search.strip()}%"
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, sku, name, category, price, quantity, min_stock
                FROM products
                WHERE sku LIKE ? OR name LIKE ? OR category LIKE ?
                ORDER BY name COLLATE NOCASE
                """,
                (pattern, pattern, pattern),
            ).fetchall()
        return [Product(**dict(row)) for row in rows]

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, sku, name, category, price, quantity, min_stock
                FROM products
                WHERE id = ?
                """,
                (product_id,),
            ).fetchone()
        if row is None:
            return None
        return Product(**dict(row))

    def add_product(self, sku: str, name: str, category: str, price: float, quantity: int, min_stock: int) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO products (sku, name, category, price, quantity, min_stock)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sku.strip(), name.strip(), category.strip(), float(price), int(quantity), int(min_stock)),
            )

    def update_product(self, product_id: int, sku: str, name: str, category: str, price: float, min_stock: int) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE products
                SET sku = ?, name = ?, category = ?, price = ?, min_stock = ?
                WHERE id = ?
                """,
                (sku.strip(), name.strip(), category.strip(), float(price), int(min_stock), product_id),
            )

    def delete_product(self, product_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def adjust_stock(self, product_id: int, movement_type: str, quantity: int, note: str = "") -> None:
        movement_type = movement_type.upper().strip()
        if movement_type not in {"IN", "OUT"}:
            raise ValueError("movement_type must be IN or OUT")
        qty = int(quantity)
        if qty <= 0:
            raise ValueError("quantity must be positive")

        with self.connection() as conn:
            row = conn.execute("SELECT quantity FROM products WHERE id = ?", (product_id,)).fetchone()
            if row is None:
                raise ValueError("Produit introuvable")

            current_qty = int(row["quantity"])
            new_qty = current_qty + qty if movement_type == "IN" else current_qty - qty
            if new_qty < 0:
                raise ValueError("Stock insuffisant pour cette sortie")

            conn.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_qty, product_id))
            conn.execute(
                """
                INSERT INTO stock_movements (product_id, movement_type, quantity, note)
                VALUES (?, ?, ?, ?)
                """,
                (product_id, movement_type, qty, note.strip()),
            )

    def low_stock_products(self) -> list[Product]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, sku, name, category, price, quantity, min_stock
                FROM products
                WHERE quantity <= min_stock
                ORDER BY quantity ASC, name COLLATE NOCASE
                """
            ).fetchall()
        return [Product(**dict(row)) for row in rows]

    def recent_movements(self, limit: int = 50) -> Iterable[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT m.created_at, p.sku, p.name, m.movement_type, m.quantity, COALESCE(m.note, '') AS note
                FROM stock_movements m
                JOIN products p ON p.id = m.product_id
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return rows
