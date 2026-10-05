import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.models.schemas import Ingrediente, Producto, Receta

DATA_DIR = Path(__file__).parent
CATALOGO_DIR = DATA_DIR / "mercadona_catalog"


def _norm(texto: str) -> str:
    """Minúsculas y sin acentos, para búsquedas."""
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _a_float(valor) -> Optional[float]:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def normalizar_producto(raw: dict) -> Producto:
    """Convierte el JSON crudo de Mercadona en un `Producto`."""
    pi = raw.get("price_instructions") or {}
    cats = raw.get("categories") or []
    cat0 = cats[0] if cats else {}
    sub = (cat0.get("categories") or [{}])[0] if cat0 else {}
    return Producto(
        id=str(raw["id"]),
        nombre=raw.get("display_name", ""),
        precio=_a_float(pi.get("unit_price")) or 0.0,
        precio_referencia=_a_float(pi.get("reference_price")),
        formato_referencia=pi.get("reference_format"),
        tamano=pi.get("unit_size"),
        formato_tamano=pi.get("size_format"),
        categoria=cat0.get("name", ""),
        subcategoria=sub.get("name"),
        thumbnail=raw.get("thumbnail"),
        url=raw.get("share_url"),
    )


def _leer(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_categorias() -> dict:
    """Árbol de categorías del catálogo real de Mercadona."""
    return _leer(CATALOGO_DIR / "categories.json")


def get_producto_ids() -> list[str]:
    return _leer(CATALOGO_DIR / "product_ids.json")["product_ids"]


@lru_cache(maxsize=1)
def _indice() -> dict[str, Producto]:
    """Carga y normaliza todo el catálogo una sola vez."""
    indice = {}
    for pid in get_producto_ids():
        path = CATALOGO_DIR / "products" / f"{pid}.json"
        if not path.exists():
            continue
        p = normalizar_producto(_leer(path))
        if p.precio > 0:
            indice[p.id] = p
    return indice


def get_producto(product_id: str) -> Optional[Producto]:
    return _indice().get(str(product_id))


def buscar_productos(
    texto: Optional[str] = None,
    categoria: Optional[str] = None,
    precio_max: Optional[float] = None,
    limite: int = 50,
) -> list[Producto]:
    texto_n = _norm(texto) if texto else None
    cat_n = _norm(categoria) if categoria else None
    resultado = []
    for p in _indice().values():
        if texto_n and texto_n not in _norm(p.nombre):
            continue
        if cat_n and cat_n not in _norm(p.categoria) and cat_n not in _norm(p.subcategoria or ""):
            continue
        if precio_max is not None and p.precio > precio_max:
            continue
        resultado.append(p)
        if len(resultado) >= limite:
            break
    return resultado


def mejor_producto(consulta: str) -> Optional[Producto]:
    """Producto que mejor encaja con lo que pide el usuario ("leche", "café molido"...).

    Prefiere nombres que empiezan por la consulta, luego marca Hacendado, luego el más barato
    por precio de referencia. Los productos que no son de alimentación no se consideran.
    """
    q = _norm(consulta.strip())
    if not q:
        return None
    candidatos = [
        p
        for p in _indice().values()
        if q in _norm(p.nombre) and p.categoria not in CATEGORIAS_NO_ALIMENTACION
    ]
    if not candidatos:
        return None
    return min(
        candidatos,
        key=lambda p: (
            not _norm(p.nombre).startswith(q),
            "hacendado" not in _norm(p.nombre),
            p.precio_referencia if p.precio_referencia is not None else p.precio,
        ),
    )


CATEGORIAS_NO_ALIMENTACION = {
    "Bebé",
    "Cuidado del cabello",
    "Cuidado facial y corporal",
    "Fitoterapia y parafarmacia",
    "Limpieza y hogar",
    "Maquillaje",
    "Mascotas",
}


@lru_cache(maxsize=1)
def _recetas() -> tuple[Receta, ...]:
    from app.logic.carrito import precio_receta

    recetas = []
    for raw in _leer(DATA_DIR / "mock_data.json")["recetas"]:
        ingredientes = [
            Ingrediente(unidades=i["unidades"], producto=_indice()[i["producto_id"]]) for i in raw["ingredientes"]
        ]
        receta = Receta(**{**raw, "ingredientes": ingredientes})
        receta.precio_estimado = precio_receta(receta)
        recetas.append(receta)
    return tuple(recetas)


def get_recetas() -> list[Receta]:
    """Recetas mock con los productos reales dentro de cada ingrediente."""
    return list(_recetas())


def get_receta(receta_id: str) -> Optional[Receta]:
    return next((r for r in _recetas() if r.id == receta_id), None)
