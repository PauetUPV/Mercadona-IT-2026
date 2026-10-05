from fastapi import APIRouter
from pydantic import BaseModel

# Importaciones de tus compañeros
from app.data.catalogo import get_recetas
from app.logic.planificador import generar_plan
from app.logic.sustituciones import sustituir_plato
from app.models.schemas import PeticionPlan, PeticionSustitucion

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

@router.post("/plan")
def crear_plan(peticion: PeticionPlan):
    return {"dias": generar_plan(peticion), "carrito": []}

@router.get("/catalogo")
def ver_catalogo():
    return get_recetas()

@router.post("/sustituir")
def sustituir(peticion: PeticionSustitucion):
    return {"dia": peticion.dia, "receta": sustituir_plato(peticion)}

@router.get("/dashboard")
def dashboard():
    return {"planes_generados": 0, "ahorro_medio": 0.0, "platos_mas_pedidos": []}

# ==========================================
# TU RUTA DEL CHATBOT
# ==========================================
@router.post("/chat")
def chat_mercadona(peticion: PeticionChat):
    # ¡Magia! Toda la complejidad de Gemini se queda oculta en llm.py
    texto_ia = consultar_llm(peticion.texto)
    
    return {"respuesta_bot": texto_ia}