"""Estado de cada conversación. Es la memoria del agente entre mensajes.

Se guarda en memoria y se escribe en disco (`.estado/<session_id>.json`) tras cada cambio, así que
sobrevive a reinicios del servidor (`uvicorn --reload`). Para desactivar el disco: `DIRECTORIO = None`.
"""
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.models.schemas import MensajeChat, PlanResponse

DIRECTORIO: Optional[Path] = Path(os.getenv("STATE_DIR", ".estado"))


class Sesion(BaseModel):
    id: str
    # Conversación
    mensajes: list[MensajeChat] = Field(default_factory=list)
    # Preferencias (lo que el usuario nos ha ido diciendo)
    comensales: Optional[int] = None
    presupuesto: Optional[float] = None
    dias: Optional[list[str]] = None
    momentos: list[str] = Field(default_factory=lambda: ["comida"])
    sin_cocinar: list[str] = Field(default_factory=list)  # días en los que no cocina
    excluir: list[str] = Field(default_factory=list)  # etiquetas: dietas y alergias
    rechazadas: list[str] = Field(default_factory=list)  # ids de recetas que no le gustaron
    # Estado del plan
    plan: Optional[PlanResponse] = None  # plan vigente (el del frontend manda si lo ha editado)
    listas: list[dict] = Field(default_factory=list)  # listas guardadas (/lista)
    feedback: list[dict] = Field(default_factory=list)  # valoraciones (/feedback)


_sesiones: dict[str, Sesion] = {}


def _fichero(session_id: str) -> Optional[Path]:
    if DIRECTORIO is None:
        return None
    return DIRECTORIO / (re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:80] + ".json")


def reset() -> None:
    """Olvida las sesiones en memoria (no borra el disco)."""
    _sesiones.clear()


def buscar(session_id: str) -> Optional[Sesion]:
    if session_id in _sesiones:
        return _sesiones[session_id]
    fichero = _fichero(session_id)
    if fichero and fichero.exists():
        _sesiones[session_id] = Sesion.model_validate_json(fichero.read_text(encoding="utf-8"))
        return _sesiones[session_id]
    return None


def obtener(session_id: Optional[str]) -> Sesion:
    """Devuelve la sesión; si no existe (o no se pasa id) la crea."""
    sid = session_id or uuid.uuid4().hex[:8]
    sesion = buscar(sid)
    if sesion is None:
        sesion = _sesiones[sid] = Sesion(id=sid)
    return sesion


def guardar(sesion: Sesion) -> None:
    _sesiones[sesion.id] = sesion
    fichero = _fichero(sesion.id)
    if fichero:
        fichero.parent.mkdir(parents=True, exist_ok=True)
        tmp = fichero.with_suffix(".tmp")
        tmp.write_text(sesion.model_dump_json(indent=1), encoding="utf-8")
        tmp.replace(fichero)
