"""Feedback: qué preguntar después de una compra y qué aprender de cada respuesta.

- Al guardar una lista se apunta qué platos y productos se compraron de verdad (los que tienen algo en la lista).
- Merche pregunta por ellos, como mucho MAX_POR_LISTA por lista, para no agobiar.
- Lo que aprende se guarda en la sesión y lo usan el planificador y los extras:
    👍 receta   -> `favoritas`: vuelve a salir en los planes.
    👎 receta   -> `rechazadas`: no vuelve a salir (salvo que la pida).
    👍 producto -> `productos_favoritos`: se elige ese al pedir "añade X".
    👎 producto -> `productos_rechazados`: no se vuelve a elegir.
    motivo "Muy caro"      -> `prefiere_barato`: planes con platos más baratos.
    motivo "Mucho trabajo" -> `prefiere_facil`: planes con platos más sencillos.
"""
import re
from typing import Optional

from app.logic.sesiones import Sesion
from app.logic.texto import norm
from app.models.schemas import FeedbackRequest, FeedbackResponse, LineaLista, SujetoPendiente

MAX_POR_LISTA = 3
MOTIVOS = ["Estaba soso", "Muy caro", "Mucho trabajo", "No me gustó"]


def sujetos_de_lista(sesion: Sesion, lineas: list[LineaLista]) -> list[dict]:
    """Platos (y productos sueltos) del plan que se compraron. Sin líneas, se asume todo el plan."""
    if sesion.plan is None:
        return []
    comprados = {l.producto_id for l in lineas}
    sujetos, vistos = [], set()
    for recetas in sesion.plan.dias.values():
        for r in recetas:
            if r.id in vistos or (comprados and not any(i.producto.id in comprados for i in r.ingredientes)):
                continue  # repetido, o el usuario quitó todos sus ingredientes de la lista
            vistos.add(r.id)
            imagen = r.ingredientes[0].producto.thumbnail if r.ingredientes else None
            sujetos.append({"tipo": "receta", "id": r.id, "nombre": r.nombre, "imagen": imagen})
    for e in sesion.plan.extras:
        if not comprados or e.producto.id in comprados:
            sujetos.append({"tipo": "producto", "id": e.producto.id, "nombre": e.producto.nombre, "imagen": e.producto.thumbnail})
    return sujetos


def _valorados(sesion: Sesion) -> set[tuple[str, str]]:
    return {(f["sujeto"]["tipo"], f["sujeto"]["id"]) for f in sesion.feedback}


def sujeto_pendiente(sesion: Sesion) -> Optional[SujetoPendiente]:
    """Lo siguiente por valorar: de la lista más reciente con preguntas pendientes."""
    valorados = _valorados(sesion)
    for lista in reversed(sesion.listas):
        sujetos = lista.get("sujetos", [])
        if sum((s["tipo"], s["id"]) in valorados for s in sujetos) >= MAX_POR_LISTA:
            continue
        for s in sujetos:
            if (s["tipo"], s["id"]) not in valorados:
                return SujetoPendiente(**s)
    return None


def _anadir(lista: list[str], valor: str) -> None:
    if valor not in lista:
        lista.append(valor)


def _quitar(lista: list[str], valor: str) -> None:
    if valor in lista:
        lista.remove(valor)


def registrar(sesion: Sesion, req: FeedbackRequest) -> FeedbackResponse:
    sesion.feedback.append(req.model_dump())
    sujeto, positivo = req.sujeto, req.valor == "positivo"

    if sujeto.tipo == "receta":
        (_anadir if positivo else _quitar)(sesion.favoritas, sujeto.id)
        (_quitar if positivo else _anadir)(sesion.rechazadas, sujeto.id)
    else:
        (_anadir if positivo else _quitar)(sesion.productos_favoritos, sujeto.id)
        (_quitar if positivo else _anadir)(sesion.productos_rechazados, sujeto.id)

    if not positivo and not req.motivo:  # primero entendemos qué falló; luego seguimos preguntando
        return FeedbackResponse(mensaje="Vaya, lo siento. ¿Qué falló?", sugerencias=MOTIVOS)

    if positivo:
        gracias = "¡Me alegro! Lo volveré a proponer." if sujeto.tipo == "receta" else "¡Me alegro! Lo tendré en cuenta."
    else:
        motivo = norm(req.motivo or "")
        if re.search(r"caro|precio|cuesta", motivo):
            sesion.prefiere_barato = True
            gracias = "Gracias. Apunto que prefieres opciones más baratas."
        elif re.search(r"trabajo|dificil|complicad|tiempo|largo|lio", motivo):
            sesion.prefiere_facil = True
            gracias = "Gracias. Apunto que prefieres platos más sencillos."
        else:
            gracias = "Gracias, no te lo volveré a proponer."

    siguiente = sujeto_pendiente(sesion)
    if siguiente:
        return FeedbackResponse(mensaje=f"{gracias} ¿Y qué tal salió «{siguiente.nombre}»?", feedback=siguiente)
    return FeedbackResponse(mensaje=f"{gracias} Lo tendré en cuenta para la próxima semana.")
