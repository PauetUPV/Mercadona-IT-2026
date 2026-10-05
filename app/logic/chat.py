from app.logic import historial, mensajes, sesiones
from app.logic.errores import DatosInvalidos, NoEncontrado
from app.logic.interprete import DIAS_SEMANA, norm, interpretar
from app.logic.planificador import generar_plan
from app.logic.sustituciones import sustituir_plato
from app.models.schemas import ChatRequest, ChatResponse, MensajeChat, PeticionPlan, PeticionSustitucion

DIAS_POR_DEFECTO = DIAS_SEMANA[:5]  # lunes a viernes


def _orden_semana(dia: str) -> int:
    ordenados = [norm(d) for d in DIAS_SEMANA]
    return ordenados.index(norm(dia)) if norm(dia) in ordenados else len(ordenados)


def _responder(sesion: sesiones.Sesion, texto: str) -> ChatResponse:
    sesion.mensajes.append(MensajeChat(rol="asistente", texto=texto))
    return ChatResponse(session_id=sesion.id, mensaje=texto, plan=sesion.plan)


def _sustituir(sesion: sesiones.Sesion, dia_norm: str) -> ChatResponse:
    if sesion.plan is None:
        return _responder(sesion, mensajes.SIN_PLAN)
    dia = next((d for d in sesion.plan.dias if norm(d) == norm(dia_norm)), None)
    if dia is None:
        return _responder(sesion, f"El {dia_norm} no está en tu plan.")
    try:
        sesion.plan = sustituir_plato(PeticionSustitucion(plan=sesion.plan, dia=dia, comensales=sesion.comensales))
    except (NoEncontrado, DatosInvalidos) as e:
        return _responder(sesion, str(e))
    historial.registrar_sustitucion(sesion.plan)
    return _responder(sesion, mensajes.plan_sustituido(sesion.plan, dia))


def procesar(req: ChatRequest) -> ChatResponse:
    sesion = sesiones.obtener(req.session_id)
    sesion.mensajes.append(MensajeChat(rol="usuario", texto=req.mensaje))
    i = interpretar(req.mensaje)

    # Cambiar un plato del plan actual
    if i.quiere_sustituir and not i.aporta_datos:
        if i.sustituir_dia:
            return _sustituir(sesion, i.sustituir_dia)
        return _responder(sesion, mensajes.PREGUNTA_DIA)

    # Datos nuevos: lo enviado explícitamente manda sobre lo interpretado del texto
    comensales = req.comensales or i.comensales
    presupuesto = req.presupuesto if req.presupuesto is not None else i.presupuesto
    dias = req.dias or i.dias
    hay_novedad = bool(comensales or presupuesto is not None or dias or i.sin_cocinar)

    if comensales:
        sesion.comensales = comensales
    if presupuesto is not None:
        sesion.presupuesto = presupuesto
    if dias:
        sesion.dias = dias
    sesion.restricciones += [c for c in i.clausulas_no_cocino if c not in sesion.restricciones]

    if not hay_novedad:
        return _responder(sesion, mensajes.NO_ENTIENDO)
    if not sesion.comensales:
        return _responder(sesion, mensajes.PREGUNTA_COMENSALES)

    # Días del plan: los indicados, o lunes-viernes; los de "no cocino" también cuentan
    plan_dias = list(sesion.dias or DIAS_POR_DEFECTO)
    for d in i.sin_cocinar:
        if all(norm(d) != norm(x) for x in plan_dias):
            plan_dias.append(d)
    plan_dias.sort(key=_orden_semana)

    try:
        plan = generar_plan(
            PeticionPlan(
                comensales=sesion.comensales,
                presupuesto=sesion.presupuesto,
                dias=plan_dias,
                restricciones=". ".join(sesion.restricciones) or None,
            )
        )
    except DatosInvalidos as e:
        return _responder(sesion, str(e))
    sesion.plan = plan
    historial.registrar_plan(plan, sesion.presupuesto)
    return _responder(sesion, mensajes.plan_nuevo(plan))
