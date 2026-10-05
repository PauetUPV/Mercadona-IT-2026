import pytest

from app.data.catalogo import get_receta, get_recetas
from app.logic import planificador
from app.logic.carrito import escalar_receta, lista_compra, precio_receta, total_plan
from app.logic.errores import DatosInvalidos, Inviable, NoEncontrado, SinAlternativa
from app.logic.planificador import Peticion

DIAS = ["lunes", "martes", "miércoles"]


def plan(**kw):
    return planificador.generar_plan(Peticion(**{"comensales": 2, "dias": DIAS, **kw}))


def test_recetas_mock_validas():
    recetas = get_recetas()
    assert {r.tipo for r in recetas} == {"cocinar", "listo_para_comer"}
    for r in recetas:
        assert r.ingredientes and r.precio_estimado > 0
        if r.tipo == "listo_para_comer":
            assert not r.instrucciones
        else:
            assert r.instrucciones


def test_escalado_por_comensales():
    r = get_receta("r1")
    e = escalar_receta(r, 4, "comida")
    assert e.raciones == 4 and e.momento == "comida"
    assert e.ingredientes[0].unidades == pytest.approx(r.ingredientes[0].unidades * 2)
    assert precio_receta(r, 4) == pytest.approx(precio_receta(r, 2) * 2, abs=0.02)


def test_plan_basico():
    p = plan()
    assert list(p.dias) == DIAS
    assert all(len(rs) == 1 and rs[0].momento == "comida" for rs in p.dias.values())
    assert len({rs[0].id for rs in p.dias.values()}) == 3  # sin repetir
    assert total_plan(p) > 0 and p.en_casa and p.id


def test_comida_y_cena():
    p = plan(momentos=["comida", "cena"])
    assert all([r.momento for r in rs] == ["comida", "cena"] for rs in p.dias.values())
    assert len({r.id for rs in p.dias.values() for r in rs}) == 6


def test_lista_compra_envases_enteros():
    p = plan(comensales=3)
    for _, envases, subtotal in lista_compra(p):
        assert isinstance(envases, int) and envases >= 1 and subtotal > 0


def test_dia_sin_cocinar_y_orden_semana():
    p = plan(dias=["viernes", "lunes"], sin_cocinar={"viernes"})
    assert list(p.dias) == ["lunes", "viernes"]
    assert p.dias["viernes"][0].tipo == "listo_para_comer" and p.dias["lunes"][0].tipo == "cocinar"


def test_dietas_excluyen_etiquetas():
    p = plan(dias=["lunes", "martes", "miércoles", "jueves", "viernes"], excluir={"carne", "pescado"})
    assert all(not ({"carne", "pescado"} & set(r.etiquetas)) for rs in p.dias.values() for r in rs)


def test_dieta_imposible():
    listos = {r.id for r in get_recetas() if r.tipo == "listo_para_comer"}
    with pytest.raises(DatosInvalidos):  # no queda ningún plato listo para el día sin cocinar
        plan(sin_cocinar={"lunes"}, rechazadas=listos)


def test_recetario_amplio_y_coherente():
    recetas = get_recetas()
    assert len({r.id for r in recetas}) == len(recetas) >= 60
    assert sum(r.tipo == "cocinar" for r in recetas) >= 40
    for r in recetas:
        assert all(0.01 <= i.unidades <= 6 for i in r.ingredientes), r.id  # cantidades razonables
        assert 0.5 <= r.precio_estimado <= 15, r.id
    # una semana completa de comida y cena, vegetariana, es posible sin repetir platos
    p = plan(dias=["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
             momentos=["comida", "cena"], excluir={"carne", "pescado"})
    assert len({r.id for rs in p.dias.values() for r in rs}) == 14


def test_presupuesto_reduce_coste():
    libre = total_plan(plan())
    assert total_plan(plan(presupuesto=libre - 2)) < libre


def test_presupuesto_imposible_avisa_con_el_minimo():
    with pytest.raises(Inviable) as e:
        plan(presupuesto=1)
    assert e.value.minimo > 1


@pytest.mark.parametrize("kw", [{"comensales": 0}, {"comensales": 50}, {"presupuesto": 0}, {"dias": []}, {"dias": ["funday"]}])
def test_peticiones_absurdas(kw):
    with pytest.raises(DatosInvalidos):
        plan(**kw)


def test_dias_repetidos_se_unifican():
    assert list(plan(dias=["lunes", "lunes", "Lunes"]).dias) == ["lunes"]


def test_cambiar_plato():
    p = plan()
    nuevo = planificador.cambiar_plato(p, "Lunes")
    assert nuevo.id != p.id
    assert nuevo.dias["lunes"][0].id != p.dias["lunes"][0].id
    assert nuevo.dias["lunes"][0].tipo == p.dias["lunes"][0].tipo
    assert nuevo.dias["lunes"][0].raciones == 2
    assert nuevo.dias["martes"] == p.dias["martes"]


def test_cambiar_plato_respeta_presupuesto():
    from app.models.schemas import PlanResponse

    def solo(r):
        return PlanResponse(id="x", dias={"lunes": [escalar_receta(r, 2, "comida")]})

    cocinar = [r for r in get_recetas() if r.tipo == "cocinar"]
    barato = min(cocinar, key=lambda r: total_plan(solo(r)))  # la más barata en envases enteros
    p = solo(barato)
    with pytest.raises(SinAlternativa):  # cualquier otra cuesta más y no cabe en su propio coste
        planificador.cambiar_plato(p, "lunes", presupuesto=total_plan(p))
    # sin presupuesto sí se puede
    assert planificador.cambiar_plato(p, "lunes").dias["lunes"][0].id != barato.id


def test_cambiar_plato_errores():
    p = plan()
    with pytest.raises(NoEncontrado):
        planificador.cambiar_plato(p, "domingo")
    with pytest.raises(NoEncontrado):
        planificador.cambiar_plato(p, "lunes", momento="cena")


def test_extras():
    from app.data.catalogo import mejor_producto

    leche = mejor_producto("leche")
    assert leche and leche.categoria == "Huevos, leche y mantequilla"
    p = plan()
    con = planificador.anadir_extra(p, leche)
    assert con.extras[0].unidades == 1 and con.id != p.id
    assert planificador.anadir_extra(con, leche).extras[0].unidades == 2
    sin, quitado = planificador.quitar_extra(con, "leche")
    assert sin.extras == [] and quitado.id == leche.id
    with pytest.raises(NoEncontrado):
        planificador.quitar_extra(p, "leche")


def test_extras_cuentan_en_el_total():
    from app.data.catalogo import mejor_producto

    p = plan()
    assert total_plan(planificador.anadir_extra(p, mejor_producto("leche"))) > total_plan(p)
