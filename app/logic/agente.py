"""Capa de lenguaje del agente: Gemini con plan B por reglas/plantillas.

UNA sola llamada a Gemini por mensaje (la clave gratuita tiene ~5 peticiones por minuto):
`interpretar` clasifica el mensaje y, de paso, propone el texto de la respuesta (`respuesta`).
Qué platos hay, cantidades, precios y si algo es viable lo decide siempre el código (`planificador`);
si la acción falla, el texto lo escribe el código, no el LLM.
"""
import json
import re
from typing import Optional

from app.logic import interprete, llm, mensajes
from app.logic.sesiones import Sesion
from app.logic.texto import hoy

SISTEMA_INTERPRETE = """Eres el módulo de comprensión de Merche, una asistente de Mercadona que planifica la comida de la semana.
Tu única tarea es clasificar el último mensaje del usuario y devolver SOLO un JSON con el esquema indicado.

Acciones (campo `accion`):
- "plan": el usuario da o cambia datos del plan (personas, presupuesto, días, comida/cena, dietas o alergias, días que no cocina) o pide un plan nuevo.
- "pedir_plato": pide un plato concreto ("quiero pollo al curry", "me apetece lentejas el martes", "pizza para cenar hoy"). `plato` = el nombre del plato tal como lo dice (sin verbos ni días); `dia` y `momento` si los dice. Si en el mismo mensaje da personas, presupuesto, etc., rellénalos también.
- "cambiar_plato": quiere OTRO plato distinto en un día, sin decir cuál ("cambia el martes"). `dia` es obligatorio (minúsculas y con tilde: lunes, martes, miércoles, jueves, viernes, sábado, domingo); `momento` solo si dice comida o cena.
- "evitar": SOLO rechaza algo, sin pedir nada más ("no quiero pollo al curry", "nada de pizza", "sin cebolla", "no me apetecen lentejas"). Lo rechazado va en `no_quiere`.
- "anadir_extra": quiere añadir un producto suelto a su compra (leche, café...). `producto` en singular y genérico.
- "quitar_extra": quiere quitar uno de esos productos sueltos. `producto` igual.
- "charla": saludos, agradecimientos, preguntas sobre el plan o cualquier cosa que no cambie el plan. Usa el estado para contestar sobre el plan actual.

Campo `respuesta` (siempre): lo que Merche diría al usuario, una o dos frases en español de España, cercanas, tuteando. En "plan", "pedir_plato", "evitar", "cambiar_plato", "anadir_extra" y "quitar_extra" escríbelo como si la acción fuera a salir bien, SIN cifras, SIN precios y SIN nombrar platos ni productos concretos (el plan se muestra aparte; el sistema te corrige si algo falla). Campo `conclusion` (opcional): una pregunta muy corta que va después del plan, p. ej. "¿Qué te parece?".

Reglas:
- Rellena solo lo que el usuario haya dicho en este mensaje; el resto, null o lista vacía. El estado actual es contexto, no lo repitas.
- `excluir` solo admite: carne, pescado, gluten, lactosa, huevo, soja. Vegetariano = carne y pescado. Vegano = carne, pescado, huevo y lactosa.
- `presupuesto` en euros, número. `comensales` número entero.
- "No cocino el martes" va en `sin_cocinar` (no en `dias`).
- "Para mí", "solo yo", "una persona" = `comensales` 1. "Somos una pareja" = 2.
- Los días SIEMPRE con su nombre. Convierte "hoy", "mañana", "pasado mañana" y "esta noche" usando `hoy` del CONTEXTO (p. ej. si hoy es lunes, "mañana" = "martes"). "Esta noche" o "para cenar" = `momento` cena.
- NEGACIONES (muy importante): lo que va detrás de "no", "nada de", "sin", "ni", "pero no" NUNCA es una petición.
  - Platos o ingredientes rechazados -> `no_quiere` (texto corto: "pollo al curry", "cebolla", "pizza carnívora"). Nunca los pongas en `plato`.
  - Si además pide otra cosa en el mismo mensaje ("no quiero pollo al curry, mejor lentejas"), la acción es la de lo que pide (aquí "pedir_plato" con `plato` "lentejas") y lo rechazado va igualmente en `no_quiere`.
  - "No quiero carne/pescado/gluten..." -> `excluir`. "Ya no soy vegetariano", "ya como carne" -> `permitir` (etiquetas que vuelven a valer).
  - Correcciones: "no somos 4, somos 3" -> `comensales` 3. "No quiero cocinar el martes" -> `sin_cocinar`. "No quiero cenas" -> `momentos` ["comida"].
  - "No tengo presupuesto", "da igual el precio" -> `sin_presupuesto` true.
  - Un "no" suelto al principio ("no, mejor para mañana") solo corrige lo anterior: interpreta el resto.
- Nunca inventes precios ni platos. Si piden algo que no puedes hacer (pedir un pedido, pagar...), usa "charla" y explícalo con amabilidad.
"""

def _estado_para_llm(sesion: Sesion) -> dict:
    plan = sesion.plan
    return {
        "comensales": sesion.comensales,
        "presupuesto_eur": sesion.presupuesto,
        "dias_en_plan": list(plan.dias) if plan else None,
        "platos": {d: [f"{r.nombre} ({r.momento or 'comida'})" for r in rs] for d, rs in plan.dias.items()} if plan else None,
        "productos_extra": [e.producto.nombre for e in plan.extras] if plan else [],
        "evitar": sesion.excluir,
        "dias_que_no_cocina": sesion.sin_cocinar,
        "platos_pedidos_pendientes": [f["receta_id"] for f in sesion.fijos if not plan],
    }


def interpretar(mensaje: str, sesion: Sesion) -> interprete.Interpretacion:
    contexto = {
        "hoy": hoy(),
        "estado": _estado_para_llm(sesion),
        "ultimos_mensajes": [m.model_dump() for m in sesion.mensajes[-7:-1]],  # sin el actual
    }
    prompt = f"CONTEXTO:\n{json.dumps(contexto, ensure_ascii=False)}\n\nMENSAJE DEL USUARIO:\n{mensaje}"
    resultado = llm.generar_json(prompt, interprete.Interpretacion, SISTEMA_INTERPRETE, temperatura=0.4)
    if resultado is None:
        resultado = interprete.interpretar(mensaje)
        llm.log.debug("Mensaje %r entendido por el PLAN B (reglas): accion=%s", mensaje[:60], resultado.accion)
        return resultado
    resultado.excluir = [e for e in resultado.excluir if e in interprete.ETIQUETAS]
    resultado.permitir = [e for e in resultado.permitir if e in interprete.ETIQUETAS]
    llm.log.debug("Mensaje %r entendido por GEMINI: %s", mensaje[:60], resultado.model_dump(exclude_none=True, exclude_defaults=True))
    return resultado


_CON_CIFRAS = re.compile(r"\d+(?:[.,]\d+)?\s*(?:€|euros?)|€\s*\d")


def redactar(hechos: dict, i: interprete.Interpretacion) -> tuple[str, Optional[str]]:
    """(mensaje, mensaje_conclusion).

    Si el LLM escribió un texto y la acción salió bien, se usa ese. Los fallos y rechazos los redacta
    siempre el código (plantillas) para que lo que se le dice al usuario sea exacto.
    """
    texto = (i.respuesta or "").strip()
    if hechos.get("tipo") == "charla" and texto:
        llm.log.debug("Respuesta: texto propuesto por el interprete (charla)")
        return texto, None
    if hechos.get("exito") and texto and not _CON_CIFRAS.search(texto) and not hechos.get("parecido"):
        llm.log.debug("Respuesta: texto propuesto por el interprete")
        return texto, (i.conclusion or None)
    llm.log.debug("Respuesta: PLANTILLA del codigo (resultado=%s)", hechos.get("tipo"))
    return mensajes.redactar(hechos)
