from pathlib import Path

from stock_app.db import StockDatabase


def test_add_update_and_list_products(tmp_path: Path) -> None:
    db = StockDatabase(tmp_path / "test.db")

    db.add_product("A1", "Article 1", "Divers", 12.5, 10, 2)
    products = db.list_products()
    assert len(products) == 1
    assert products[0].name == "Article 1"

    product_id = products[0].id
    db.update_product(product_id, "A1", "Article A", "Divers", 14.0, 3)

    products = db.list_products("Article")
    assert products[0].price == 14.0
    assert products[0].min_stock == 3


def test_movements_and_low_stock(tmp_path: Path) -> None:
    db = StockDatabase(tmp_path / "test.db")
    db.add_product("B1", "Clavier", "IT", 30.0, 5, 2)
    product = db.list_products()[0]

    db.adjust_stock(product.id, "IN", 2, "réception")
    assert db.list_products()[0].quantity == 7

    db.adjust_stock(product.id, "OUT", 6, "vente")
    assert db.list_products()[0].quantity == 1

    low = db.low_stock_products()
    assert len(low) == 1
    assert low[0].sku == "B1"

    movements = list(db.recent_movements())
    assert len(movements) == 2


def test_get_by_id_and_delete_cascade(tmp_path: Path) -> None:
    db = StockDatabase(tmp_path / "test.db")
    db.add_product("C1", "Souris", "IT", 20.0, 10, 2)

    product = db.list_products()[0]
    by_id = db.get_product_by_id(product.id)
    assert by_id is not None
    assert by_id.sku == "C1"

    db.adjust_stock(product.id, "OUT", 1, "sortie")
    assert len(list(db.recent_movements())) == 1

    db.delete_product(product.id)
    assert db.get_product_by_id(product.id) is None
    assert len(list(db.recent_movements())) == 0
