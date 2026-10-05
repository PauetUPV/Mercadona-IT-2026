"""Textos del asistente por plantilla: plan B cuando Gemini no está disponible.

Recibe los mismos `hechos` que el redactor con LLM (ver `chat._hechos_*`). No cita precios ni totales,
salvo el importe mínimo cuando el presupuesto es imposible.
"""
from typing import Optional

from app.logic import ideas


def euros(x: float) -> str:
    return f"{x:.2f}".replace(".", ",") + " €"


def _platos(platos: dict[str, list[str]]) -> str:
    return "; ".join(f"{dia}: {' y '.join(nombres)}" for dia, nombres in platos.items())


def _no_exacto(h: dict) -> str:
    """Aviso cuando el plato pedido no existe tal cual y se usa el más parecido."""
    return f"No tengo «{h['pedido']}» tal cual; te pongo {h['plato']}. " if h.get("parecido") else ""


def redactar(h: dict) -> tuple[str, Optional[str]]:
    tipo = h.get("tipo")
    avisos = " ".join(h.get("avisos", []))
    conclusion = None

    if tipo == "plan":
        texto = f"¡Listo! He preparado el plan para {h['comensales']} persona(s). {_platos(h['platos'])}."
        if h.get("plato"):
            texto = _no_exacto(h) + texto
        conclusion = "¿Qué opinas?"
    elif tipo == "plato_puesto":
        texto = _no_exacto(h) + f"Hecho: el {h['dia']} toca {h['plato']}."
        conclusion = "¿Algo más?"
    elif tipo == "plato_no_encontrado":
        texto = f"No tengo «{h['busqueda']}» entre mis recetas."
        if h.get("alternativas"):
            texto += " Lo más parecido: " + " o ".join(h["alternativas"]) + "."
    elif tipo == "plato_excluido":
        texto = f"«{h['plato']}» lleva {' y '.join(h['etiquetas'])}, y me dijiste que lo evitas. Prueba con otro plato."
    elif tipo == "ideas":
        return ideas.texto(h)
    elif tipo == "opinion":
        texto = "Gracias por contárnoslo. Se lo he hecho llegar a Mercadona."
        conclusion = "¿Preparamos lo de la semana que viene?"
    elif tipo == "consulta":
        texto = h["texto"]
    elif tipo == "evitado":
        if h.get("sin_coincidencias"):
            texto = "Entendido, lo tendré en cuenta."
        else:
            texto = f"Entendido, no te pondré {' ni '.join(h['evitados'])}."
        if h.get("cambios"):
            texto += " He cambiado " + "; ".join(f"el {d} por {n}" for d, n in h["cambios"].items()) + "."
    elif tipo == "cambio_plato" and len(h.get("cambios", {})) > 1:
        partes = [f"el {d}, {n}" for d, n in h["cambios"].items()]
        texto = "Hecho. Ahora tienes " + "; ".join(partes[:-1]) + " y " + partes[-1] + "."
        if h.get("no_estaban"):
            texto += f" (El {' ni el '.join(h['no_estaban'])} no estaba en tu plan.)"
        conclusion = "¿Te encaja?"
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
    elif tipo == "pregunta_comensales" and h.get("plato"):
        para = "y para qué día" if not h.get("dia_pedido") else ""
        texto = _no_exacto(h) + f"¡Apuntado: {h['plato']}! ¿Para cuántas personas es{(' ' + para) if para else ''}?"
    elif tipo == "pregunta_comensales":
        texto = "¿Para cuántas personas es el plan? Puedes decirme también tu presupuesto y qué días no cocinas."
    elif tipo == "sin_plan":
        texto = "Aún no hay un plan. Dime para cuántas personas y lo preparo."
    elif tipo == "producto_no_encontrado":
        texto = f"No he encontrado «{h['busqueda']}» en el catálogo."
    else:
        texto = "No te he entendido. Dime para cuántas personas, tu presupuesto y qué días no cocinas, o pídeme cambiar un plato (p. ej. «cambia el martes»)."
    return (f"{texto} {avisos}".strip(), conclusion)
