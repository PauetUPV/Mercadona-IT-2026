from typing import Optional

from pydantic import BaseModel


class PeticionPlan(BaseModel):
    comensales: int
    presupuesto: Optional[float] = None
    dias: list[str]
    restricciones: Optional[str] = None  # "el martes no cocino"


class Receta(BaseModel):
    id: str
    nombre: str
    tipo: str  # "cocinar" o "listo_para_comer"
    precio_estimado: float


class PlanResponse(BaseModel):
    dias: dict[str, Receta]
    carrito: list[str]


class PeticionSustitucion(BaseModel):
    dia: str
    receta_id: str
    motivo: Optional[str] = None
