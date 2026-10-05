import pytest

from app.data.catalogo import get_receta, get_recetas
from app.logic.carrito import construir_carrito, precio_receta
from app.logic.errores import DatosInvalidos, NoEncontrado
from app.logic.planificador import dias_sin_cocinar, generar_plan
from app.logic.sustituciones import sustituir_plato
from app.models.schemas import PeticionPlan, PeticionSustitucion

DIAS = ["lunes", "martes", "miércoles"]


def test_precio_receta_escala_con_comensales():
    r = get_receta("r1")
    assert precio_receta(r, 4) == pytest.approx(precio_receta(r, 2) * 2, abs=0.02)


def test_carrito_total_y_envases_enteros():
    r = get_receta("r2")
    carrito = construir_carrito([r], comensales=2)
    assert carrito.total == pytest.approx(sum(l.subtotal for l in carrito.lineas))
    assert all(isinstance(l.unidades, int) and l.unidades >= 1 for l in carrito.lineas)


def test_carrito_agrega_ingredientes_repetidos():
    r = get_receta("r1")
    una = construir_carrito([r], 2)
    dos = construir_carrito([r, r], 2)
    # mismas líneas (mismos productos), más unidades o igual por redondeo
    assert {l.producto.id for l in una.lineas} == {l.producto.id for l in dos.lineas}
    assert dos.total >= una.total


def test_plan_basico():
    plan = generar_plan(PeticionPlan(comensales=2, dias=DIAS))
    assert list(plan.dias) == DIAS
    assert len({r.id for r in plan.dias.values()}) == 3  # sin repetir
    assert plan.total == plan.carrito.total > 0
    assert plan.dentro_presupuesto is None


def test_dia_sin_cocinar():
    peticion = PeticionPlan(comensales=2, dias=DIAS, restricciones="El martes no cocino")
    assert dias_sin_cocinar(peticion) == {"martes"}
    plan = generar_plan(peticion)
    assert plan.dias["martes"].tipo == "listo_para_comer"
    assert plan.dias["lunes"].tipo == "cocinar"


def test_presupuesto_reduce_total():
    libre = generar_plan(PeticionPlan(comensales=2, dias=DIAS))
    ajustado = generar_plan(PeticionPlan(comensales=2, dias=DIAS, presupuesto=libre.total - 3))
    assert ajustado.total < libre.total


def test_presupuesto_imposible():
    plan = generar_plan(PeticionPlan(comensales=2, dias=DIAS, presupuesto=0.5))
    assert plan.dentro_presupuesto is False


def test_dias_repetidos():
    with pytest.raises(DatosInvalidos):
        generar_plan(PeticionPlan(comensales=2, dias=["lunes", "lunes"]))


def test_sustituir_cambia_plato_del_mismo_tipo():
    plan = generar_plan(PeticionPlan(comensales=2, dias=DIAS))
    original = plan.dias["lunes"]
    nuevo = sustituir_plato(PeticionSustitucion(plan=plan, dia="lunes", comensales=2))
    assert nuevo.dias["lunes"].id != original.id
    assert nuevo.dias["lunes"].tipo == original.tipo
    assert nuevo.dias["martes"] == plan.dias["martes"]
    assert nuevo.id == plan.id
    assert nuevo.total == nuevo.carrito.total


def test_sustituir_dia_inexistente():
    plan = generar_plan(PeticionPlan(comensales=2, dias=DIAS))
    with pytest.raises(NoEncontrado):
        sustituir_plato(PeticionSustitucion(plan=plan, dia="domingo", comensales=2))


def test_hay_recetas_de_ambos_tipos():
    tipos = {r.tipo for r in get_recetas()}
    assert tipos == {"cocinar", "listo_para_comer"}
