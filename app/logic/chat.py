"""Orquestación de un turno de chat:

    mensaje -> agente.interpretar (clasifica) -> se ejecuta la acción (código determinista, con reglas
    de viabilidad) -> se actualiza el estado de la sesión -> agente.redactar (texto) -> respuesta.
"""
import uuid
from typing import Optional

from app.data import catalogo
from app.logic import agente, apertura, planificador, sesiones, sugerencias
from app.logic.carrito import total_plan
from app.logic.errores import DatosInvalidos, Inviable, NoEncontrado, SinAlternativa
from app.logic.interprete import Interpretacion
from app.logic.planificador import Peticion
from app.logic.sesiones import Sesion
from app.logic.texto import DIAS_SEMANA, norm
from app.models.schemas import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse, ListaRequest, ListaResponse, MensajeChat, PlanResponse

# NUEVO: Importamos el cerebro de la IA
from app.logic.llm import consultar_llm

DIAS_POR_DEFECTO = DIAS_SEMANA[:5]  # lunes a viernes

def _platos(plan: PlanResponse) -> dict[str, list[str]]:
    return {d: [r.nombre for r in rs] for d, rs in plan.dias.items()}


def _plan_con_hechos(sesion: Sesion, i: Interpretacion) -> tuple[dict, Optional[PlanResponse]]:
    """Crear o rehacer el plan con los datos nuevos mezclados con las preferencias de la sesión."""
    comensales = i.comensales or sesion.comensales
    presupuesto = i.presupuesto if i.presupuesto is not None else sesion.presupuesto
    excluir = sorted(set(sesion.excluir) | set(i.excluir))
    momentos = list(i.momentos or sesion.momentos)
    sin_cocinar = sorted(set(sesion.sin_cocinar) | set(i.sin_cocinar))
    dias = list(i.dias or (sesion.plan.dias if sesion.plan else None) or sesion.dias or DIAS_POR_DEFECTO)
    for d in i.sin_cocinar:  # un día marcado como "no cocino" también es un día del plan
        if all(norm(d) != norm(x) for x in dias):
            dias.append(d)

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
    return {"tipo": "plan", "exito": True, "comensales": comensales, "platos": _platos(plan)}, plan


def _cambiar_plato(sesion: Sesion, i: Interpretacion) -> tuple[dict, Optional[PlanResponse]]:
    if sesion.plan is None:
        return {"tipo": "sin_plan"}, None
    if not i.dia:
        return {"tipo": "rechazo", "exito": False, "motivo": "¿Qué día quieres cambiar?"}, None
    try:
        nuevo = planificador.cambiar_plato(
            sesion.plan, i.dia, i.momento, sesion.presupuesto, set(sesion.excluir), set(sesion.rechazadas)
        )
    except (NoEncontrado, SinAlternativa) as e:
        tipo = "sin_alternativa" if isinstance(e, SinAlternativa) else "rechazo"
        return {"tipo": tipo, "exito": False, "motivo": str(e)}, None
    dia = next(d for d in nuevo.dias if norm(d) == norm(i.dia))
    sesion.plan = nuevo
    return {"tipo": "cambio_plato", "exito": True, "dia": dia, "nuevo": " y ".join(r.nombre for r in nuevo.dias[dia])}, nuevo


def _extra(sesion: Sesion, i: Interpretacion, anadir: bool) -> tuple[dict, Optional[PlanResponse]]:
    if sesion.plan is None:
        return {"tipo": "sin_plan"}, None
    busqueda = i.producto or ""
    if anadir:
        producto = catalogo.mejor_producto(busqueda)
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


def procesar(req: ChatRequest) -> ChatResponse:
    sesion = sesiones.obtener(req.session_id)
    if req.plan is not None:  # el usuario lo ha editado: lo que ve manda sobre lo que teníamos guardado
        sesion.plan = req.plan
    sesion.mensajes.append(MensajeChat(rol="usuario", texto=req.mensaje))

    i = agente.interpretar(req.mensaje, sesion)
    if i.accion == "plan":
        hechos, plan = _plan_con_hechos(sesion, i)
    elif i.accion == "cambiar_plato":
        hechos, plan = _cambiar_plato(sesion, i)
    elif i.accion in ("anadir_extra", "quitar_extra"):
        hechos, plan = _extra(sesion, i, anadir=i.accion == "anadir_extra")
    else:
        hechos, plan = ({"tipo": "charla", "respuesta": i.respuesta} if i.respuesta else {"tipo": "no_entiendo"}), None

    mensaje, conclusion = agente.redactar(hechos, i)
    sesion.mensajes.append(MensajeChat(rol="asistente", texto=mensaje))
    sesiones.guardar(sesion)
    chips = sugerencias.para(hechos, sesion)
    return ChatResponse(
        session_id=sesion.id, mensaje=mensaje, mensaje_conclusion=conclusion, plan=plan, sugerencias=chips or None
    )


def guardar_lista(req: ListaRequest) -> ListaResponse:
    sesion = sesiones.buscar(req.session_id)
    if sesion is None:
        raise NoEncontrado(f"Sesión {req.session_id} no existe")
    for linea in req.lineas:
        if catalogo.get_producto(linea.producto_id) is None:
            raise DatosInvalidos(f"El producto {linea.producto_id} no existe")
    lista_id = "l_" + uuid.uuid4().hex[:4]
    sesion.listas.append(
        {"lista_id": lista_id, "plan_id": req.plan_id, "nombre": req.nombre, "lineas": [l.model_dump() for l in req.lineas]}
    )
    sesiones.guardar(sesion)
    return ListaResponse(lista_id=lista_id, mensaje="Guardada. Luego te pregunto qué tal salió.")


def registrar_feedback(req: FeedbackRequest) -> FeedbackResponse:
    """Provisional: guarda la valoración y, si es negativa sobre una receta, no la vuelve a proponer."""
    sesion = sesiones.buscar(req.session_id)
    if sesion is None:
        raise NoEncontrado(f"Sesión {req.session_id} no existe")
    sesion.feedback.append(req.model_dump())
    if req.valor == "negativo" and req.sujeto.tipo == "receta" and req.sujeto.id not in sesion.rechazadas:
        sesion.rechazadas.append(req.sujeto.id)
    sesiones.guardar(sesion)
    if req.valor == "negativo" and not req.motivo:  # primero entendemos qué falló; luego seguimos preguntando
        return FeedbackResponse(mensaje="Vaya, lo siento. ¿Qué falló?", sugerencias=["Estaba soso", "Muy caro", "No me gustó"])
    gracias = "¡Me alegro!" if req.valor == "positivo" else "Gracias, no te lo volveré a proponer."
    siguiente = apertura.sujeto_pendiente(sesion)
    if siguiente:
        return FeedbackResponse(mensaje=f"{gracias} ¿Y qué tal salió «{siguiente.nombre}»?", feedback=siguiente)
    return FeedbackResponse(mensaje=f"{gracias} Lo tendré en cuenta para la próxima semana.")
