from app.data.catalogo import get_recetas
from app.logic.carrito import construir_carrito, extras_de
from app.logic.errores import DatosInvalidos, NoEncontrado
from app.models.schemas import PeticionSustitucion, PlanResponse


def sustituir_plato(peticion: PeticionSustitucion) -> PlanResponse:
    """Cambia el plato de `dia` por otro del mismo tipo y precio parecido."""
    plan = peticion.plan
    actual = plan.dias.get(peticion.dia)
    if actual is None:
        raise NoEncontrado(f"El plan no tiene el día {peticion.dia!r}")

    usadas = {r.id for r in plan.dias.values()}
    mismo_tipo = [r for r in get_recetas() if r.tipo == actual.tipo and r.id != actual.id]
    candidatas = [r for r in mismo_tipo if r.id not in usadas] or mismo_tipo
    if not candidatas:
        raise DatosInvalidos("No hay recetas alternativas")

    nueva = min(candidatas, key=lambda r: abs(r.precio_estimado - actual.precio_estimado))
    dias = {**plan.dias, peticion.dia: nueva}
    comensales = peticion.comensales or plan.comensales
    if not comensales:
        raise DatosInvalidos("Faltan los comensales")
    carrito = construir_carrito(list(dias.values()), comensales)

    dentro = None if plan.presupuesto is None else carrito.total <= plan.presupuesto
    return PlanResponse(
        id=plan.id,
        dias=dias,
        carrito=carrito,
        total=carrito.total,
        extras=extras_de(list(dias.values())),
        comensales=comensales,
        presupuesto=plan.presupuesto,
        dentro_presupuesto=dentro,
    )
