from typing import Literal, Optional

from pydantic import BaseModel, Field


class Producto(BaseModel):
    id: str
    nombre: str
    precio: float  # precio de UN envase (unit_price)
    precio_referencia: Optional[float] = None
    formato_referencia: Optional[str] = None  # kg, l, ud...
    tamano: Optional[float] = None
    formato_tamano: Optional[str] = None
    categoria: str  # nivel 0, ej. "Carne"
    subcategoria: Optional[str] = None
    thumbnail: Optional[str] = None
    url: Optional[str] = None


class Ingrediente(BaseModel):
    """Fracción (o múltiplo) de un envase de `producto` que gasta una receta o un extra."""

    unidades: float = 1
    producto: Producto


class Receta(BaseModel):
    id: str
    nombre: str
    tipo: Literal["cocinar", "listo_para_comer"]
    momento: Optional[Literal["comida", "cena"]] = None
    raciones: int = 2  # en un plan, coincide con los comensales (las unidades ya vienen escaladas)
    ingredientes: list[Ingrediente] = Field(default_factory=list)
    instrucciones: Optional[str] = None
    en_casa: list[str] = Field(default_factory=list)  # se supone que ya hay en casa (sal, agua...)
    etiquetas: list[str] = Field(default_factory=list)  # carne, pescado, gluten, lactosa, huevo, soja
    precio_estimado: float = 0.0  # coste de los ingredientes para `raciones`


class PlanResponse(BaseModel):
    id: str = ""
    dias: dict[str, list[Receta]]
    extras: list[Ingrediente] = Field(default_factory=list)  # productos sueltos (leche, café...)
    en_casa: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: Optional[str] = None  # si falta se crea; si el cliente envía uno nuevo, se usa tal cual
    mensaje: str = Field(min_length=1)
    plan: Optional[PlanResponse] = None  # el plan tal como lo ve el usuario, si lo ha editado
    # Al empezar de cero ("Volver"), el id de la sesión anterior: la nueva hereda su memoria (listas, gustos, dieta)
    sesion_anterior: Optional[str] = None


class SujetoPendiente(BaseModel):
    """Algo que Merche quiere que el usuario valore (el frontend pinta 👍/👎)."""

    tipo: Literal["receta", "producto"]
    id: str
    nombre: str
    imagen: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    mensaje: str  # texto para la burbuja del chat
    mensaje_conclusion: Optional[str] = None  # va DESPUÉS del plan
    plan: Optional[PlanResponse] = None  # solo si ha cambiado; si falta, el frontend conserva el último
    sugerencias: Optional[list[str]] = None  # chips de respuesta rápida (máx. 4); al pulsar, se envían como `mensaje`
    feedback: Optional[SujetoPendiente] = None  # Merche pregunta qué tal salió algo (la pregunta va en `mensaje`)
    enviado: Optional["Enviado"] = None  # comentario del usuario "enviado a Mercadona": el frontend pinta una tarjeta


class MensajeChat(BaseModel):
    rol: Literal["usuario", "asistente"]
    texto: str


class ChatHistorial(BaseModel):
    session_id: str
    historial: list[MensajeChat]
    plan: Optional[PlanResponse] = None


class LineaLista(BaseModel):
    producto_id: str
    unidades: int = Field(ge=1)  # envases enteros, ya editados por el usuario


class ListaRequest(BaseModel):
    session_id: str
    plan_id: Optional[str] = None
    nombre: Optional[str] = None
    lineas: list[LineaLista]


class ListaResponse(BaseModel):
    lista_id: str
    mensaje: Optional[str] = None
    sugerencias: Optional[list[str]] = None  # tiendas para elegir dónde hacer la compra (solo informativo)


class Enviado(BaseModel):
    """Comentario del usuario que Merche "hace llegar" a Mercadona (no se envía a ningún sitio real)."""

    destinatario: str = "Mercadona"
    puntos: list[str]  # lo esencial del comentario, en frases cortas


class SujetoFeedback(BaseModel):
    tipo: Literal["receta", "producto"]
    id: str


class FeedbackRequest(BaseModel):
    session_id: str
    sujeto: SujetoFeedback
    valor: Literal["positivo", "negativo"]
    motivo: Optional[str] = None


class FeedbackResponse(BaseModel):
    mensaje: Optional[str] = None
    sugerencias: Optional[list[str]] = None
    feedback: Optional[SujetoPendiente] = None  # siguiente cosa a valorar, si Merche quiere seguir preguntando


ChatResponse.model_rebuild()  # `enviado` usa Enviado, definido más abajo
