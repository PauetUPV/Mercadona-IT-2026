from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.data import catalogo
from app.logic import apertura, chat, llm, sesiones
from app.logic.errores import DatosInvalidos, NoEncontrado
from app.models.schemas import (
    ChatHistorial,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    ListaRequest,
    ListaResponse,
    Producto,
    VozResponse,
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


# Formatos de audio que entiende Gemini (la interfaz envía WAV)
TIPOS_AUDIO = {"audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/flac",
               "audio/aac", "audio/aiff", "audio/x-aiff"}
MAX_AUDIO = 10 * 1024 * 1024  # 10 MB (~5 min de WAV a 16 kHz)


@router.post(
    "/voz",
    response_model=VozResponse,
    openapi_extra={"requestBody": {"required": True, "content": {"audio/wav": {"schema": {"type": "string", "format": "binary"}}}}},
)
async def voz(request: Request):
    """Mensaje de voz -> texto (con Gemini). El cuerpo es el audio tal cual (Content-Type: audio/wav, audio/mpeg...).
    Después, el frontend envía ese texto a /chat como un mensaje normal."""
    mime = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if mime not in TIPOS_AUDIO:
        raise DatosInvalidos(f"Formato de audio no admitido ({mime or 'sin Content-Type'}). Usa WAV, MP3, OGG, FLAC o AAC.")
    audio = await request.body()
    if not audio:
        raise DatosInvalidos("El audio está vacío")
    if len(audio) > MAX_AUDIO:
        raise DatosInvalidos("El audio es demasiado largo")
    texto = await run_in_threadpool(llm.transcribir, audio, mime)
    if texto is None:
        return JSONResponse(status_code=503, content={"detail": "Ahora mismo no puedo escuchar audios. Escríbemelo, por favor."})
    if not texto:
        raise DatosInvalidos("No te he entendido. ¿Puedes repetirlo?")
    return VozResponse(texto=texto)


@router.get("/productos", response_model=list[Producto])
def listar_productos(
    q: Optional[str] = None,
    categoria: Optional[str] = None,
    precio_max: Optional[float] = Query(None, ge=0),
    limite: int = Query(50, ge=1, le=200),
):
    """Búsqueda en el catálogo real (la usa el frontend para añadir productos)."""
    return catalogo.buscar_productos(q, categoria, precio_max, limite)
