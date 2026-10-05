from fastapi import APIRouter

from app.data.catalogo import get_recetas
from app.logic.planificador import generar_plan
from app.logic.sustituciones import sustituir_plato
from app.models.schemas import PeticionPlan, PeticionSustitucion

router = APIRouter()


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
    # TODO: datos reales; de momento JSON estático
    return {"planes_generados": 0, "ahorro_medio": 0.0, "platos_mas_pedidos": []}
