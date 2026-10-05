from typing import Literal, Optional

from pydantic import BaseModel, Field


class Producto(BaseModel):
    id: str
    nombre: str
    precio: float  # precio unitario (unit_price)
    precio_referencia: Optional[float] = None
    formato_referencia: Optional[str] = None  # kg, l, ud...
    tamano: Optional[float] = None
    formato_tamano: Optional[str] = None
    categoria: str  # nivel 0, ej. "Carne"
    subcategoria: Optional[str] = None
    thumbnail: Optional[str] = None
    url: Optional[str] = None


class Ingrediente(BaseModel):
    producto_id: str
    unidades: float = 1  # unidades de producto por receta (para `raciones` raciones)


class Receta(BaseModel):
    id: str
    nombre: str
    tipo: str  # "cocinar" o "listo_para_comer"
    raciones: int = 2
    ingredientes: list[Ingrediente] = Field(default_factory=list)
    extras: list[str] = Field(default_factory=list)  # se suponen en casa (sal, agua...); no se cobran
    precio_estimado: float = 0.0  # se calcula a partir de los ingredientes


class PeticionPlan(BaseModel):
    comensales: int = Field(gt=0)
    presupuesto: Optional[float] = None
    dias: list[str] = Field(min_length=1)
    restricciones: Optional[str] = None  # "el martes no cocino"


class LineaCarrito(BaseModel):
    producto: Producto
    unidades: int
    subtotal: float


class Carrito(BaseModel):
    lineas: list[LineaCarrito] = Field(default_factory=list)
    total: float = 0.0


class PlanResponse(BaseModel):
    id: str = ""
    dias: dict[str, Receta]
    carrito: Carrito
    total: float = 0.0
    extras: list[str] = Field(default_factory=list)
    comensales: Optional[int] = None
    presupuesto: Optional[float] = None
    dentro_presupuesto: Optional[bool] = None


class PeticionSustitucion(BaseModel):
    plan: PlanResponse
    dia: str
    comensales: Optional[int] = Field(None, gt=0)  # si falta, se usa plan.comensales
    motivo: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: Optional[str] = None  # si falta se crea; si el cliente envía uno nuevo, se usa tal cual
    mensaje: str = Field(min_length=1)
    # Opcionales: si se envían, mandan sobre lo interpretado del texto
    comensales: Optional[int] = Field(None, gt=0)
    presupuesto: Optional[float] = Field(None, ge=0)
    dias: Optional[list[str]] = None


class ChatResponse(BaseModel):
    session_id: str
    mensaje: str  # texto para la burbuja del chat
    plan: Optional[PlanResponse] = None  # plan vigente (fuente de verdad para pintar)


class MensajeChat(BaseModel):
    rol: Literal["usuario", "asistente"]
    texto: str


class ChatHistorial(BaseModel):
    session_id: str
    historial: list[MensajeChat]
    plan: Optional[PlanResponse] = None
