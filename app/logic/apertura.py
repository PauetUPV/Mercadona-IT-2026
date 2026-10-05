"""Merche toma la iniciativa: saludo al abrir la app y preguntas de feedback ("¿qué tal salió...?")."""
from typing import Optional

from app.logic import sesiones, sugerencias
from app.logic.feedback import sujeto_pendiente
from app.models.schemas import ChatResponse, MensajeChat


def bienvenida(session_id: Optional[str], sesion_anterior: Optional[str] = None) -> ChatResponse:
    """Primer mensaje de Merche al abrir la conversación; depende del estado de la sesión."""
    sesion = sesiones.obtener(session_id, sesion_anterior)
    pendiente = sujeto_pendiente(sesion)
    chips: list[str] = []
    if pendiente:
        ultima = sesion.listas[-1].get("sujetos", []) if sesion.listas else []
        valorados = {f["sujeto"]["id"] for f in sesion.feedback}
        primera = not any(s["id"] in valorados for s in ultima)  # aún no ha contado nada de esta compra
        mensaje = (
            f"¡Hola otra vez! ¿Qué tal fue la compra? Empecemos por «{pendiente.nombre}»: ¿qué tal salió?"
            if primera else f"¡Hola otra vez! ¿Qué tal salió «{pendiente.nombre}»?"
        )
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
