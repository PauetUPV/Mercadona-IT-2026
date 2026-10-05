from typing import Optional

from fastapi import APIRouter, Query

from app.data import catalogo
from app.logic import apertura, chat, llm, sesiones
from app.logic.errores import NoEncontrado
from app.models.schemas import (
    ChatHistorial,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    ListaRequest,
    ListaResponse,
    Producto,
)

router = APIRouter()


@router.get("/health")
def health():
    """Comprobación de vida. `llm` dice si Gemini está activo o si todo va por el plan B."""
    return {"status": "ok", "llm": llm.LLM_MODEL if llm.disponible() else "desactivado (plan B)"}


@router.post("/chat", response_model=ChatResponse, response_model_exclude_none=True)
def enviar_mensaje(peticion: ChatRequest):
    """Un mensaje del usuario -> texto de Merche (+ plan solo si ha cambiado)."""
    return chat.procesar(peticion)


@router.get("/chat/{session_id}", response_model=ChatHistorial)
def ver_chat(session_id: str):
    """Historial y plan vigente de una sesión (por ejemplo, al recargar la página)."""
    sesion = sesiones.buscar(session_id)
    if sesion is None:
        raise NoEncontrado(f"Sesión {session_id} no existe")
    return ChatHistorial(session_id=sesion.id, historial=sesion.mensajes, plan=sesion.plan)


@router.get("/bienvenida", response_model=ChatResponse, response_model_exclude_none=True)
def bienvenida(session_id: Optional[str] = None, sesion_anterior: Optional[str] = None):
    """Primer mensaje de Merche al abrir la conversación (saludo, o pregunta de feedback si procede)."""
    return apertura.bienvenida(session_id, sesion_anterior)


@router.post("/lista", response_model=ListaResponse, response_model_exclude_none=True)
def guardar_lista(peticion: ListaRequest):
    """El usuario guarda su lista final de la compra."""
    return chat.guardar_lista(peticion)


@router.post("/feedback", response_model=FeedbackResponse, response_model_exclude_none=True)
def feedback(peticion: FeedbackRequest):
    """Valoración de una receta o producto (👍/👎). Provisional."""
    return chat.registrar_feedback(peticion)


@router.get("/productos", response_model=list[Producto])
def listar_productos(
    q: Optional[str] = None,
    categoria: Optional[str] = None,
    precio_max: Optional[float] = Query(None, ge=0),
    limite: int = Query(50, ge=1, le=200),
):
    """Búsqueda en el catálogo real (la usa el frontend para añadir productos)."""
    return catalogo.buscar_productos(q, categoria, precio_max, limite)
