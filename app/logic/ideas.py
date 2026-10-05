"""Ideas sueltas, sin plan: "¿qué puedo cenar con pasta?", "tengo pollo y arroz, ¿qué hago?", "algo especial para el domingo".

Propone hasta 3 recetas del recetario según lo que tiene o quiere usar, el estilo y su dieta. No crea ni cambia el plan:
el usuario elige una con un chip ("Quiero X el martes") y entonces sí se pone en su plan.
"""
import random
import zlib
from typing import TYPE_CHECKING, Optional

from app.data import catalogo
from app.logic.sesiones import Sesion
from app.logic.texto import hoy, norm
from app.models.schemas import Receta

if TYPE_CHECKING:  # el intérprete importa este módulo: evitar la importación circular
    from app.logic.interprete import Interpretacion

MAX_IDEAS = 3

# Palabras que el usuario dice y las que aparecen en recetas/productos
SINONIMOS = {
    "pasta": ["pasta", "espagueti", "macarron", "tallarin", "lasana", "canelon"],
    "carne": ["pollo", "pavo", "lomo", "costilla", "picada", "hamburguesa", "albondiga", "ternera", "cerdo"],
    "pescado": ["merluza", "bacalao", "salmon", "atun", "sardina"],
    "legumbre": ["lenteja", "garbanzo", "alubia"],
    "verdura": ["verdura", "calabacin", "berenjena", "brocoli", "espinaca", "pisto", "ensalada", "pimiento", "coliflor"],
    "huevo": ["huevo", "tortilla", "revuelto"],
}
LIGERO = {"ensalada", "crema", "verdura", "plancha", "merluza", "brocoli", "calabacin", "garbanzo", "lenteja", "pisto",
          "gazpacho", "salmon", "espinaca", "revuelto", "sardina"}
PESADO = {"frito", "gratinado", "gratinada", "lasana", "pizza", "hamburguesa", "costilla", "carbonara", "chorizo", "bacon",
          "canelon", "fabada", "cocido", "albondiga", "alita", "quesadilla"}


def _palabras(receta: Receta) -> str:
    """Nombre e ingredientes, normalizados, para buscar dentro."""
    return norm(receta.nombre + " " + " ".join(i.producto.nombre for i in receta.ingredientes))


def puntuacion_ligera(receta: Receta) -> int:
    texto = _palabras(receta)
    return sum(p in texto for p in LIGERO) - 2 * sum(p in texto for p in PESADO)


def _coincidencias(receta: Receta, ingredientes: list[str]) -> int:
    texto = _palabras(receta)
    total = 0
    for ingrediente in ingredientes:
        clave = norm(ingrediente).rstrip("s")
        variantes = SINONIMOS.get(clave, [clave])
        total += any(v in texto for v in variantes)
    return total


def ingredientes_en(texto_norm: str) -> list[str]:
    """Palabras del mensaje que son ingredientes o tipos de comida que existen en el recetario."""
    encontrados = []
    for palabra in catalogo._tokens_plato(texto_norm):
        if palabra in SINONIMOS or catalogo.recetas_con(palabra):
            encontrados.append(palabra)
    return encontrados


def proponer(sesion: Sesion, i: "Interpretacion", sin_cocinar: bool) -> dict:
    excluir = set(sesion.excluir) | set(i.excluir)
    candidatas = [
        r for r in catalogo.get_recetas()
        if not (set(r.etiquetas) & excluir) and r.id not in sesion.rechazadas
        and (r.tipo == "listo_para_comer") == sin_cocinar
    ]
    random.Random(zlib.crc32((sesion.id + " ".join(i.ingredientes)).encode())).shuffle(candidatas)  # variedad estable

    def orden(r: Receta):
        estilo = {
            "ligero": -puntuacion_ligera(r),
            "especial": -r.precio_estimado,
            "rapido": len(r.ingredientes),
            "barato": r.precio_estimado,
        }.get(i.estilo or "", 0)
        return (-_coincidencias(r, i.ingredientes), estilo, r.id not in sesion.favoritas)

    if i.ingredientes:
        candidatas = [r for r in candidatas if _coincidencias(r, i.ingredientes) > 0]
    elegidas = sorted(candidatas, key=orden)[:MAX_IDEAS]

    dia = i.dia
    if not elegidas:
        return {"tipo": "ideas", "exito": False, "ingredientes": i.ingredientes, "dia": dia, "momento": i.momento}
    sesion.ultima_receta = elegidas[0].id
    return {
        "tipo": "ideas",
        "exito": True,
        "opciones": [r.nombre for r in elegidas],
        "dia": dia,
        "momento": i.momento,
        "esta_noche": dia == hoy() and i.momento == "cena",
        "ingredientes": i.ingredientes,
    }


def cuando(h: dict) -> str:
    """'esta noche', 'hoy', 'el martes' o '' según el día y momento pedidos."""
    if h.get("esta_noche"):
        return "esta noche"
    if h.get("dia"):
        return "hoy" if h["dia"] == hoy() else f"el {h['dia']}"
    return ""


def chips(h: dict) -> list[str]:
    sufijo = f" {cuando(h)}" if cuando(h) else ""
    return [f"Quiero {nombre.lower()}{sufijo}" for nombre in h.get("opciones", [])]


def texto(h: dict) -> tuple[str, Optional[str]]:
    momento = cuando(h)
    if not h.get("exito"):
        con = f" con {' y '.join(h['ingredientes'])}" if h.get("ingredientes") else ""
        return f"No tengo recetas{con} que encajen. ¿Probamos con otra cosa?", None
    opciones = h["opciones"]
    lista = opciones[0] if len(opciones) == 1 else ", ".join(opciones[:-1]) + " o " + opciones[-1]
    para = f" para {momento}" if momento else ""
    return f"Te propongo{para}: {lista}.", "¿Te apetece alguna?"
