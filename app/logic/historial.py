"""Historial de planes en memoria (se pierde al reiniciar) y métricas del dashboard."""
from collections import Counter
from typing import Optional

from app.models.schemas import PlanResponse

_planes: dict[str, PlanResponse] = {}
_presupuestos: dict[str, Optional[float]] = {}
_sustituciones = 0


def reset() -> None:
    global _sustituciones
    _planes.clear()
    _presupuestos.clear()
    _sustituciones = 0


def registrar_plan(plan: PlanResponse, presupuesto: Optional[float] = None) -> None:
    _planes[plan.id] = plan
    _presupuestos[plan.id] = presupuesto


def registrar_sustitucion(plan: PlanResponse) -> None:
    global _sustituciones
    _sustituciones += 1
    if plan.id in _planes:
        _planes[plan.id] = plan


def get_plan(plan_id: str) -> Optional[PlanResponse]:
    return _planes.get(plan_id)


def metricas() -> dict:
    planes = list(_planes.values())
    usos = Counter(r.nombre for p in planes for r in p.dias.values())
    ahorros = [
        _presupuestos[p.id] - p.total
        for p in planes
        if _presupuestos.get(p.id) is not None and _presupuestos[p.id] >= p.total
    ]
    return {
        "planes_generados": len(planes),
        "sustituciones": _sustituciones,
        "gasto_medio": round(sum(p.total for p in planes) / len(planes), 2) if planes else 0.0,
        "planes_dentro_presupuesto": sum(1 for p in planes if p.dentro_presupuesto),
        "ahorro_total_vs_presupuesto": round(sum(ahorros), 2),
        "recetas_mas_usadas": [{"receta": n, "veces": v} for n, v in usos.most_common(5)],
    }
