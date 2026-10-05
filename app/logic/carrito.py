"""Cálculo de precios. Es la misma regla que aplica el frontend para la lista de la compra:

    envases(producto) = ceil(suma de unidades de ese producto en todas las recetas y extras)
    total = suma de envases * precio

El backend la usa solo internamente (ajustar a presupuesto, avisar de imposibles); no devuelve totales.
"""
import math
from typing import Optional

from app.models.schemas import Ingrediente, PlanResponse, Receta

EPS = 1e-9


def precio_receta(receta: Receta, comensales: Optional[int] = None) -> float:
    """Coste de los ingredientes (sin redondear a envases) para `comensales`."""
    factor = (comensales or receta.raciones) / receta.raciones
    return round(sum(i.producto.precio * i.unidades * factor for i in receta.ingredientes), 2)


def escalar_receta(receta: Receta, comensales: int, momento: Optional[str] = None) -> Receta:
    """Copia de la receta para `comensales`: unidades escaladas y raciones = comensales."""
    factor = comensales / receta.raciones
    return receta.model_copy(
        update={
            "momento": momento,
            "raciones": comensales,
            "ingredientes": [i.model_copy(update={"unidades": round(i.unidades * factor, 4)}) for i in receta.ingredientes],
            "precio_estimado": precio_receta(receta, comensales),
        }
    )


def _ingredientes_del_plan(plan: PlanResponse) -> list[Ingrediente]:
    ingredientes = [i for recetas in plan.dias.values() for r in recetas for i in r.ingredientes]
    return ingredientes + list(plan.extras)


def lista_compra(plan: PlanResponse) -> list[tuple[Ingrediente, int, float]]:
    """[(ingrediente representativo, envases, subtotal)] por producto."""
    unidades: dict[str, float] = {}
    producto = {}
    for ing in _ingredientes_del_plan(plan):
        unidades[ing.producto.id] = unidades.get(ing.producto.id, 0.0) + ing.unidades
        producto[ing.producto.id] = ing.producto
    lineas = []
    for pid, u in unidades.items():
        envases = max(1, math.ceil(u - EPS))
        lineas.append((Ingrediente(unidades=u, producto=producto[pid]), envases, round(envases * producto[pid].precio, 2)))
    return lineas


def total_plan(plan: PlanResponse) -> float:
    return round(sum(subtotal for _, _, subtotal in lista_compra(plan)), 2)


def en_casa_de(recetas: list[Receta]) -> list[str]:
    """Lo que se supone en casa (sal, agua...) de todas las recetas, sin repetir y ordenado."""
    return sorted({e for r in recetas for e in r.en_casa})
