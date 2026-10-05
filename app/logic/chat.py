from app.logic import historial, sesiones
from app.logic.errores import DatosInvalidos, NoEncontrado
from app.logic.interprete import DIAS_SEMANA, norm, interpretar
from app.logic.planificador import generar_plan
from app.logic.sustituciones import sustituir_plato
from app.models.schemas import ChatRequest, ChatResponse, MensajeChat, PeticionPlan, PeticionSustitucion

# NUEVO: Importamos el cerebro de la IA
from app.logic.llm import consultar_llm

DIAS_POR_DEFECTO = DIAS_SEMANA[:5]  # lunes a viernes

def _orden_semana(dia: str) -> int:
    ordenados = [norm(d) for d in DIAS_SEMANA]
    return ordenados.index(norm(dia)) if norm(dia) in ordenados else len(ordenados)


def _responder(sesion: sesiones.Sesion, texto: str) -> ChatResponse:
    """Guarda en la base de datos y devuelve el JSON oficial."""
    sesion.mensajes.append(MensajeChat(rol="asistente", texto=texto))
    return ChatResponse(session_id=sesion.id, mensaje=texto, plan=sesion.plan)


def _responder_con_ia(sesion: sesiones.Sesion, mensaje_usuario: str, directriz_sistema: str = "") -> ChatResponse:
    """NUEVO: Usa Gemini para generar una respuesta natural en lugar de un texto robótico."""
    if directriz_sistema:
        # El sistema necesita algo concreto, se lo inyectamos a Gemini como una orden oculta
        prompt = f"El usuario ha dicho: '{mensaje_usuario}'.\nInstrucción para ti: {directriz_sistema}"
    else:
        # El usuario solo está charlando (saludos, dudas...), dejamos que la IA responda sola
        prompt = mensaje_usuario
        
    texto_ia = consultar_llm(prompt)
    return _responder(sesion, texto_ia)


def _sustituir(sesion: sesiones.Sesion, dia_norm: str, mensaje_usuario: str) -> ChatResponse:
    if sesion.plan is None:
        return _responder_con_ia(sesion, mensaje_usuario, "Dile que no hay ningún plan activo y que primero debe pedir uno.")
    dia = next((d for d in sesion.plan.dias if norm(d) == norm(dia_norm)), None)
    if dia is None:
        return _responder_con_ia(sesion, mensaje_usuario, f"Dile amablemente que el día {dia_norm} no está en su menú actual.")
    try:
        sesion.plan = sustituir_plato(PeticionSustitucion(plan=sesion.plan, dia=dia, comensales=sesion.comensales))
    except (NoEncontrado, DatosInvalidos) as e:
        return _responder_con_ia(sesion, mensaje_usuario, f"Comunícale este error de forma suave: {str(e)}")
    historial.registrar_sustitucion(sesion.plan)
    return _responder_con_ia(sesion, mensaje_usuario, f"Confírmale con alegría que has cambiado el plato del {dia}.")


def procesar(req: ChatRequest) -> ChatResponse:
    sesion = sesiones.obtener(req.session_id)
    sesion.mensajes.append(MensajeChat(rol="usuario", texto=req.mensaje))
    i = interpretar(req.mensaje)

    # Cambiar un plato del plan actual
    if i.quiere_sustituir and not i.aporta_datos:
        if i.sustituir_dia:
            return _sustituir(sesion, i.sustituir_dia, req.mensaje)
        return _responder_con_ia(sesion, req.mensaje, "Pregúntale para qué día de la semana quiere cambiar la comida.")

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
        # MAGIA: Si no es un comando del menú ("hola", "¿quién eres?"), Gemini responde al natural
        return _responder_con_ia(sesion, req.mensaje)
        
    if not sesion.comensales:
        return _responder_con_ia(sesion, req.mensaje, "Pregúntale amablemente cuántos comensales van a comer.")

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
        return _responder_con_ia(sesion, req.mensaje, f"Explícale este error de forma sencilla: {str(e)}")
        
    sesion.plan = plan
    historial.registrar_plan(plan, sesion.presupuesto)
    
    return _responder_con_ia(sesion, req.mensaje, "Comunícale con entusiasmo que su nuevo menú ya está listo y generado en su pantalla.")