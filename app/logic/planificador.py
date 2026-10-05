import re
import unicodedata
import uuid

from app.data.catalogo import get_recetas
from app.logic.carrito import construir_carrito, extras_de
from app.logic.errores import DatosInvalidos
from app.models.schemas import PeticionPlan, PlanResponse, Receta


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def dias_sin_cocinar(peticion: PeticionPlan) -> set[str]:
    """Días (tal cual vienen en `dias`) en los que la restricción dice "no cocino".

    Solo reconoce frases simples ("el martes no cocino"). TODO: el resto de
    restricciones en texto libre se interpretarán con el LLM.
    """
    if not peticion.restricciones:
        return set()
    resultado = set()
    for frase in re.split(r"[.;\n]", _norm(peticion.restricciones)):
        if "no cocin" not in frase:
            continue
        for dia in peticion.dias:
            if _norm(dia) in frase:
                resultado.add(dia)
    return resultado


def _total(dias: dict[str, Receta], comensales: int) -> float:
    return construir_carrito(list(dias.values()), comensales).total


def _seleccion_inicial(peticion: PeticionPlan, recetas: list[Receta]) -> dict[str, Receta]:
    sin_cocinar = dias_sin_cocinar(peticion)
    por_tipo = {
        "cocinar": [r for r in recetas if r.tipo == "cocinar"],
        "listo_para_comer": [r for r in recetas if r.tipo == "listo_para_comer"],
    }
    usadas = {"cocinar": 0, "listo_para_comer": 0}
    plan = {}
    for dia in peticion.dias:
        tipo = "listo_para_comer" if dia in sin_cocinar else "cocinar"
        pool = por_tipo[tipo]
        if not pool:
            raise DatosInvalidos(f"No hay recetas de tipo {tipo}")
        plan[dia] = pool[usadas[tipo] % len(pool)]  # sin repetir hasta agotar el pool
        usadas[tipo] += 1
    return plan


def _ajustar_a_presupuesto(plan: dict[str, Receta], recetas: list[Receta], comensales: int, presupuesto: float):
    """Cambia, de uno en uno, el plato que más abarata el total hasta cumplir el presupuesto."""
    while _total(plan, comensales) > presupuesto:
        total_actual = _total(plan, comensales)
        usadas = {r.id for r in plan.values()}
        mejor = None  # (total, dia, receta)
        for dia, actual in plan.items():
            libres = [r for r in recetas if r.tipo == actual.tipo and r.id not in usadas]
            candidatas = libres or [r for r in recetas if r.tipo == actual.tipo and r.id != actual.id]
            for cand in candidatas:
                total = _total({**plan, dia: cand}, comensales)
                if total < total_actual - 1e-9 and (mejor is None or total < mejor[0]):
                    mejor = (total, dia, cand)
        if mejor is None:
            return
        plan[mejor[1]] = mejor[2]


def generar_plan(peticion: PeticionPlan) -> PlanResponse:
    if not peticion.dias:
        raise DatosInvalidos("Hay que indicar al menos un día")
    if len(set(peticion.dias)) != len(peticion.dias):
        raise DatosInvalidos("Hay días repetidos")

    recetas = get_recetas()
    plan = _seleccion_inicial(peticion, recetas)
    if peticion.presupuesto is not None:
        _ajustar_a_presupuesto(plan, recetas, peticion.comensales, peticion.presupuesto)

    carrito = construir_carrito(list(plan.values()), peticion.comensales)
    return PlanResponse(
        id=uuid.uuid4().hex[:8],
        dias=plan,
        carrito=carrito,
        total=carrito.total,
        extras=extras_de(list(plan.values())),
        comensales=peticion.comensales,
        presupuesto=peticion.presupuesto,
        dentro_presupuesto=None if peticion.presupuesto is None else carrito.total <= peticion.presupuesto,
    )
