import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
CATALOGO_DIR = DATA_DIR / "mercadona_catalog"


def get_recetas() -> list[dict]:
    with open(DATA_DIR / "mock_data.json", encoding="utf-8") as f:
        return json.load(f)["recetas"]


def get_categorias() -> dict:
    """Árbol de categorías del catálogo real de Mercadona."""
    with open(CATALOGO_DIR / "categories.json", encoding="utf-8") as f:
        return json.load(f)


def get_producto(product_id: str) -> dict:
    """Detalle completo de un producto del catálogo real."""
    with open(CATALOGO_DIR / "products" / f"{product_id}.json", encoding="utf-8") as f:
        return json.load(f)


def get_producto_ids() -> list[str]:
    with open(CATALOGO_DIR / "product_ids.json", encoding="utf-8") as f:
        return json.load(f)["product_ids"]
