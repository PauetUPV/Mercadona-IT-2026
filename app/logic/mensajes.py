"""Textos del asistente (plantillas).

PUNTO DE ENGANCHE PARA GEMINI: estas funciones devuelven el texto de la burbuja del chat;
se pueden reimplementar con el LLM sin tocar nada más.
"""
from app.models.schemas import PlanResponse


def euros(x: float) -> str:
    return f"{x:.2f}".replace(".", ",") + " €"


def resumen_plan(plan: PlanResponse) -> str:
    platos = "; ".join(f"{dia}: {receta.nombre}" for dia, receta in plan.dias.items())
    texto = f"{platos}. Total de la compra: {euros(plan.total)}"
    if plan.comensales:
        texto = f"Plan para {plan.comensales} persona(s). " + texto
    if plan.presupuesto is not None:
        if plan.dentro_presupuesto:
            texto += f", dentro de tu presupuesto de {euros(plan.presupuesto)}."
        else:
            exceso = plan.total - plan.presupuesto
            texto += f". Me paso {euros(exceso)} de tu presupuesto ({euros(plan.presupuesto)}); es lo más barato que he encontrado."
    else:
        texto += "."
    return texto


def plan_nuevo(plan: PlanResponse) -> str:
    return "¡Listo! " + resumen_plan(plan)


def plan_sustituido(plan: PlanResponse, dia: str) -> str:
    return f"He cambiado el plato del {dia} por {plan.dias[dia].nombre}. " + resumen_plan(plan)


PREGUNTA_COMENSALES = "¿Para cuántas personas es el plan? Puedes decirme también tu presupuesto y qué días no cocinas."
NO_ENTIENDO = "No te he entendido. Dime para cuántas personas, tu presupuesto y qué días no cocinas, o pídeme cambiar un plato (p. ej. «cambia el martes»)."
PREGUNTA_DIA = "¿Qué día quieres cambiar?"
SIN_PLAN = "Aún no hay un plan. Dime para cuántas personas y lo preparo."
