"""Interpreta el mensaje del usuario con reglas simples (sin LLM).

PUNTO DE ENGANCHE PARA GEMINI: `interpretar()` debe devolver una `Interpretacion`.
Cuando haya LLM, basta con reimplementar esta función (el resto del chat no cambia).
"""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_SIN_ACENTO = {}  # se rellena abajo: "miercoles" -> "miércoles"

NUMEROS = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8}
_NUM = r"(\d+|" + "|".join(NUMEROS) + r")"


def norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


_SIN_ACENTO = {norm(d): d for d in DIAS_SEMANA}
_DIA = r"(" + "|".join(_SIN_ACENTO) + r")"


@dataclass
class Interpretacion:
    comensales: Optional[int] = None
    presupuesto: Optional[float] = None
    dias: Optional[list[str]] = None  # None = no se mencionan días
    sin_cocinar: list[str] = field(default_factory=list)  # días con "no cocino"
    clausulas_no_cocino: list[str] = field(default_factory=list)  # texto original, para `restricciones`
    sustituir_dia: Optional[str] = None
    quiere_sustituir: bool = False

    @property
    def aporta_datos(self) -> bool:
        return any([self.comensales, self.presupuesto is not None, self.dias, self.sin_cocinar])


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


def interpretar(mensaje: str) -> Interpretacion:
    res = Interpretacion()
    n = norm(mensaje)

    m = re.search(r"\b(?:somos|seremos|para)\s+" + _NUM + r"\b", n) or re.search(
        r"\b" + _NUM + r"\s+(?:personas|comensales|adultos|ninos|raciones)\b", n
    )
    if m:
        res.comensales = _a_numero(m.group(1))

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
            res.clausulas_no_cocino.append(clausula.strip())
            res.sin_cocinar += [d for d in _dias_en(cn) if d not in res.sin_cocinar]
        else:
            resto.append(cn)
    dias = _dias_en(" . ".join(resto))
    res.dias = dias or None

    if re.search(r"\b(cambia|cambiame|cambiar|sustituye|sustituir|otro plato|otra cosa|no me gusta|no quiero)\b", n):
        res.quiere_sustituir = True
        if len(dias) == 1:
            res.sustituir_dia = dias[0]
            res.dias = None  # no es una petición de nuevo plan
    return res
