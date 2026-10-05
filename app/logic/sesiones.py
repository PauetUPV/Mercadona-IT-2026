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
    fijos: list[dict] = Field(default_factory=list)  # platos pedidos por el usuario: {dia, momento, receta_id}
    # Estado del plan
    plan: Optional[PlanResponse] = None  # plan vigente (el del frontend manda si lo ha editado)
    listas: list[dict] = Field(default_factory=list)  # listas guardadas (/lista), con qué platos/productos se compraron
    feedback: list[dict] = Field(default_factory=list)  # valoraciones (/feedback)
    # Gustos aprendidos del feedback
    favoritas: list[str] = Field(default_factory=list)  # recetas con 👍: se vuelven a proponer
    productos_favoritos: list[str] = Field(default_factory=list)  # productos con 👍: se prefieren al añadir extras
    productos_rechazados: list[str] = Field(default_factory=list)  # productos con 👎: no se vuelven a elegir
    prefiere_barato: bool = False  # dijo "muy caro"
    prefiere_facil: bool = False  # dijo "mucho trabajo" o "algo rápido"
    prefiere_ligero: bool = False  # pidió comer "más ligero"
    # De qué receta se habló por última vez, para entender "¿y qué lleva?" sin repetir el nombre
    ultima_receta: Optional[str] = None
    # Comentarios sobre productos o la compra que se "enviaron a Mercadona"
    opiniones: list[dict] = Field(default_factory=list)


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


# Lo que se conserva al empezar una conversación nueva ("Volver"): la memoria a largo plazo del usuario.
# La conversación, el plan y los datos de esta semana (personas, presupuesto, días...) empiezan de cero.
CAMPOS_DURADEROS = (
    "listas", "feedback", "rechazadas", "favoritas", "productos_favoritos", "productos_rechazados",
    "prefiere_barato", "prefiere_facil", "excluir",
)


def obtener(session_id: Optional[str], sesion_anterior: Optional[str] = None) -> Sesion:
    """Devuelve la sesión; si no existe (o no se pasa id) la crea. Si es nueva y viene de otra
    (`sesion_anterior`, el usuario pulsó "Volver"), hereda su memoria duradera."""
    sid = session_id or uuid.uuid4().hex[:8]
    sesion = buscar(sid)
    if sesion is None:
        sesion = _sesiones[sid] = Sesion(id=sid)
        anterior = buscar(sesion_anterior) if sesion_anterior and sesion_anterior != sid else None
        if anterior:
            for campo in CAMPOS_DURADEROS:
                setattr(sesion, campo, getattr(anterior, campo).copy() if isinstance(getattr(anterior, campo), list) else getattr(anterior, campo))
    return sesion


def guardar(sesion: Sesion) -> None:
    _sesiones[sesion.id] = sesion
    fichero = _fichero(sesion.id)
    if fichero:
        fichero.parent.mkdir(parents=True, exist_ok=True)
        tmp = fichero.with_suffix(".tmp")
        tmp.write_text(sesion.model_dump_json(indent=1), encoding="utf-8")
        tmp.replace(fichero)
