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

SISTEMA_INTERPRETE = """Eres el módulo de comprensión de Merche, una asistente de Mercadona que ayuda con la comida: desde una idea
para cenar esta noche hasta el plan de toda la semana. NO des por hecho que el usuario quiere un plan semanal: muchas veces
solo quiere una idea, un plato o resolver una comida.
Tu única tarea es clasificar el último mensaje del usuario y devolver SOLO un JSON con el esquema indicado.

Acciones (campo `accion`):
- "sugerir": pide IDEAS o recomendaciones sin nombrar un plato concreto ("¿qué puedo cenar esta noche con pasta?", "el martes no me apetece cocinar, ¿qué me recomiendas?", "algo especial para el domingo", "tengo pollo y arroz, ¿qué hago?", "me apetece algo ligero"). Rellena `ingredientes` (lo que tiene o quiere usar: "pasta", "pollo"), `estilo` ("ligero", "especial", "rapido", "barato") y `dia`/`momento` si los dice. Si no quiere cocinar ese día, pon el día también en `sin_cocinar`.
- "plan": pide un plan o menú de VARIOS días ("hazme el menú de la semana", "¿me propones un menú ligero para esta semana?") o da/cambia datos de su plan (personas, presupuesto, días, comida/cena, dietas, días que no cocina). Si dice cómo lo quiere ("más ligero", "barato"), rellena `estilo`.
- "pedir_plato": pide un plato concreto ("quiero pollo al curry", "me apetece lentejas el martes", "pizza para cenar hoy"). `plato` = el nombre del plato tal como lo dice (sin verbos ni días); `dia` y `momento` si los dice. Si en el mismo mensaje da personas, presupuesto, etc., rellénalos también.
- "cambiar_plato": quiere cambiar platos de SU plan ("cambia el martes", "cambia el lunes y el martes por algo de pescado", "cambia las hamburguesas", "cambia la pasta por arroz", "cámbiame la cena del jueves por algo ligero", "cambia todo"). Rellena:
  `dias_cambio` (días a cambiar, minúsculas y con tilde: lunes, martes, miércoles, jueves, viernes, sábado, domingo), o `objetivo` si nombra el plato en vez del día ("hamburguesas", "pasta"), o `todo` true si quiere cambiarlo todo;
  `por` con lo que quiere en su lugar, tal cual lo dice ("lentejas", "pescado", "algo ligero", "vegetariano"); `momento` solo si dice comida o cena.
  Lo que va tras "por" es SOLO para ese plato: "por algo vegetariano" NO va en `excluir` (no cambia su dieta). "Cambia X" nunca es "pedir_plato".
- "evitar": SOLO rechaza algo, sin pedir nada más ("no quiero pollo al curry", "nada de pizza", "sin cebolla", "no me apetecen lentejas"). Lo rechazado va en `no_quiere`.
- "anadir_extra": quiere añadir un producto suelto a su compra (leche, café...). `producto` en singular y genérico.
- "quitar_extra": quiere quitar uno de esos productos sueltos. `producto` igual.
- "consultar": PREGUNTA algo sobre su plan o sus datos, sin pedir cambios ("¿qué como el martes?", "¿cómo se hace la tortilla?", "¿qué lleva el del lunes?", "¿y qué lleva?", "¿cuánto me va a costar?", "¿para cuántos era?", "¿esto es sano?"). Una pregunta NUNCA es "plan". Rellena `tema`:
  "menu" (qué se come y cuándo), "receta" (cómo se prepara), "ingredientes" (qué lleva), "coste" (cuánto cuesta), "en_casa" (qué hay que tener en casa), "preferencias" (personas, presupuesto, dieta... que dijo), "otro" (cualquier otra pregunta).
  Rellena `dia`/`momento` si los dice y `plato` con el nombre del plato si lo nombra. Si `tema` es "otro", contesta tú en `respuesta` usando SOLO los datos del estado (ingredientes, instrucciones), sin cifras ni precios.
- "opinion": comentario, queja o sugerencia sobre productos de Mercadona o sobre la compra ("las latas de atún vienen con demasiado aceite", "el pan llegó duro", "echo de menos el tofu ahumado", "la lasaña estaba buenísima"). Rellena `puntos_clave`: 1 a 3 frases cortas y neutras con lo esencial, empezando por el producto ("Latas de atún: demasiado aceite"). Tiene prioridad sobre "evitar".
- "charla": saludos, agradecimientos o cualquier cosa que no cambie el plan ni sea una pregunta sobre él.

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
        # Detalle completo, para que pueda contestar preguntas abiertas ("¿esto es sano?") sin inventar
        "platos": {
            d: [
                {
                    "nombre": r.nombre,
                    "momento": r.momento or "comida",
                    "tipo": r.tipo,
                    "ingredientes": [x.producto.nombre for x in r.ingredientes],
                    "instrucciones": r.instrucciones,
                }
                for r in rs
            ]
            for d, rs in plan.dias.items()
        } if plan else None,
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
    resultado._fuente = "gemini"
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
    if hechos.get("tipo") in ("ideas", "cambio_plato"):  # nombres exactos de recetas: los pone el código
        llm.log.debug("Respuesta: ideas del recetario (codigo)")
        return mensajes.redactar(hechos)
    if hechos.get("tipo") == "opinion":  # el texto es fijo: la tarjeta "Enviado a Mercadona" lleva lo importante
        return mensajes.redactar(hechos)
    if hechos.get("tipo") == "consulta":
        # Lo concreto (menú, receta, ingredientes, coste...) lo contesta el código con los datos; lo abierto, Gemini
        if hechos["tema"] == "otro" and texto and not _CON_CIFRAS.search(texto):
            llm.log.debug("Respuesta: consulta abierta contestada por %s", i._fuente.upper())
            return texto, None
        llm.log.debug("Respuesta: consulta '%s' contestada con los datos de la sesion", hechos["tema"])
        return hechos["texto"], None
    if hechos.get("tipo") == "charla" and texto:
        llm.log.debug("Respuesta: texto escrito por %s (charla)", i._fuente.upper())
        return texto, None
    if hechos.get("exito") and texto and not _CON_CIFRAS.search(texto) and not hechos.get("parecido"):
        llm.log.debug("Respuesta: texto escrito por %s", i._fuente.upper())
        return texto, (i.conclusion or None)
    llm.log.debug("Respuesta: PLANTILLA del codigo (resultado=%s)", hechos.get("tipo"))
    return mensajes.redactar(hechos)
