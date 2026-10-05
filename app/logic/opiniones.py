"""Lo que opina el Jefe: valoraciones 👍/👎 y comentarios libres de TODAS las sesiones, en un solo sitio.

Es la entrada del sistema de agentes (`mas.py`). Se guarda en `.estado/opiniones.jsonl`, un fichero al que
solo se añaden líneas (una por opinión). Si `sesiones.DIRECTORIO` es None, se queda en memoria.
"""
import uuid
from datetime import datetime
from typing import Literal, Optional, TypeVar

from pydantic import BaseModel

from app.data import catalogo
from app.logic import sesiones

FICHERO = "opiniones.jsonl"


class Opinion(BaseModel):
    id: str
    fecha: str  # ISO, p. ej. "2026-10-05T18:30:00"
    session_id: str
    texto: Optional[str] = None  # comentario libre, o el motivo de un 👎
    valor: Optional[Literal["positivo", "negativo"]] = None  # solo en las valoraciones
    sujeto_tipo: Optional[Literal["receta", "producto"]] = None  # sobre qué opina, si se sabe
    sujeto_id: Optional[str] = None
    sujeto_nombre: Optional[str] = None
    tienda: Optional[str] = None


T = TypeVar("T", bound=BaseModel)
_memoria: dict[str, list[str]] = {}


def leer_lineas(fichero: str, modelo: type[T]) -> list[T]:
    if sesiones.DIRECTORIO is None:
        lineas = _memoria.get(fichero, [])
    else:
        ruta = sesiones.DIRECTORIO / fichero
        lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
    return [modelo.model_validate_json(l) for l in lineas if l.strip()]


def anadir_linea(fichero: str, dato: BaseModel) -> None:
    linea = dato.model_dump_json()
    if sesiones.DIRECTORIO is None:
        _memoria.setdefault(fichero, []).append(linea)
        return
    sesiones.DIRECTORIO.mkdir(parents=True, exist_ok=True)
    with open(sesiones.DIRECTORIO / fichero, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def _nombre(tipo: Optional[str], sujeto_id: Optional[str]) -> Optional[str]:
    if tipo == "receta":
        receta = catalogo.get_receta(sujeto_id)
        return receta.nombre if receta else None
    if tipo == "producto":
        producto = catalogo.get_producto(sujeto_id)
        return producto.nombre if producto else None
    return None


def registrar(
    session_id: str,
    texto: Optional[str] = None,
    valor: Optional[str] = None,
    sujeto_tipo: Optional[str] = None,
    sujeto_id: Optional[str] = None,
    tienda: Optional[str] = None,
    fecha: Optional[str] = None,
) -> Opinion:
    opinion = Opinion(
        id="o_" + uuid.uuid4().hex[:8],
        fecha=fecha or datetime.now().isoformat(timespec="seconds"),
        session_id=session_id,
        texto=(texto or "").strip() or None,
        valor=valor,
        sujeto_tipo=sujeto_tipo,
        sujeto_id=sujeto_id,
        sujeto_nombre=_nombre(sujeto_tipo, sujeto_id),
        tienda=tienda,
    )
    anadir_linea(FICHERO, opinion)
    return opinion


def todas() -> list[Opinion]:
    """Todas las opiniones. De cada valoración (misma sesión y mismo sujeto) solo cuenta la última:
    un 👎 sin motivo seguido del mismo 👎 con motivo es una sola opinión."""
    resultado: dict[object, Opinion] = {}
    for o in leer_lineas(FICHERO, Opinion):
        clave = (o.session_id, o.sujeto_tipo, o.sujeto_id) if o.valor else o.id
        resultado.pop(clave, None)
        resultado[clave] = o
    return list(resultado.values())
