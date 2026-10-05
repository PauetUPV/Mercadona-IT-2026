"""Textos del asistente por plantilla: plan B cuando Gemini no está disponible.

Recibe los mismos `hechos` que el redactor con LLM (ver `chat._hechos_*`). No cita precios ni totales,
salvo el importe mínimo cuando el presupuesto es imposible.
"""
from typing import Optional


def euros(x: float) -> str:
    return f"{x:.2f}".replace(".", ",") + " €"


def _platos(platos: dict[str, list[str]]) -> str:
    return "; ".join(f"{dia}: {' y '.join(nombres)}" for dia, nombres in platos.items())


def redactar(h: dict) -> tuple[str, Optional[str]]:
    tipo = h.get("tipo")
    avisos = " ".join(h.get("avisos", []))
    conclusion = None

    if tipo == "plan":
        texto = f"¡Listo! He preparado el plan para {h['comensales']} persona(s). {_platos(h['platos'])}."
        conclusion = "¿Qué opinas?"
    elif tipo == "cambio_plato":
        texto = f"He cambiado el plato del {h['dia']}: ahora es {h['nuevo']}."
        conclusion = "¿Te encaja?"
    elif tipo == "extra_anadido":
        texto = f"Añadido: {h['producto']}."
    elif tipo == "extra_quitado":
        texto = f"Quitado: {h['producto']}."
    elif tipo == "inviable":
        texto = (
            f"Con {euros(h['presupuesto'])} no puede ser para {h['comensales']} persona(s) y {h['n_comidas']} comida(s): "
            f"lo más barato que encuentro ronda los {euros(h['importe_minimo_aproximado'])}. "
            "Puedes subir el presupuesto, quitar días o ser menos personas."
        )
    elif tipo == "sin_alternativa":
        texto = h.get("motivo", "No tengo otro plato parecido que cumpla las condiciones.")
    elif tipo == "rechazo":
        texto = h.get("motivo", "No puedo hacer eso.")
    elif tipo == "pregunta_comensales":
        texto = "¿Para cuántas personas es el plan? Puedes decirme también tu presupuesto y qué días no cocinas."
    elif tipo == "sin_plan":
        texto = "Aún no hay un plan. Dime para cuántas personas y lo preparo."
    elif tipo == "producto_no_encontrado":
        texto = f"No he encontrado «{h['busqueda']}» en el catálogo."
    else:
        texto = "No te he entendido. Dime para cuántas personas, tu presupuesto y qué días no cocinas, o pídeme cambiar un plato (p. ej. «cambia el martes»)."
    return (f"{texto} {avisos}".strip(), conclusion)
