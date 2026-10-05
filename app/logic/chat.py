"""Orquestación de un turno de chat:

    mensaje -> agente.interpretar (clasifica) -> se ejecuta la acción (código determinista, con reglas
    de viabilidad) -> se actualiza el estado de la sesión -> agente.redactar (texto) -> respuesta.
"""
import uuid
import zlib
from typing import Optional

from app.data import catalogo
from app.logic import agente, apertura, cambios, consultas, feedback, ideas, planificador, sesiones, sugerencias
from app.logic.carrito import total_plan
from app.logic.errores import DatosInvalidos, Inviable, NoEncontrado, SinAlternativa
from app.logic.interprete import _PALABRAS_DIETA as ETIQUETA_DE_PALABRA, Interpretacion
from app.logic.planificador import Peticion
from app.logic.sesiones import Sesion
from app.logic.texto import DIAS_SEMANA, hoy, norm
from app.models.schemas import ChatRequest, ChatResponse, Enviado, FeedbackRequest, FeedbackResponse, ListaRequest, ListaResponse, MensajeChat, PlanResponse

# NUEVO: Importamos el cerebro de la IA
from app.logic.llm import consultar_llm

DIAS_POR_DEFECTO = DIAS_SEMANA[:5]  # lunes a viernes
TIENDAS = ["Paterna", "Alboraya"]  # solo para elegir dónde se hará la compra; no se conecta a nada

def _platos(plan: PlanResponse) -> dict[str, list[str]]:
    return {d: [r.nombre for r in rs] for d, rs in plan.dias.items()}


def _plan_con_hechos(sesion: Sesion, i: Interpretacion) -> tuple[dict, Optional[PlanResponse]]:
    """Crear o rehacer el plan con los datos nuevos mezclados con las preferencias de la sesión."""
    comensales = i.comensales or sesion.comensales
    presupuesto = None if i.sin_presupuesto else (i.presupuesto if i.presupuesto is not None else sesion.presupuesto)
    excluir = sorted((set(sesion.excluir) | set(i.excluir)) - set(i.permitir))
    momentos = list(i.momentos or sesion.momentos)
    sin_cocinar = sorted(set(sesion.sin_cocinar) | set(i.sin_cocinar))
    platos_sueltos = [f["dia"] or hoy() for f in sesion.fijos] if sesion.fijos and not sesion.plan else None
    dias = list(i.dias or (sesion.plan.dias if sesion.plan else None) or sesion.dias or platos_sueltos or DIAS_POR_DEFECTO)
    for d in i.sin_cocinar:  # un día marcado como "no cocino" también es un día del plan
        if all(norm(d) != norm(x) for x in dias):
            dias.append(d)

    if i.estilo == "ligero":
        sesion.prefiere_ligero = True
    elif i.estilo == "barato":
        sesion.prefiere_barato = True
    elif i.estilo == "rapido":
        sesion.prefiere_facil = True

    def guardar_preferencias(con_presupuesto: bool = True):
        sesion.comensales = comensales
        if con_presupuesto:
            sesion.presupuesto = presupuesto
        sesion.excluir, sesion.momentos, sesion.sin_cocinar = excluir, momentos, sin_cocinar
        sesion.dias = i.dias or sesion.dias

    if not comensales:
        guardar_preferencias()  # nos quedamos con lo que sí ha dicho y preguntamos lo que falta
        return {"tipo": "pregunta_comensales"}, None

    peticion = Peticion(
        comensales=comensales,
        dias=dias,
        presupuesto=presupuesto,
        momentos=momentos,
        sin_cocinar=set(sin_cocinar),
        excluir=set(excluir),
        rechazadas=set(sesion.rechazadas),
        fijos=[(f["dia"], f["momento"], f["receta_id"]) for f in sesion.fijos],
        semilla=zlib.crc32(sesion.id.encode()),
        favoritas=set(sesion.favoritas),
        prefiere_barato=sesion.prefiere_barato,
        prefiere_facil=sesion.prefiere_facil,
        prefiere_ligero=sesion.prefiere_ligero,
    )
    try:
        plan = planificador.generar_plan(peticion, extras=sesion.plan.extras if sesion.plan else [])
    except Inviable as e:  # presupuesto imposible: se recuerda todo lo demás, pero no ese presupuesto
        guardar_preferencias(con_presupuesto=False)
        return {
            "tipo": "inviable",
            "exito": False,
            "comensales": comensales,
            "presupuesto": presupuesto,
            "n_comidas": len(dias) * len(momentos),
            "importe_minimo_aproximado": e.minimo,
        }, None
    except DatosInvalidos as e:
        return {"tipo": "rechazo", "exito": False, "motivo": str(e)}, None

    guardar_preferencias()
    sesion.plan = plan
    _ubicar_fijos(sesion, plan)
    return {"tipo": "plan", "exito": True, "comensales": comensales, "platos": _platos(plan)}, plan


def _ubicar_fijos(sesion: Sesion, plan: PlanResponse) -> None:
    """Apunta en qué día quedó cada plato pedido sin día, y olvida los que ya no están en el plan."""
    ubicados = []
    for f in sesion.fijos:
        dia = next((d for d, rs in plan.dias.items() if any(r.id == f["receta_id"] for r in rs)), None)
        if dia:
            ubicados.append({**f, "dia": dia})
    sesion.fijos = ubicados


def _pedir_plato(sesion: Sesion, i: Interpretacion, rechazadas_ahora: set[str] = frozenset()) -> tuple[dict, Optional[PlanResponse]]:
    """El usuario pide un plato concreto ("quiero pollo al curry", "lentejas el martes")."""
    receta, parecido, alternativas = catalogo.buscar_receta(i.plato or "")
    if receta is not None and receta.id in rechazadas_ahora:  # "quiero pizza pero no carnívora"
        receta = next((r for r in alternativas if r.id not in rechazadas_ahora), None)
    if receta is None or parecido < 0.5:
        sugeridas = ([receta] if receta else []) + alternativas
        return {"tipo": "plato_no_encontrado", "exito": False, "busqueda": i.plato, "alternativas": [r.nombre for r in sugeridas[:2]]}, None
    choca = sorted(set(receta.etiquetas) & (set(sesion.excluir) | set(i.excluir)))
    if choca:
        return {"tipo": "plato_excluido", "exito": False, "plato": receta.nombre, "etiquetas": choca}, None
    if receta.id in sesion.rechazadas:  # lo pide expresamente: deja de estar vetado
        sesion.rechazadas.remove(receta.id)
    sesion.ultima_receta = receta.id

    dia = next((d for d in DIAS_SEMANA if i.dia and norm(d) == norm(i.dia)), None)
    sesion.fijos = [f for f in sesion.fijos if not (dia and f["dia"] == dia and f["momento"] == i.momento)]
    sesion.fijos.append({"dia": dia, "momento": i.momento, "receta_id": receta.id})
    extra = {"plato": receta.nombre, "pedido": i.plato, "parecido": parecido < 1, "dia_pedido": dia}

    cambia_comensales = i.comensales and i.comensales != sesion.comensales
    if sesion.plan is not None and not cambia_comensales:
        comensales = sesion.comensales or next((r.raciones for rs in sesion.plan.dias.values() for r in rs), 2)
        hueco_rechazado = next((d for d, rs in sesion.plan.dias.items() if any(r.id in rechazadas_ahora for r in rs)), None)
        destino = dia or hueco_rechazado or next(iter(sesion.plan.dias), None) or DIAS_SEMANA[0]
        try:
            nuevo = planificador.poner_plato(sesion.plan, receta, destino, i.momento, comensales)
        except DatosInvalidos as e:
            return {"tipo": "rechazo", "exito": False, "motivo": str(e)}, None
        avisos = []
        if sesion.presupuesto is not None and total_plan(nuevo) > sesion.presupuesto:
            avisos.append("Ojo: con este cambio te pasas del presupuesto que me dijiste.")
        sesion.plan = nuevo
        _ubicar_fijos(sesion, nuevo)
        return {"tipo": "plato_puesto", "exito": True, "dia": destino, **extra, "avisos": avisos}, nuevo

    # Aún no hay plan (o cambian los comensales): se hace uno con este plato dentro
    cambios = {}
    if dia and sesion.plan is None and not sesion.dias:
        cambios["dias"] = [dia]  # "quiero pollo al curry hoy": plan solo para ese día
        if i.momento:
            cambios["momentos"] = [i.momento]
    hechos, plan = _plan_con_hechos(sesion, i.model_copy(update=cambios))
    return {**hechos, **extra}, plan


def _cambiar_plato(sesion: Sesion, i: Interpretacion) -> tuple[dict, Optional[PlanResponse]]:
    """Ver cambios.py: días, platos nombrados o todo, y "por X" como criterio solo para ese hueco."""
    return cambios.cambiar(sesion, i)


def _extra(sesion: Sesion, i: Interpretacion, anadir: bool) -> tuple[dict, Optional[PlanResponse]]:
    if sesion.plan is None:
        return {"tipo": "sin_plan"}, None
    busqueda = i.producto or ""
    if anadir:
        producto = catalogo.mejor_producto(busqueda, set(sesion.productos_favoritos), set(sesion.productos_rechazados))
        if producto is None:
            return {"tipo": "producto_no_encontrado", "exito": False, "busqueda": busqueda}, None
        nuevo = planificador.anadir_extra(sesion.plan, producto)
        avisos = []
        if sesion.presupuesto is not None and total_plan(nuevo) > sesion.presupuesto:
            avisos.append("Ojo: con eso te pasas del presupuesto que me dijiste.")
        sesion.plan = nuevo
        return {"tipo": "extra_anadido", "exito": True, "producto": producto.nombre, "avisos": avisos}, nuevo
    try:
        nuevo, producto = planificador.quitar_extra(sesion.plan, busqueda)
    except NoEncontrado as e:
        return {"tipo": "rechazo", "exito": False, "motivo": str(e)}, None
    sesion.plan = nuevo
    return {"tipo": "extra_quitado", "exito": True, "producto": producto.nombre}, nuevo


def _aplicar_rechazos(sesion: Sesion, i: Interpretacion) -> tuple[set[str], list[str]]:
    """Lo que el usuario NO quiere: recetas vetadas (por nombre o ingrediente), etiquetas de dieta y extras.

    Devuelve (ids de recetas vetadas ahora, nombres legibles de lo vetado)."""
    nuevas, nombres = set(), []
    for cosa in i.no_quiere:
        if norm(cosa) in ETIQUETA_DE_PALABRA:  # "no quiero carne" por si Gemini lo pone aquí
            if ETIQUETA_DE_PALABRA[norm(cosa)] not in i.excluir:
                i.excluir.append(ETIQUETA_DE_PALABRA[norm(cosa)])
            continue
        recetas = catalogo.recetas_con(cosa)
        for r in recetas:
            if r.id not in sesion.rechazadas:
                sesion.rechazadas.append(r.id)
            nuevas.add(r.id)
        sesion.fijos = [f for f in sesion.fijos if f["receta_id"] not in nuevas]
        if sesion.plan and any(norm(cosa) in norm(e.producto.nombre) for e in sesion.plan.extras):
            sesion.plan = sesion.plan.model_copy(update={"extras": [e for e in sesion.plan.extras if norm(cosa) not in norm(e.producto.nombre)]})
        nombres.append(cosa)
    if i.permitir:
        sesion.excluir = [t for t in sesion.excluir if t not in i.permitir]
    if i.sin_presupuesto:
        sesion.presupuesto = None
    return nuevas, nombres


def _quitar_vetados_del_plan(sesion: Sesion, vetadas: set[str]) -> dict[str, str]:
    """Sustituye en el plan vigente los platos que el usuario acaba de rechazar. Devuelve {día: plato nuevo}."""
    cambios = {}
    if not sesion.plan or not vetadas:
        return cambios
    for dia, recetas in list(sesion.plan.dias.items()):
        for r in recetas:
            if r.id in vetadas:
                try:
                    sesion.plan = planificador.cambiar_plato(
                        sesion.plan, dia, r.momento, None, set(sesion.excluir), set(sesion.rechazadas)
                    )
                    cambios[dia] = " y ".join(x.nombre for x in sesion.plan.dias[dia])
                except (NoEncontrado, SinAlternativa):
                    pass
    return cambios


def procesar(req: ChatRequest) -> ChatResponse:
    sesion = sesiones.obtener(req.session_id, req.sesion_anterior)
    if req.plan is not None:  # el usuario lo ha editado: lo que ve manda sobre lo que teníamos guardado
        sesion.plan = req.plan
    sesion.mensajes.append(MensajeChat(rol="usuario", texto=req.mensaje))

    i = agente.interpretar(req.mensaje, sesion)
    if i.accion == "pedir_plato" and not (i.plato or "").strip():
        # Gemini a veces arrastra la acción anterior ("solo para mí" tras pedir un plato): sin plato, son datos del plan
        i.accion = "plan" if i.aporta_datos or sesion.fijos else "charla"
    plan_antes = sesion.plan
    vetadas, vetadas_nombres = _aplicar_rechazos(sesion, i)
    if i.accion == "evitar" or (vetadas_nombres and i.accion == "charla"):
        cambios = _quitar_vetados_del_plan(sesion, vetadas)
        hechos = {"tipo": "evitado", "exito": True, "evitados": vetadas_nombres, "cambios": cambios,
                  "sin_coincidencias": not vetadas}
        plan = sesion.plan if sesion.plan is not plan_antes else None
    elif i.accion == "plan":
        hechos, plan = _plan_con_hechos(sesion, i)
    elif i.accion == "opinion":  # comentario para Mercadona: se "envía" y se propone seguir con la semana
        puntos = [p.strip() for p in i.puntos_clave if p.strip()][:3] or [req.mensaje.strip()]
        sesion.opiniones.append({"texto": req.mensaje, "puntos": puntos})
        hechos, plan = {"tipo": "opinion", "exito": True, "puntos": puntos}, None
    elif i.accion == "sugerir" or (i.accion == "consultar" and i.tema == "menu" and sesion.plan is None):
        # Ideas sueltas, sin crear plan: "¿qué ceno con pasta?", "¿qué me recomiendas?"
        sin_cocinar = bool(i.sin_cocinar) or bool(i.dia and i.dia in sesion.sin_cocinar)
        if not i.dia and len(i.sin_cocinar) == 1:  # "el martes no me apetece cocinar": las ideas son para el martes
            i.dia = i.sin_cocinar[0]
        hechos, plan = ideas.proponer(sesion, i, sin_cocinar), None
    elif i.accion == "consultar":  # una pregunta nunca cambia el plan
        hechos, plan = consultas.responder(sesion, i), None
    elif i.accion == "pedir_plato":
        hechos, plan = _pedir_plato(sesion, i, vetadas)
    elif i.accion == "cambiar_plato":
        hechos, plan = _cambiar_plato(sesion, i)
    elif i.accion in ("anadir_extra", "quitar_extra"):
        hechos, plan = _extra(sesion, i, anadir=i.accion == "anadir_extra")
    else:
        hechos, plan = ({"tipo": "charla", "respuesta": i.respuesta} if i.respuesta else {"tipo": "no_entiendo"}), None

    if i.accion != "evitar" and vetadas:  # además de lo pedido, quita del plan lo que acaba de rechazar
        cambios = _quitar_vetados_del_plan(sesion, vetadas)
        if cambios:
            plan = sesion.plan
            hechos.setdefault("avisos", []).append("También he cambiado " + ", ".join(f"el {d}" for d in cambios) + " para quitar lo que no quieres.")
    if plan is None and sesion.plan is not plan_antes and sesion.plan is not None and hechos.get("exito", True):
        plan = sesion.plan  # p. ej. se quitó un extra rechazado
    mensaje, conclusion = agente.redactar(hechos, i)
    sesion.mensajes.append(MensajeChat(rol="asistente", texto=mensaje))
    sesiones.guardar(sesion)
    chips = sugerencias.para(hechos, sesion)
    enviado = Enviado(puntos=hechos["puntos"]) if hechos.get("tipo") == "opinion" else None
    return ChatResponse(
        session_id=sesion.id, mensaje=mensaje, mensaje_conclusion=conclusion, plan=plan, sugerencias=chips or None,
        enviado=enviado,
    )


def guardar_lista(req: ListaRequest) -> ListaResponse:
    sesion = sesiones.buscar(req.session_id)
    if sesion is None:
        raise NoEncontrado(f"Sesión {req.session_id} no existe")
    for linea in req.lineas:
        if catalogo.get_producto(linea.producto_id) is None:
            raise DatosInvalidos(f"El producto {linea.producto_id} no existe")
    lista_id = "l_" + uuid.uuid4().hex[:4]
    sesion.listas.append({
        "lista_id": lista_id, "plan_id": req.plan_id, "nombre": req.nombre,
        "lineas": [l.model_dump() for l in req.lineas],
        "sujetos": feedback.sujetos_de_lista(sesion, req.lineas),  # qué se compró: de eso preguntará luego
    })
    sesiones.guardar(sesion)
    return ListaResponse(lista_id=lista_id, mensaje="Lista guardada. ¿En qué tienda vas a hacer la compra?", sugerencias=TIENDAS)


def registrar_feedback(req: FeedbackRequest) -> FeedbackResponse:
    """Guarda la valoración, aprende de ella (ver feedback.py) y encadena la siguiente pregunta."""
    sesion = sesiones.buscar(req.session_id)
    if sesion is None:
        raise NoEncontrado(f"Sesión {req.session_id} no existe")
    respuesta = feedback.registrar(sesion, req)
    sesiones.guardar(sesion)
    return respuesta
