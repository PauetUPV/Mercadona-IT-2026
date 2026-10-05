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


class OpinionRequest(BaseModel):
    """Queja o sugerencia en texto libre ("las latas de atún vienen con demasiado aceite")."""

    session_id: str
    texto: str = Field(min_length=1)
    sujeto: Optional[SujetoFeedback] = None  # si la interfaz sabe sobre qué producto o receta opina
    tienda: Optional[str] = None


class OpinionResponse(BaseModel):
    mensaje: str


# --- Informe para Mercadona (lo generan los agentes de `app/logic/mas.py`) ---

TipoOpinion = Literal["queja", "sugerencia", "elogio"]
Categoria = Literal["seguridad", "calidad", "sabor", "formato", "precio", "disponibilidad", "receta", "otro"]


class Tema(BaseModel):
    """Opiniones que dicen lo mismo (mismo sujeto, categoría y tipo), agrupadas."""

    sujeto_tipo: Literal["producto", "receta", "general"]
    sujeto: str  # "Atún", "Pollo al horno con patatas"...
    producto_id: Optional[str] = None  # producto del catálogo; aproximado si el cliente no dio uno concreto
    categoria: Categoria
    tipo: TipoOpinion
    menciones: int
    clientes: int  # sesiones distintas
    tiendas: dict[str, int] = Field(default_factory=dict)  # tienda -> menciones (solo si se conoce)
    desde: str  # fecha (AAAA-MM-DD) de la primera mención
    hasta: str
    alerta: bool = False
    ejemplos: list[str] = Field(default_factory=list)  # hasta 3 resúmenes
    accion: Optional[str] = None  # qué propone hacer el agente redactor


class Puntuacion(BaseModel):
    tipo: Literal["receta", "producto"]
    id: str
    nombre: str
    positivos: int = 0
    negativos: int = 0


class Informe(BaseModel):
    generado: str
    opiniones: int
    clientes: int
    resumen: str
    temas: list[Tema]  # alertas primero, luego por número de menciones
    valoraciones: list[Puntuacion]  # 👍/👎 por receta o producto, lo peor valorado primero
