"""Respuestas a preguntas sobre la sesión ("¿qué como el martes?", "¿cómo se hace la tortilla?").

Las responde el código con los datos guardados (plan, recetas, preferencias), no el LLM, para que sean exactas.
Ninguna pregunta cambia el plan.
"""
from typing import Optional

from app.data import catalogo
from app.logic.carrito import total_plan
from app.logic.interprete import Interpretacion
from app.logic.mensajes import euros
from app.logic.sesiones import Sesion
from app.logic.texto import norm
from app.models.schemas import Ingrediente, Receta


def cantidad(ing: Ingrediente) -> str:
    """'300 g', '400 ml', '2 ud' o, si no se sabe el tamaño, '0,5 envases'."""
    p = ing.producto
    if p.tamano and p.formato_tamano in ("kg", "l"):
        valor = round(ing.unidades * p.tamano * 1000)
        return f"{valor} {'g' if p.formato_tamano == 'kg' else 'ml'}"
    if p.tamano and p.formato_tamano == "ud":
        return f"{ing.unidades * p.tamano:g} ud"
    return f"{ing.unidades:g} envase(s)".replace(".", ",")


def _recetas_del_plan(sesion: Sesion) -> list[tuple[str, Receta]]:
    return [(d, r) for d, rs in sesion.plan.dias.items() for r in rs] if sesion.plan else []


def receta_aludida(sesion: Sesion, i: Interpretacion) -> Optional[Receta]:
    """La receta de la que pregunta: por día, por nombre (primero en su plan, luego en el recetario) o la última citada."""
    del_plan = _recetas_del_plan(sesion)
    if i.dia:
        candidatas = [r for d, r in del_plan if norm(d) == norm(i.dia) and (not i.momento or r.momento == i.momento)]
        if candidatas:
            return candidatas[0]
    if i.plato:
        pedidas = set(catalogo._tokens_plato(i.plato))
        if pedidas:
            # Su plan tiene preferencia, salvo que una receta del recetario encaje mejor
            # ("tortilla de patata" no es "Costillas al horno con patatas" aunque compartan "patata")
            puntuadas = [(len(pedidas & set(catalogo._tokens_plato(r.nombre))), r) for _, r in del_plan]
            comunes_plan, del_plan_mejor = max(puntuadas, key=lambda x: x[0], default=(0, None))
            receta, parecido, _ = catalogo.buscar_receta(i.plato)
            comunes_recetario = round(parecido * len(pedidas)) if receta else 0
            if del_plan_mejor and comunes_plan > 0 and comunes_plan >= comunes_recetario:
                return del_plan_mejor
            if receta and parecido >= 0.5:
                return receta
    if sesion.ultima_receta:
        return next((r for _, r in del_plan if r.id == sesion.ultima_receta), None) or catalogo.get_receta(sesion.ultima_receta)
    return None


def responder(sesion: Sesion, i: Interpretacion) -> dict:
    """Hechos de la consulta, con la respuesta ya redactada en `texto` (exacta, a partir de los datos)."""
    tema = i.tema or "otro"
    plan = sesion.plan

    if tema == "menu":
        if plan is None:
            return {"tipo": "consulta", "tema": tema, "texto": "Aún no tienes plan. Dime para cuántas personas y lo preparo."}
        dias = {d: rs for d, rs in plan.dias.items() if not i.dia or norm(d) == norm(i.dia)}
        if not dias:
            return {"tipo": "consulta", "tema": tema, "texto": f"El {i.dia} no está en tu plan. ¿Quieres que lo añada?"}
        partes = []
        for d, rs in dias.items():
            recetas = [r for r in rs if not i.momento or r.momento == i.momento] or rs
            partes.append(f"{d}: " + " y ".join(f"{r.nombre}{f' ({r.momento})' if len(rs) > 1 else ''}" for r in recetas))
        texto = ("El " if len(dias) == 1 else "Tu menú: ") + "; ".join(partes) + "."
        if not i.dia and plan.extras:
            texto += " Además tienes en la compra: " + ", ".join(e.producto.nombre for e in plan.extras) + "."
        if len(dias) == 1:
            sesion.ultima_receta = next(iter(dias.values()))[0].id
            return {"tipo": "consulta", "tema": tema, "texto": texto, "dia": next(iter(dias))}
        return {"tipo": "consulta", "tema": tema, "texto": texto}

    if tema in ("receta", "ingredientes"):
        receta = receta_aludida(sesion, i)
        if receta is None:
            return {"tipo": "consulta", "tema": tema, "texto": "¿De qué plato? Dime el día o el nombre."}
        sesion.ultima_receta = receta.id
        if tema == "receta":
            if not receta.instrucciones:
                texto = f"«{receta.nombre}» viene listo para comer: solo hay que calentarlo o servirlo."
            else:
                texto = f"{receta.nombre}: {receta.instrucciones}"
                if receta.en_casa:
                    texto += f" Necesitarás también {', '.join(receta.en_casa)}."
        else:
            lista = ", ".join(f"{ing.producto.nombre} ({cantidad(ing)})" for ing in receta.ingredientes)
            texto = f"{receta.nombre} para {receta.raciones} persona(s) lleva: {lista}."
            if receta.en_casa:
                texto += f" Y de casa: {', '.join(receta.en_casa)}."
        return {"tipo": "consulta", "tema": tema, "texto": texto}

    if tema == "coste":
        if plan is None:
            return {"tipo": "consulta", "tema": tema, "texto": "Aún no tienes plan, así que no hay nada que calcular."}
        total = total_plan(plan)
        texto = f"Con el plan tal como lo tienes, la compra sale por unos {euros(total)} (en envases enteros)."
        if sesion.presupuesto is not None:
            texto += (
                f" Entra en tu presupuesto de {euros(sesion.presupuesto)}." if total <= sesion.presupuesto
                else f" Te pasas {euros(total - sesion.presupuesto)} de tu presupuesto de {euros(sesion.presupuesto)}."
            )
        return {"tipo": "consulta", "tema": tema, "texto": texto}

    if tema == "en_casa":
        if not plan or not plan.en_casa:
            return {"tipo": "consulta", "tema": tema, "texto": "No necesitas nada especial de casa."}
        return {"tipo": "consulta", "tema": tema, "texto": "Lo que se supone que ya tienes en casa: " + ", ".join(plan.en_casa) + "."}

    if tema == "preferencias":
        partes = []
        if sesion.comensales:
            partes.append(f"sois {sesion.comensales} persona(s)")
        partes.append(f"presupuesto de {euros(sesion.presupuesto)}" if sesion.presupuesto is not None else "sin presupuesto fijo")
        if plan:
            partes.append("días: " + ", ".join(plan.dias))
        if sesion.momentos != ["comida"]:
            partes.append(" y ".join(sesion.momentos))
        if sesion.excluir:
            partes.append("evitas " + ", ".join(sesion.excluir))
        if sesion.sin_cocinar:
            partes.append("no cocinas el " + " ni el ".join(sesion.sin_cocinar))
        if sesion.favoritas:
            nombres = [r.nombre for rid in sesion.favoritas if (r := catalogo.get_receta(rid))]
            partes.append("te gustaron " + ", ".join(nombres))
        if sesion.prefiere_barato:
            partes.append("prefieres opciones baratas")
        if sesion.prefiere_facil:
            partes.append("prefieres platos sencillos")
        if sesion.fijos:
            nombres = [r.nombre for f in sesion.fijos if (r := catalogo.get_receta(f["receta_id"]))]
            if nombres:
                partes.append("me pediste " + ", ".join(nombres))
        return {"tipo": "consulta", "tema": tema, "texto": "Lo que tengo apuntado: " + "; ".join(partes) + "."}

    # "otro" (¿esto es sano?, ¿con qué lo acompaño?): lo contesta Gemini con el plan en el contexto; sin LLM, se reconduce
    return {
        "tipo": "consulta",
        "tema": "otro",
        "texto": "Eso no lo sé responder bien. Puedo contarte el menú, cómo se hace un plato, qué lleva o cuánto cuesta la compra.",
    }
