"""Merche toma la iniciativa: saludo al abrir la app y preguntas de feedback ("¿qué tal salió...?")."""
from typing import Optional

from app.logic import sesiones, sugerencias
from app.logic.sesiones import Sesion
from app.models.schemas import ChatResponse, MensajeChat, SujetoPendiente

MAX_FEEDBACK_POR_LISTA = 3  # para no agobiar: como mucho 3 platos por lista guardada


def valorados(sesion: Sesion) -> set[str]:
    return {f["sujeto"]["id"] for f in sesion.feedback if f["sujeto"]["tipo"] == "receta"}


def sujeto_pendiente(sesion: Sesion) -> Optional[SujetoPendiente]:
    """Siguiente plato del plan por valorar. Solo después de guardar una lista (es lo que sí se compró)."""
    if sesion.plan is None or not sesion.listas:
        return None
    hechos = valorados(sesion)
    if len(hechos) >= MAX_FEEDBACK_POR_LISTA * len(sesion.listas):
        return None
    for recetas in sesion.plan.dias.values():
        for r in recetas:
            if r.id not in hechos:
                imagen = r.ingredientes[0].producto.thumbnail if r.ingredientes else None
                return SujetoPendiente(tipo="receta", id=r.id, nombre=r.nombre, imagen=imagen)
    return None


def bienvenida(session_id: Optional[str]) -> ChatResponse:
    """Primer mensaje de Merche al abrir la conversación; depende del estado de la sesión."""
    sesion = sesiones.obtener(session_id)
    pendiente = sujeto_pendiente(sesion)
    chips: list[str] = []
    if pendiente:
        mensaje = f"¡Hola otra vez! ¿Qué tal salió «{pendiente.nombre}»?"
    elif sesion.listas:
        mensaje = "¡Gracias por tus valoraciones! ¿Preparamos la semana que viene?"
        chips = [sugerencias.PEDIR_PLAN]
    elif sesion.plan:
        mensaje = "Tienes un plan en marcha. ¿Quieres cambiar algo?"
        chips = sugerencias._chips_del_plan(sesion)
    else:
        mensaje = "¡Hola! Soy Merche y te ayudo a planificar la comida de la semana con productos de Mercadona. ¿Para cuántas personas es?"
        chips = sugerencias.PEDIR_COMENSALES
    if not sesion.mensajes or sesion.mensajes[-1].texto != mensaje:  # no duplicar si recargan la página
        sesion.mensajes.append(MensajeChat(rol="asistente", texto=mensaje))
        sesiones.guardar(sesion)
    return ChatResponse(
        session_id=sesion.id, mensaje=mensaje, sugerencias=chips[: sugerencias.MAX_CHIPS] or None, feedback=pendiente
    )
