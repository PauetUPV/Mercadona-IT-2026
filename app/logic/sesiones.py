"""Sesiones de chat en memoria (se pierden al reiniciar el servidor)."""
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.models.schemas import MensajeChat, PlanResponse


@dataclass
class Sesion:
    id: str
    mensajes: list[MensajeChat] = field(default_factory=list)
    comensales: Optional[int] = None
    presupuesto: Optional[float] = None
    dias: Optional[list[str]] = None
    restricciones: list[str] = field(default_factory=list)
    plan: Optional[PlanResponse] = None


_sesiones: dict[str, Sesion] = {}


def reset() -> None:
    _sesiones.clear()


def obtener(session_id: Optional[str]) -> Sesion:
    """Devuelve la sesión; si no existe (o no se pasa id) la crea."""
    sid = session_id or uuid.uuid4().hex[:8]
    if sid not in _sesiones:
        _sesiones[sid] = Sesion(id=sid)
    return _sesiones[sid]


def buscar(session_id: str) -> Optional[Sesion]:
    return _sesiones.get(session_id)
