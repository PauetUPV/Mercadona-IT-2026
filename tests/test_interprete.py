from app.logic.interprete import interpretar


def test_datos_basicos():
    i = interpretar("Somos 4, tenemos 60 euros y el martes no cocino")
    assert (i.accion, i.comensales, i.presupuesto) == ("plan", 4, 60)
    assert i.sin_cocinar == ["martes"] and i.dias is None


def test_rangos_decimales_y_numeros_en_texto():
    i = interpretar("para dos personas de lunes a miércoles, 35,5 €")
    assert i.comensales == 2 and i.presupuesto == 35.5 and i.dias == ["lunes", "martes", "miércoles"]


def test_fin_de_semana_y_momentos():
    assert interpretar("plan para el fin de semana").dias == ["sábado", "domingo"]
    assert interpretar("comida y cena de lunes a viernes").momentos == ["comida", "cena"]
    assert interpretar("solo cenas entre semana").momentos == ["cena"]
    assert interpretar("quiero un plan de comidas").momentos is None


def test_dietas_y_alergias():
    assert set(interpretar("soy vegetariano").excluir) == {"carne", "pescado"}
    assert set(interpretar("somos veganos").excluir) == {"carne", "pescado", "huevo", "lactosa"}
    assert interpretar("mi hijo es celíaco").excluir == ["gluten"]
    assert interpretar("tengo alergia al huevo").excluir == ["huevo"]
    assert interpretar("intolerante a la lactosa").excluir == ["lactosa"]


def test_cambiar_plato():
    i = interpretar("cambia el lunes")
    assert (i.accion, i.dia, i.momento) == ("cambiar_plato", "lunes", None)
    assert interpretar("cambia la cena del martes").momento == "cena"
    i = interpretar("cambia otro plato")  # falta el día: el chat lo pregunta
    assert (i.accion, i.dias_cambio, i.objetivo, i.todo) == ("cambiar_plato", [], None, False)


def test_extras():
    i = interpretar("añade leche a la compra")
    assert (i.accion, i.producto) == ("anadir_extra", "leche")
    i = interpretar("quita la leche")
    assert (i.accion, i.producto) == ("quitar_extra", "leche")


def test_peticion_generica_y_ruido():
    assert interpretar("hazme un plan para la semana").accion == "plan"
    assert interpretar("blablabla").accion == "charla"
