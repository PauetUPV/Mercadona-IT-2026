import math
from typing import Optional

from app.data.catalogo import get_producto
from app.models.schemas import Carrito, LineaCarrito, Receta

EPS = 1e-9


def precio_receta(receta: Receta, comensales: Optional[int] = None) -> float:
    """Coste de los ingredientes (sin redondear a envases) para `comensales`."""
    factor = (comensales or receta.raciones) / receta.raciones
    total = 0.0
    for ing in receta.ingredientes:
        producto = get_producto(ing.producto_id)
        if producto:
            total += producto.precio * ing.unidades * factor
    return round(total, 2)


def construir_carrito(recetas: list[Receta], comensales: int) -> Carrito:
    """Suma los ingredientes de todas las recetas; los envases se compran enteros."""
    unidades: dict[str, float] = {}
    for receta in recetas:
        factor = comensales / receta.raciones
        for ing in receta.ingredientes:
            unidades[ing.producto_id] = unidades.get(ing.producto_id, 0.0) + ing.unidades * factor

    lineas = []
    for pid, u in unidades.items():
        producto = get_producto(pid)
        if producto is None:
            continue
        n = max(1, math.ceil(u - EPS))
        lineas.append(LineaCarrito(producto=producto, unidades=n, subtotal=round(n * producto.precio, 2)))
    lineas.sort(key=lambda l: (l.producto.categoria, l.producto.nombre))
    return Carrito(lineas=lineas, total=round(sum(l.subtotal for l in lineas), 2))


def extras_de(recetas: list[Receta]) -> list[str]:
    """Extras (sal, agua...) de todas las recetas, sin repetir y ordenados."""
    return sorted({e for r in recetas for e in r.extras})
