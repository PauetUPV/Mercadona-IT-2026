"""Chips de respuesta rápida. Los genera el código a partir de lo que acaba de pasar, y cada chip es un
mensaje que el intérprete entiende (al pulsarlo, el frontend lo envía tal cual a /chat)."""
import math
from typing import Optional

from app.logic.sesiones import Sesion

MAX_CHIPS = 4
PEDIR_COMENSALES = ["Somos 2", "Somos 4", "Para 1 persona"]
PEDIR_PLAN = "Hazme un plan para la semana"


def _otro_dia(sesion: Sesion, distinto_de: Optional[str] = None) -> Optional[str]:
    dias = list(sesion.plan.dias) if sesion.plan else []
    return next((d for d in dias if d != distinto_de), None)


def _chips_del_plan(sesion: Sesion, distinto_de: Optional[str] = None) -> list[str]:
    chips = []
    dia = _otro_dia(sesion, distinto_de)
    if dia:
        chips.append(f"Cambia el {dia}")
    if sesion.momentos == ["comida"]:
        chips.append("Quiero comida y cena")
    if not sesion.excluir:
        chips.append("Soy vegetariano")
    if sesion.plan and not sesion.plan.extras:
        chips.append("Añade leche")
    return chips


def para(hechos: dict, sesion: Sesion) -> list[str]:
    tipo = hechos.get("tipo")
    if tipo == "plan":
        chips = _chips_del_plan(sesion)
    elif tipo == "cambio_plato":
        chips = _chips_del_plan(sesion, hechos.get("dia"))
    elif tipo in ("extra_anadido", "extra_quitado", "producto_no_encontrado"):
        chips = ["Añade café", "Añade huevos"] + _chips_del_plan(sesion)[:1]
    elif tipo == "inviable":
        objetivo = int(math.ceil((hechos["importe_minimo_aproximado"] + 0.01) / 5) * 5)
        chips = [f"Mejor {objetivo} euros"]
        if hechos.get("comensales", 1) > 1:
            chips.append("Para 1 persona")
        chips.append("Solo de lunes a miércoles")
    elif tipo in ("pregunta_comensales", "sin_plan"):
        chips = PEDIR_COMENSALES + ([PEDIR_PLAN] if tipo == "sin_plan" else [])
    elif tipo == "rechazo" and "personas" in hechos.get("motivo", ""):
        chips = ["Somos 2", "Somos 4"]
    elif tipo in ("charla", "no_entiendo"):
        chips = _chips_del_plan(sesion) if sesion.plan else [PEDIR_PLAN]
    else:
        chips = []
    return chips[:MAX_CHIPS]
