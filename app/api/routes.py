from fastapi import APIRouter
from pydantic import BaseModel

# Importaciones de tus compañeros
from app.data.catalogo import get_recetas
from typing import Optional

from fastapi import APIRouter, Query

from app.data import catalogo
from app.logic import chat, historial, sesiones
from app.logic.errores import NoEncontrado
from app.logic.planificador import generar_plan
from app.logic.sustituciones import sustituir_plato
from app.models.schemas import (
    ChatHistorial,
    ChatRequest,
    ChatResponse,
    PeticionPlan,
    PeticionSustitucion,
    PlanResponse,
    Producto,
    Receta,
)

# TU IMPORTACIÓN DE IA
from app.logic.llm import consultar_llm

router = APIRouter()

# Definimos qué JSON esperas recibir en el chat
class PeticionChat(BaseModel):
    texto: str
    usuario_id: str

# ==========================================
# RUTAS DE TUS COMPAÑEROS
# ==========================================
@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/plan", response_model=PlanResponse)
def crear_plan(peticion: PeticionPlan):
    plan = generar_plan(peticion)
    historial.registrar_plan(plan, peticion.presupuesto)
    return plan


@router.get("/catalogo", response_model=list[Receta])
def ver_catalogo():
    """Recetas disponibles (mock)."""
    return catalogo.get_recetas()


@router.get("/categorias")
def ver_categorias():
    return catalogo.get_categorias()


@router.get("/productos", response_model=list[Producto])
def listar_productos(
    q: Optional[str] = None,
    categoria: Optional[str] = None,
    precio_max: Optional[float] = Query(None, ge=0),
    limite: int = Query(50, ge=1, le=200),
):
    return catalogo.buscar_productos(q, categoria, precio_max, limite)


@router.get("/productos/{producto_id}", response_model=Producto)
def ver_producto(producto_id: str):
    producto = catalogo.get_producto(producto_id)
    if producto is None:
        raise NoEncontrado(f"Producto {producto_id} no existe")
    return producto


@router.post("/sustituir", response_model=PlanResponse)
def sustituir(peticion: PeticionSustitucion):
    plan = sustituir_plato(peticion)
    historial.registrar_sustitucion(plan)
    return plan

@router.get("/dashboard")
def dashboard():
    return historial.metricas()


@router.post("/chat", response_model=ChatResponse)
def enviar_mensaje(peticion: ChatRequest):
    """Un mensaje del usuario -> texto del asistente + plan vigente."""
    return chat.procesar(peticion)


@router.get("/chat/{session_id}", response_model=ChatHistorial)
def ver_chat(session_id: str):
    """Historial y plan actual de una sesión (por ejemplo, al recargar la página)."""
    sesion = sesiones.buscar(session_id)
    if sesion is None:
        raise NoEncontrado(f"Sesión {session_id} no existe")
    return ChatHistorial(session_id=sesion.id, historial=sesion.mensajes, plan=sesion.plan)
