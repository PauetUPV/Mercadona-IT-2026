"""Entiende el mensaje del usuario con reglas simples (sin LLM).

Es el plan B del agente: si Gemini no está disponible o falla, `agente.interpretar` usa esto.
Ambos devuelven la misma `Interpretacion`.
"""
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.logic.texto import DIAS_SEMANA, norm

Accion = Literal["plan", "cambiar_plato", "anadir_extra", "quitar_extra", "charla"]
Momento = Literal["comida", "cena"]
ETIQUETAS = ["carne", "pescado", "gluten", "lactosa", "huevo", "soja"]


class Interpretacion(BaseModel):
    """Lo que el usuario quiere, clasificado. Solo se rellena lo que el usuario ha dicho."""

    accion: Accion = "charla"
    comensales: Optional[int] = None
    presupuesto: Optional[float] = None  # en euros
    dias: Optional[list[str]] = None  # días del plan, p. ej. ["lunes", "martes"]
    momentos: Optional[list[Momento]] = None
    sin_cocinar: list[str] = Field(default_factory=list)  # días en los que no cocina
    excluir: list[str] = Field(default_factory=list)  # etiquetas a evitar (ETIQUETAS)
    dia: Optional[str] = None  # cambiar_plato: día del plato a cambiar
    momento: Optional[Momento] = None  # cambiar_plato: comida o cena
    producto: Optional[str] = None  # anadir_extra / quitar_extra: "leche", "café"...
    respuesta: Optional[str] = None  # texto corto para el usuario (sin cifras ni nombres de platos)
    conclusion: Optional[str] = None  # cierre opcional que va después del plan

    @property
    def aporta_datos(self) -> bool:
        return any(
            [self.comensales, self.presupuesto is not None, self.dias, self.momentos, self.sin_cocinar, self.excluir]
        )


NUMEROS = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8}
_NUM = r"(\d+|" + "|".join(NUMEROS) + r")"
_SIN_ACENTO = {norm(d): d for d in DIAS_SEMANA}
_DIA = r"(" + "|".join(_SIN_ACENTO) + r")"

# palabra (normalizada) -> etiquetas que se evitan
_DIETAS = {
    "vegetarian": ["carne", "pescado"],
    "vegan": ["carne", "pescado", "huevo", "lactosa"],
    "celiac": ["gluten"],
    "gluten": ["gluten"],
    "lactosa": ["lactosa"],
    "huevo": ["huevo"],
    "pescado": ["pescado"],
    "carne": ["carne"],
    "soja": ["soja"],
}


def _a_numero(valor: str) -> int:
    return int(valor) if valor.isdigit() else NUMEROS[valor]


def _dias_en(texto_norm: str) -> list[str]:
    """Días mencionados en el texto, en orden de semana y sin repetir."""
    encontrados = set()
    for m in re.finditer(_DIA + r"\s+a\s+" + _DIA, texto_norm):  # "lunes a viernes"
        a, b = DIAS_SEMANA.index(_SIN_ACENTO[m.group(1)]), DIAS_SEMANA.index(_SIN_ACENTO[m.group(2)])
        encontrados.update(DIAS_SEMANA[a : b + 1] if a <= b else DIAS_SEMANA[a:] + DIAS_SEMANA[: b + 1])
    for m in re.finditer(r"\b" + _DIA + r"\b", texto_norm):
        encontrados.add(_SIN_ACENTO[m.group(1)])
    if re.search(r"fin de semana", texto_norm):
        encontrados.update(["sábado", "domingo"])
    elif re.search(r"entre semana", texto_norm):
        encontrados.update(DIAS_SEMANA[:5])
    elif re.search(r"\bsemana\b", texto_norm):
        encontrados.update(DIAS_SEMANA)
    m = re.search(r"\b(\d+)\s+dias\b", texto_norm)
    if m:
        encontrados.update(DIAS_SEMANA[: min(int(m.group(1)), 7)])
    return [d for d in DIAS_SEMANA if d in encontrados]


def _excluir_en(n: str) -> list[str]:
    etiquetas: list[str] = []
    for patron in (
        r"soy (vegetarian|vegan)\w*",
        r"(vegetarian|vegan)\w*",
        r"(?:sin|alergi\w*\s+(?:a|al|a la|a los)|intoleran\w*\s+(?:a|al|a la))\s+(gluten|lactosa|huevo|pescado|soja)",
        r"celiac\w*",
        r"no (?:como|quiero|puedo comer|tomo)\s+(?:nada de\s+)?(carne|pescado|huevos?|gluten|lactosa|soja)",
    ):
        for m in re.finditer(patron, n):
            clave = m.group(1) if m.groups() else m.group(0)
            clave = clave.rstrip("s") if clave.startswith("huevo") else clave
            for palabra, tags in _DIETAS.items():
                if clave.startswith(palabra):
                    etiquetas += [t for t in tags if t not in etiquetas]
    return etiquetas


def _producto_tras(verbo_re: str, n: str) -> Optional[str]:
    m = re.search(r"\b(?:" + verbo_re + r")\s+(?:(?:tambien|ademas)\s+)?(?:(?:un|una|unos|unas|el|la|los|las|mas|algo de)\s+)?(.+)", n)
    if not m:
        return None
    producto = re.split(r"\s+(?:a la|al|a mi|de la|para la|por favor|que)\b|[.,;!?]", m.group(1))[0].strip()
    return producto or None


def interpretar(mensaje: str) -> Interpretacion:
    res = Interpretacion()
    n = norm(mensaje)

    m = re.search(r"\b(?:somos|seremos|para)\s+" + _NUM + r"\b(?!\s+(?:pareja|familia))", n) or re.search(
        r"\b" + _NUM + r"\s+(?:personas|comensales|adultos|ninos|raciones)\b", n
    )
    if m:
        res.comensales = _a_numero(m.group(1))
    elif re.search(r"\b(?:pareja|los dos|mi marido y yo|mi mujer y yo)\b", n):
        res.comensales = 2

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:€|euros?|eur\b)", n) or re.search(
        r"presupuesto\s+(?:maximo\s+)?(?:de\s+)?(\d+(?:[.,]\d+)?)", n
    )
    if m:
        res.presupuesto = float(m.group(1).replace(",", "."))

    # Cláusulas "no cocino": sus días no se añaden al plan, solo se marcan
    resto = []
    for clausula in re.split(r"[.;\n,]", mensaje):
        cn = norm(clausula)
        if "no cocin" in cn:
            res.sin_cocinar += [d for d in _dias_en(cn) if d not in res.sin_cocinar]
        else:
            resto.append(cn)
    dias = _dias_en(" . ".join(resto))
    res.dias = dias or None
    res.excluir = _excluir_en(n)

    comida, cena = re.search(r"\bcomidas?\b|almuerzo", n), re.search(r"\bcenas?\b", n)
    if comida and cena:
        res.momentos = ["comida", "cena"]
    elif cena:
        res.momentos = ["cena"]

    if re.search(r"\b(cambia|cambiame|cambiar|sustituye|sustituir|otro plato|otra cosa|no me gusta|no quiero)\b", n) and not res.excluir:
        if len(dias) == 1:
            res.accion, res.dia = "cambiar_plato", dias[0]
            res.momento = "cena" if cena and not comida else ("comida" if comida and not cena else None)
            res.dias = res.momentos = None  # no es una petición de nuevo plan
            return res
        res.accion = "charla"
        res.respuesta = "¿Qué día quieres cambiar?"
        return res

    if re.fullmatch(r"\W*(gracias|muchas gracias|vale|ok|perfecto|genial)\W*", n):
        res.respuesta = "¡De nada! Aquí estoy para lo que necesites."
        return res
    if re.fullmatch(r"\W*(hola|buenas|buenos dias|buenas tardes|hey)\W*", n):
        res.respuesta = "¡Hola! Soy Merche. Dime para cuántas personas es el plan y lo preparo."
        return res

    anadir = _producto_tras(r"anade|anademe|apuntame|apunta|ponme|pon", n)
    quitar = _producto_tras(r"quita|quitame|elimina|borra", n)
    if anadir and not res.aporta_datos:
        res.accion, res.producto = "anadir_extra", anadir
    elif quitar and not res.aporta_datos and not _dias_en(quitar):
        res.accion, res.producto = "quitar_extra", quitar
    elif res.aporta_datos or re.search(r"\b(plan|menu|planifica\w*|organiza\w*|semana)\b", n):
        res.accion = "plan"  # incluye peticiones genéricas: luego se pregunta lo que falte
    return res
