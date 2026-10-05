import json
import re
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


# Palabras que no identifican un plato (se ignoran al buscar recetas por nombre)
_PALABRAS_VACIAS = set(
    "a al algo con de del el en hoy la las lo los me mi para por que un una unos unas y o "
    "quiero quisiera apetece gustaria hazme haz prepara preparame pon ponme anade anademe cocina cocinar comer cenar "
    "comida cena comidas cenas plato platos plan receta noche manana esta este semana dia dias solo tambien porfa favor "
    "lunes martes miercoles jueves viernes sabado domingo "
    "mucho mucha muchisimo algo poco rico rica ganas comerme cenarme tomar hacer tengo mejor bueno vale pasado pero nada mas "
    "hace hago preparo prepara preparar lleva llevan ingrediente ingredientes cuesta cuestan costar coste cuanto cuanta "
    "como cual cuales receta recetas instrucciones pasos dime necesito necesita tiene tienen toca hay puedo cocino".split()
)
_ALIAS = {"spaghetti": "espagueti", "espaguetti": "espagueti", "macarrone": "macarron", "albondiga": "albondiga"}


def _tokens_plato(texto: str) -> list[str]:
    """Palabras significativas en orden, en singular aproximado y sin repetir."""
    tokens: list[str] = []
    for t in re.findall(r"[a-z]+", _norm(texto)):
        if t in _PALABRAS_VACIAS or len(t) < 3:
            continue
        t = t[:-2] if t.endswith("es") and len(t) > 5 else (t[:-1] if t.endswith("s") else t)  # singular aproximado
        t = _ALIAS.get(t, t)
        if t not in tokens:
            tokens.append(t)
    return tokens


def buscar_receta(texto: str) -> tuple[Optional[Receta], float, list[Receta]]:
    """Receta cuyo nombre mejor encaja con `texto` ("pollo al curry", "quiero lentejas"...).

    Devuelve (mejor, parecido, alternativas). `parecido` es la fracción de palabras del texto que
    aparecen en el nombre de la receta (1.0 = todas). Sin coincidencias: (None, 0, []).
    """
    pedidas = _tokens_plato(texto)
    if not pedidas:
        return None, 0.0, []
    puntuadas = []
    for r in _recetas():
        nombre = _tokens_plato(r.nombre)
        comunes = len(set(pedidas) & set(nombre))
        if comunes:
            # más palabras en común; a igualdad, que contenga la primera palabra pedida (el plato, no el acompañamiento)
            puntuadas.append(((comunes, pedidas[0] in nombre, comunes / len(nombre), -len(nombre)), r))
    if not puntuadas:
        return None, 0.0, []
    puntuadas.sort(key=lambda x: x[0], reverse=True)
    mejor = puntuadas[0]
    return mejor[1], mejor[0][0] / len(pedidas), [r for _, r in puntuadas[1:3]]


def recetas_con(texto: str) -> list[Receta]:
    """Recetas que contienen lo que el usuario rechaza: por nombre ("pollo al curry", "pizza")
    o, si es una sola palabra, también por ingrediente ("cebolla")."""
    pedidas = _tokens_plato(texto)
    if not pedidas:
        return []
    encontradas = []
    for r in _recetas():
        nombre = set(_tokens_plato(r.nombre))
        por_ingrediente = len(pedidas) == 1 and any(pedidas[0] in _norm(i.producto.nombre) for i in r.ingredientes)
        if set(pedidas) <= nombre or por_ingrediente:
            encontradas.append(r)
    return encontradas
