"""Negaciones ("no quiero X", "sin cebolla", "ya no soy vegetariano"...) y modelos de reserva de Gemini."""
import datetime

import pytest
from fastapi.testclient import TestClient

from app.logic import llm, sesiones, texto
from app.logic.interprete import interpretar
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def hoy_es_lunes(monkeypatch):
    monkeypatch.setattr(texto, "FECHA_HOY", datetime.date(2026, 10, 5))


def chat(mensaje, session_id="n"):
    r = client.post("/chat", json={"mensaje": mensaje, "session_id": session_id})
    assert r.status_code == 200, r.text
    return r.json()


def todos(plan):
    return [r for rs in plan["dias"].values() for r in rs]


# --- Intérprete (plan B) ----------------------------------------------------------------


@pytest.mark.parametrize(
    "mensaje, esperado",
    [
        ("no quiero pollo al curry", {"accion": "evitar", "no_quiere": ["pollo al curry"]}),
        ("no me apetece lentejas", {"accion": "evitar", "no_quiere": ["lentejas"]}),  # antes PEDÍA lentejas
        ("nada de pizza", {"accion": "evitar", "no_quiere": ["pizza"]}),
        ("sin cebolla", {"accion": "evitar", "no_quiere": ["cebolla"]}),
        ("no quiero más pollo", {"accion": "evitar", "no_quiere": ["pollo"]}),
        ("no quiero lentejas el martes", {"accion": "evitar", "no_quiere": ["lentejas"], "dia": "martes"}),
        ("no somos 4, somos 3", {"comensales": 3}),  # antes se quedaba con 4
        ("ya no soy vegetariano", {"permitir": ["carne", "pescado"], "excluir": []}),  # antes te hacía vegetariano
        ("no me pongas pescado", {"excluir": ["pescado"]}),
        ("el martes no quiero cocinar", {"sin_cocinar": ["martes"], "plato": None}),
        ("no quiero cenas", {"momentos": ["comida"]}),
        ("no tengo presupuesto", {"sin_presupuesto": True}),
        ("quiero pizza pero no carnívora", {"accion": "pedir_plato", "plato": "pizza", "no_quiere": ["carnivora"]}),
        ("no, mejor para mañana", {"dias": ["martes"], "no_quiere": []}),
    ],
)
def test_negaciones_plan_b(mensaje, esperado):
    i = interpretar(mensaje)
    for campo, valor in esperado.items():
        assert getattr(i, campo) == valor, (mensaje, campo, getattr(i, campo))


def test_rechazo_y_peticion_en_el_mismo_mensaje():
    i = interpretar("no quiero pollo al curry, mejor unas lentejas para mañana; somos 3")
    assert (i.accion, i.plato, i.dia, i.comensales, i.no_quiere) == ("pedir_plato", "lentejas", "martes", 3, ["pollo al curry"])


# --- Flujo completo ---------------------------------------------------------------------


def test_no_quiero_un_plato_del_plan_lo_cambia_y_no_vuelve():
    plan = chat("somos 2")["plan"]
    nombre = plan["dias"]["martes"][0]["nombre"]
    r = chat(f"no quiero {nombre.lower()}")
    assert r["plan"]["dias"]["martes"][0]["nombre"] != nombre and "no te pondré" in r["mensaje"]
    r = chat("mejor 80 euros")  # al rehacer el plan tampoco aparece
    assert nombre not in [x["nombre"] for x in todos(r["plan"])]


def test_sin_ingrediente_quita_los_platos_que_lo_llevan():
    chat("somos 2, toda la semana")
    r = chat("sin cebolla")
    for receta in todos(r["plan"]):
        assert all("cebolla" not in i["producto"]["nombre"].lower() for i in receta["ingredientes"]), receta["nombre"]


def test_no_quiero_algo_que_no_esta_en_el_plan_no_cambia_nada():
    plan = chat("somos 2, de lunes a martes", "q")["plan"]
    assert all("Pizza" not in x["nombre"] for x in todos(plan))
    r = chat("nada de pizza", "q")
    assert "plan" not in r and "no te pondré pizza" in r["mensaje"]


def test_rechazo_mas_peticion():
    chat("somos 2")
    chat("quiero pollo al curry el lunes")
    r = chat("no quiero pollo al curry, mejor lentejas")
    assert r["plan"]["dias"]["lunes"][0]["nombre"].startswith("Lentejas")  # ocupa el hueco del rechazado


def test_quiero_pizza_pero_no_carnivora():
    chat("somos 2")
    r = chat("quiero pizza pero no carnívora el martes")
    assert r["plan"]["dias"]["martes"][0]["nombre"].startswith("Pizza")
    assert "carnívora" not in r["plan"]["dias"]["martes"][0]["nombre"]


def test_ya_no_soy_vegetariano():
    chat("somos 2 y soy vegetariano")
    assert sesiones.buscar("n").excluir == ["carne", "pescado"]
    chat("ya no soy vegetariano")
    assert sesiones.buscar("n").excluir == []


def test_correccion_de_comensales_y_sin_presupuesto():
    chat("somos 4 y 100 euros")
    r = chat("no somos 4, somos 3")
    assert r["plan"]["dias"]["lunes"][0]["raciones"] == 3
    chat("no tengo presupuesto")
    assert sesiones.buscar("n").presupuesto is None


def test_no_anadas_leche_quita_el_extra():
    chat("somos 2")
    assert chat("añade leche")["plan"]["extras"]
    r = chat("no añadas leche")
    assert r["plan"]["extras"] == []


# --- Modelos de reserva -----------------------------------------------------------------


class _Respuesta:
    text = '{"accion": "plan", "comensales": 2}'


class _Modelos:
    def __init__(self, fallan):
        self.fallan, self.probados = fallan, []

    def generate_content(self, model, contents, config):
        self.probados.append(model)
        if model in self.fallan:
            raise RuntimeError(self.fallan[model])
        return _Respuesta()


def test_si_el_modelo_esta_saturado_prueba_el_de_reserva(monkeypatch):
    modelos = _Modelos({"principal": "503 UNAVAILABLE"})
    monkeypatch.setattr(llm, "cliente_gemini", type("C", (), {"models": modelos})())
    monkeypatch.setattr(llm, "LLM_MODEL", "principal")
    monkeypatch.setattr(llm, "LLM_MODELOS_RESERVA", ["reserva1", "reserva2"])
    from app.logic.interprete import Interpretacion

    r = llm.generar_json("x", Interpretacion, "s")
    assert r.comensales == 2 and modelos.probados == ["principal", "reserva1"]


def test_error_no_recuperable_va_directo_al_plan_b(monkeypatch):
    modelos = _Modelos({"principal": "400 INVALID_ARGUMENT"})
    monkeypatch.setattr(llm, "cliente_gemini", type("C", (), {"models": modelos})())
    monkeypatch.setattr(llm, "LLM_MODEL", "principal")
    from app.logic.interprete import Interpretacion

    assert llm.generar_json("x", Interpretacion, "s") is None and modelos.probados == ["principal"]
