"""Entiende el mensaje del usuario con reglas simples (sin LLM).

Es el plan B del agente: si Gemini no está disponible o falla, `agente.interpretar` usa esto.
Ambos devuelven la misma `Interpretacion`.
"""
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.data.catalogo import _tokens_plato, buscar_receta
from app.logic.texto import DIAS_SEMANA, dia_mas, hoy, norm

Accion = Literal["plan", "pedir_plato", "evitar", "cambiar_plato", "anadir_extra", "quitar_extra", "consultar", "charla"]
# Sobre qué pregunta el usuario (acción "consultar"); la respuesta sale de los datos de la sesión
Tema = Literal["menu", "receta", "ingredientes", "coste", "en_casa", "preferencias", "otro"]
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
    dia: Optional[str] = None  # cambiar_plato / pedir_plato: día (nombre, nunca "hoy")
    momento: Optional[Momento] = None  # cambiar_plato / pedir_plato: comida o cena
    plato: Optional[str] = None  # pedir_plato / consultar: el plato del que habla, p. ej. "pollo al curry"
    tema: Optional[Tema] = None  # consultar: de qué pregunta
    producto: Optional[str] = None  # anadir_extra / quitar_extra: "leche", "café"...
    no_quiere: list[str] = Field(default_factory=list)  # platos o ingredientes que rechaza: "pollo al curry", "cebolla"
    permitir: list[str] = Field(default_factory=list)  # etiquetas que vuelve a admitir ("ya no soy vegetariano")
    sin_presupuesto: bool = False  # "no tengo presupuesto", "da igual el precio"
    respuesta: Optional[str] = None  # texto corto para el usuario (sin cifras ni nombres de platos)
    conclusion: Optional[str] = None  # cierre opcional que va después del plan

    @property
    def aporta_datos(self) -> bool:
        return any(
            [
                self.comensales, self.presupuesto is not None, self.dias, self.momentos, self.sin_cocinar,
                self.excluir, self.permitir, self.sin_presupuesto,
            ]
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
    if re.search(r"\bpasado manana\b", texto_norm):
        encontrados.add(dia_mas(hoy(), 2))
        texto_norm = texto_norm.replace("pasado manana", "")
    if re.search(r"\b(?:hoy|esta noche|esta tarde)\b", texto_norm):
        encontrados.add(hoy())
    if re.search(r"(?<!por la )(?<!de la )\bmanana\b", texto_norm):
        encontrados.add(dia_mas(hoy(), 1))
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


def _plato_pedido(n: str) -> Optional[str]:
    """Texto del plato si el mensaje pide uno ("quiero pollo al curry", "me apetece lentejas el martes")."""
    m = re.search(r"\b(?:quiero|quisiera|me apetece|me gustaria|hazme|preparame|ponme|pon|anade|mejor)\s+(?:comer\s+|cenar\s+)?(.+)", n)
    if not m:
        return None
    texto = re.split(r"[.,;!?]|\s+(?:para|el|los|hoy|manana|esta|que|y somos|somos|pero|mejor|y)\b", m.group(1))[0].strip()
    texto = re.sub(r"^(?:(?:mucho|muchisimo|un poco de|algo de|un|una|unos|unas|el|la|los|las|de)\s+)+", "", texto)
    if not texto or re.search(r"\b(?:plan|menu|presupuesto|euros?|personas|comida y cena)\b", texto):
        return None
    if not _tokens_plato(texto):
        return None  # "quiero comida y cena", "quiero cenar": no nombra ningún plato
    receta, parecido, _ = buscar_receta(texto)
    verbo_de_compra = re.match(r"(?:ponme|pon|anade)\b", m.group(0))
    if verbo_de_compra and not (receta and parecido >= 1.0 and len(texto.split()) > 1):
        return None  # "añade huevos": es un producto, no un plato
    if receta is None and not re.match(r"(?:quiero|quisiera|me apetece|me gustaria)\b", m.group(0)):
        return None
    return texto


def _nombra_un_plato(n: str) -> Optional[str]:
    """Si el mensaje, quitando relleno y días, es el nombre de un plato (todas sus palabras encajan), lo devuelve."""
    receta, parecido, _ = buscar_receta(n)
    if receta is None or parecido < 1:
        return None
    limpio = re.sub(r"^(?:y\s+)?(?:(?:hoy|manana|el \w+|para \w+|esta noche)\s+)*(?:algo de|un poco de|unas?|unos?)?\s*", "", n)
    return re.split(r"\s+(?:el|para|hoy|manana|esta)\b|[.,;!?]", limpio)[0].strip() or None


_DIA_SUELTO = r"(?:el |los )?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)"
_NEGACION = re.compile(
    r"\b(?:no (?:quiero|me apetece|me apetecen|me gusta|me gustan|me pongas|pongas|me hagas|hagas|incluyas|anadas|apuntes)"
    r"(?: mas| nada de| ningun| ninguna)?|pero no|nada de|sin|ni)\s+(?:(?:el|la|los|las|un|una|unos|unas|mas)\s+)*"
    r"(?P<obj>[a-z][a-z ]*?)(?=\s*(?:[,.;!?]|$|\bpero\b|\bmejor\b|\by\b|\bque\b|\bpara\b|\bhoy\b|\bmanana\b|" + _DIA_SUELTO + r"\b))"
)
_PALABRAS_DIETA = {"carne": "carne", "pescado": "pescado", "huevo": "huevo", "huevos": "huevo", "gluten": "gluten",
                   "lactosa": "lactosa", "lacteos": "lactosa", "soja": "soja", "marisco": "pescado"}


def _tapar(texto: str, inicio: int, fin: int) -> str:
    """Sustituye un trozo por espacios (conserva la longitud para poder recortar el mensaje original)."""
    return texto[:inicio] + " " * (fin - inicio) + texto[fin:]


def _negaciones(n: str, res: Interpretacion) -> str:
    """Extrae lo que el usuario NO quiere y devuelve el texto sin esas partes, para que no se lean como peticiones."""
    # "ya no soy vegetariano", "ya como carne": vuelve a admitir etiquetas
    for m in re.finditer(r"\bya no soy (vegetarian|vegan)\w*|\bya (?:como|puedo comer|tomo)\s+(\w+)", n):
        palabra = m.group(1) or m.group(2)
        tags = _DIETAS.get("vegetarian" if palabra.startswith("vegetarian") else "vegan" if palabra.startswith("vegan") else "", None)
        tags = tags or ([_PALABRAS_DIETA[palabra]] if palabra in _PALABRAS_DIETA else [])
        res.permitir += [t for t in tags if t not in res.permitir]
        n = _tapar(n, m.start(), m.end())
    # "no tengo presupuesto", "da igual el precio"
    for m in re.finditer(r"\b(?:no tengo|sin) (?:un |ningun )?(?:presupuesto|limite)\b|\bda igual (?:el precio|lo que cueste)\b", n):
        res.sin_presupuesto = True
        n = _tapar(n, m.start(), m.end())
    # "no somos 4": esa cifra no vale (la corrección suele venir después: "somos 3")
    for m in re.finditer(r"\bno (?:somos|seremos|sera para|es para) \w+", n):
        n = _tapar(n, m.start(), m.end())
    # "no quiero pollo al curry", "nada de pizza", "sin cebolla"...
    for m in list(_NEGACION.finditer(n)):
        objeto = m.group("obj").strip()
        if objeto in _PALABRAS_DIETA:
            if _PALABRAS_DIETA[objeto] not in res.excluir:
                res.excluir.append(_PALABRAS_DIETA[objeto])
        elif objeto in ("cenas", "cena", "cenar"):
            res.momentos = ["comida"]
        elif objeto in ("comidas", "comida"):
            res.momentos = ["cena"]
        elif objeto.startswith("cocin"):
            pass  # "no quiero cocinar el martes": lo resuelve la regla de "no cocino" (que mira el mensaje original)
        elif objeto and objeto not in res.no_quiere:
            res.no_quiere.append(objeto)
        n = _tapar(n, m.start(), m.end())
    return n


_INTERROGATIVO = re.compile(
    r"\s*(?:y\s+)?(?:que|como|cuanto|cuanta|cuantos|cuantas|cual|cuales|cuando|donde|dime|recuerdame|me recuerdas|me dices|hay)\b"
)
# Peticiones con forma de pregunta ("¿me haces un plan?", "¿puedes añadir leche?"): no son consultas
_PIDE_ALGO = re.compile(
    r"\b(?:quiero|quisiera|anad\w*|pon|ponme|poner|quit\w*|hazme|preparame|planifica\w*|organiza\w*)\b"
    r"|\bme (?:haces|preparas|organizas|planificas|pones|anades)\b|\bpuedes (?:hacer|preparar|planificar|organizar|poner)\b"
)


def _es_pregunta(mensaje: str, n: str) -> bool:
    return ("?" in mensaje or bool(_INTERROGATIVO.match(n))) and not _PIDE_ALGO.search(n)


def _tema(n: str, dias: list[str]) -> str:
    if re.search(r"\bcuant\w* (?:me )?(?:va a |van a )?(?:cuesta|cuestan|costar|cuestar|sale|saldra|gasto|vale)|\bprecio|\bcuesta\b|\btotal\b", n):
        return "coste"
    if re.search(r"en casa", n):
        return "en_casa"
    if re.search(r"\bcomo (?:se )?(?:hace|hago|hacer|preparo|prepara|preparar|cocino|cocina|cocinar)\b|receta|pasos|instrucciones|elaboracion", n):
        return "receta"
    if re.search(r"\bque (?:lleva|llevan|tiene|tienen)\b|ingredientes|\bque necesito\b", n):
        return "ingredientes"
    if re.search(r"para cuant|cuantas personas|cuantos somos|presupuesto|que te dije|mi dieta|que no (?:como|puedo)|preferencias|que dias", n):
        return "preferencias"
    if dias or re.search(r"menu|\bque (?:como|ceno|comemos|cenamos|hay|toca|tengo)\b|\bplan\b|semana|comida|cena", n):
        return "menu"
    return "otro"


def interpretar(mensaje: str) -> Interpretacion:
    res = Interpretacion()
    n = _negaciones(norm(mensaje), res)  # a partir de aquí, `n` ya no contiene lo que el usuario rechaza

    # Personas: vale la ÚLTIMA cifra ("somos 4... bueno, somos 3")
    cifras = list(re.finditer(r"\b(?:somos|seremos|para)\s+" + _NUM + r"\b(?!\s+(?:pareja|familia))", n)) or list(
        re.finditer(r"\b" + _NUM + r"\s+(?:personas|comensales|adultos|ninos|raciones)\b", n)
    )
    m = cifras[-1] if cifras else None
    if m:
        res.comensales = _a_numero(m.group(1))
    elif re.search(r"\b(?:pareja|los dos|las dos|mi marido y yo|mi mujer y yo|mi novi[oa] y yo)\b", n):
        res.comensales = 2
    elif re.search(
        r"\b(?:solo (?:para )?yo|yo solo|yo sola|solo para mi|para mi(?! (?:familia|marido|mujer|pareja|novi|hij|casa))"
        r"|una persona|individual)\b",
        n,
    ):
        res.comensales = 1

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:€|euros?|eur\b)", n) or re.search(
        r"presupuesto\s+(?:maximo\s+)?(?:de\s+)?(\d+(?:[.,]\d+)?)", n
    )
    if m:
        res.presupuesto = float(m.group(1).replace(",", "."))

    # Cláusulas "no cocino": sus días no se añaden al plan, solo se marcan
    resto = []
    for clausula in re.split(r"[.;\n,]", mensaje):
        cn = norm(clausula)
        if re.search(r"\bno (?:\w+ ){0,3}cocin", cn):  # "no cocino", "no quiero cocinar"
            res.sin_cocinar += [d for d in _dias_en(cn) if d not in res.sin_cocinar]
        else:
            resto.append(cn)
    dias = _dias_en(" . ".join(resto))
    res.dias = dias or None
    res.excluir += [t for t in _excluir_en(n) if t not in res.excluir and t not in res.permitir]

    comida = re.search(r"\bcomidas?\b|almuerzo|\bcomer\b", n)
    cena = re.search(r"\bcenas?\b|\bcenar\b|esta noche", n)
    if comida and cena:
        res.momentos = ["comida", "cena"]
    elif cena:
        res.momentos = ["cena"]

    if re.search(r"\b(cambia|cambiame|cambiar|sustituye|sustituir|otro plato|otra cosa)\b", n) and not res.excluir:
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

    # Preguntas sobre lo que ya hay ("¿qué como el martes?", "¿cómo se hace la tortilla?"): nunca cambian el plan
    datos_nuevos = any([res.comensales, res.presupuesto is not None, res.excluir, res.sin_cocinar, res.permitir,
                        res.sin_presupuesto, res.no_quiere])
    if _es_pregunta(mensaje, n) and not datos_nuevos:
        res.accion, res.tema = "consultar", _tema(n, dias)
        res.dia = dias[0] if len(dias) == 1 else None
        res.momento = "cena" if cena and not comida else ("comida" if comida and not cena else None)
        res.plato, res.dias, res.momentos = mensaje, None, None
        return res

    def es_pedir_plato(plato: str) -> Interpretacion:
        inicio = n.find(plato)  # norm() conserva la longitud: recupera el texto original, con tildes
        res.accion, res.plato = "pedir_plato", mensaje[inicio : inicio + len(plato)] if inicio >= 0 else plato
        res.dia = dias[0] if len(dias) == 1 else None
        res.momento = "cena" if cena and not comida else None
        res.dias = None if len(dias) <= 1 else res.dias
        res.momentos = None
        return res

    plato = _plato_pedido(n)
    if plato:
        receta, parecido, _ = buscar_receta(plato)
        if receta and parecido >= 0.5 or re.search(r"\b(?:quiero|quisiera|me apetece|me gustaria)\b", n):
            return es_pedir_plato(plato)

    anadir = _producto_tras(r"anade|anademe|anadir|apuntame|apunta|apuntar|ponme|pon|poner", n)
    quitar = _producto_tras(r"quita|quitame|elimina|borra", n)
    if anadir and not res.aporta_datos:
        res.accion, res.producto = "anadir_extra", anadir
    elif quitar and not res.aporta_datos and not _dias_en(quitar):
        res.accion, res.producto = "quitar_extra", quitar
    elif not (res.comensales or res.presupuesto is not None or res.excluir or res.sin_cocinar) and _nombra_un_plato(n):
        return es_pedir_plato(_nombra_un_plato(n))  # "y mañana algo de lentejas": un plato sin verbo
    elif res.aporta_datos or re.search(r"\b(plan|menu|planifica\w*|organiza\w*|semana)\b", n):
        res.accion = "plan"  # incluye peticiones genéricas: luego se pregunta lo que falte
    if res.no_quiere and res.accion in ("charla", "plan"):
        otros_datos = any([res.comensales, res.presupuesto is not None, res.momentos, res.sin_cocinar, res.excluir,
                           res.permitir, res.sin_presupuesto])
        if res.accion == "charla" or not otros_datos:  # "no quiero lentejas (el martes)": solo un rechazo
            res.accion, res.dia, res.dias = "evitar", dias[0] if len(dias) == 1 else None, None
    return res
