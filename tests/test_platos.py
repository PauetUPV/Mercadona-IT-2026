"""Pedir un plato concreto, "para mí", "hoy/mañana" y la memoria entre mensajes."""
import datetime

import pytest
from fastapi.testclient import TestClient

from app.data.catalogo import buscar_receta
from app.logic import llm, sesiones, texto
from app.logic.interprete import Interpretacion, interpretar
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def hoy_es_lunes(monkeypatch):
    monkeypatch.setattr(texto, "FECHA_HOY", datetime.date(2026, 10, 5))  # lunes


def chat(mensaje, session_id="s"):
    r = client.post("/chat", json={"mensaje": mensaje, "session_id": session_id})
    assert r.status_code == 200, r.text
    return r.json()


def nombres(plan):
    return {d: [r["nombre"] for r in rs] for d, rs in plan["dias"].items()}


# --- Intérprete (plan B) ----------------------------------------------------------------


@pytest.mark.parametrize(
    "mensaje, comensales",
    [("es solo para mí", 1), ("solo yo", 1), ("una persona", 1), ("para mi familia somos 4", 4), ("mi novia y yo", 2)],
)
def test_comensales_en_lenguaje_natural(mensaje, comensales):
    assert interpretar(mensaje).comensales == comensales


def test_hoy_manana_y_esta_noche():
    assert interpretar("para hoy").dias == ["lunes"]
    assert interpretar("para mañana y pasado mañana").dias == ["martes", "miércoles"]
    assert interpretar("por la mañana somos 2").dias is None  # "por la mañana" no es un día
    i = interpretar("quiero cenar pizza esta noche")
    assert (i.accion, i.dia, i.momento) == ("pedir_plato", "lunes", "cena")


def test_pedir_plato_y_no_confundir_con_otras_cosas():
    i = interpretar("me apetece lentejas el martes")
    assert (i.accion, i.plato, i.dia) == ("pedir_plato", "lentejas", "martes")
    assert interpretar("Quiero lasaña de verduras").plato == "lasaña de verduras"  # conserva tildes y eñes
    assert interpretar("añade huevos").accion == "anadir_extra"  # producto, no plato
    assert interpretar("no quiero carne").accion == "plan"  # dieta, no plato
    assert interpretar("quiero comida y cena").accion == "plan"
    assert interpretar("quiero un plan para 3 días").accion == "plan"


def test_buscar_receta():
    receta, parecido, _ = buscar_receta("pollo al curry")
    assert receta.nombre.startswith("Pollo al curry") and parecido == 1
    receta, parecido, _ = buscar_receta("lasaña de verduras")
    assert receta.nombre.startswith("Lasaña") and parecido == 0.5  # prioriza el plato, no el acompañamiento
    assert buscar_receta("sushi")[0] is None


# --- Flujo completo ---------------------------------------------------------------------


def test_plato_pendiente_hasta_saber_personas_y_dia():
    r = chat("quiero pollo al curry")
    assert "plan" not in r and "Pollo al curry" in r["mensaje"] and "Solo para mí, hoy" in r["sugerencias"]
    r = chat("es solo para mí y para hoy")
    assert nombres(r["plan"]) == {"lunes": ["Pollo al curry con arroz basmati"]}
    assert r["plan"]["dias"]["lunes"][0]["raciones"] == 1


def test_el_chip_de_plato_pendiente_funciona():
    r = chat("quiero pollo al curry", "chip")
    r = chat(r["sugerencias"][0], "chip")  # "Solo para mí, hoy"
    assert nombres(r["plan"]) == {"lunes": ["Pollo al curry con arroz basmati"]}


def test_pedir_plato_con_plan_existente_y_que_se_mantenga():
    plan = chat("somos 2 y 60 euros")["plan"]
    assert len(set(sum(nombres(plan).values(), []))) == 5
    r = chat("quiero lentejas el miércoles")
    assert r["plan"]["dias"]["miércoles"][0]["nombre"].startswith("Lentejas")
    assert r["plan"]["dias"]["lunes"] == plan["dias"]["lunes"]  # el resto no cambia
    r = chat("mejor 55 euros")  # al rehacer el plan, el plato pedido se queda
    assert r["plan"]["dias"]["miércoles"][0]["nombre"].startswith("Lentejas")
    r = chat("cambia el miércoles")  # si luego lo cambia, deja de estar fijado
    assert not r["plan"]["dias"]["miércoles"][0]["nombre"].startswith("Lentejas")
    assert sesiones.buscar("s").fijos == []


def test_plato_en_un_dia_que_no_estaba_lo_anade():
    chat("somos 2, de lunes a miércoles")
    r = chat("quiero pizza el sábado")
    assert list(r["plan"]["dias"]) == ["lunes", "martes", "miércoles", "sábado"]


def test_plato_inexistente_o_parecido():
    chat("somos 2")
    r = chat("quiero sushi")
    assert "plan" not in r and "No tengo «sushi»" in r["mensaje"]
    r = chat("quiero lasaña de verduras")
    assert "No tengo «lasaña de verduras» tal cual" in r["mensaje"]
    assert r["plan"]["dias"]["lunes"][0]["nombre"].startswith("Lasaña")


def test_plato_que_choca_con_la_dieta():
    chat("somos 2 y soy vegetariano")
    r = chat("quiero pollo al curry")
    assert "plan" not in r and "lleva carne" in r["mensaje"]


def test_plato_vetado_por_feedback_se_puede_pedir():
    plan = chat("somos 2")["plan"]
    receta = plan["dias"]["lunes"][0]
    client.post("/lista", json={"session_id": "s", "lineas": []})
    client.post("/feedback", json={"session_id": "s", "sujeto": {"tipo": "receta", "id": receta["id"]}, "valor": "negativo", "motivo": "x"})
    assert receta["id"] in sesiones.buscar("s").rechazadas
    r = chat(f"quiero {receta['nombre'].lower()} el martes")
    assert r["plan"]["dias"]["martes"][0]["id"] == receta["id"]
    assert receta["id"] not in sesiones.buscar("s").rechazadas


def test_planes_variados_y_distintos_por_sesion():
    a = chat("somos 2", "uno")["plan"]
    b = chat("somos 2", "otro")["plan"]
    assert nombres(a) != nombres(b)
    assert len({n.split()[0] for n in sum(nombres(a).values(), [])}) >= 3  # no cinco platos de pollo seguidos


def test_con_gemini_pedir_plato(monkeypatch):
    llamadas = []

    def falso(prompt, esquema, sistema, temperatura=0.2):
        llamadas.append(prompt)
        return Interpretacion(accion="pedir_plato", plato="pollo al curry", comensales=1, dia="lunes")

    monkeypatch.setattr(llm, "generar_json", falso)
    r = chat("me pido un currito de pollo para mí solo hoy", "gem")
    assert nombres(r["plan"]) == {"lunes": ["Pollo al curry con arroz basmati"]}
    assert '"hoy": "lunes"' in llamadas[0]  # Gemini recibe qué día es hoy


def test_conversacion_completa_sin_verbo_y_con_relleno():
    r = chat("Me apetece mucho un pollo al curry", "conv")
    assert "tal cual" not in r["mensaje"]  # "mucho un" es relleno, no parte del plato
    chat("es solo para mí y para hoy", "conv")
    r = chat("y mañana algo de lentejas", "conv")  # sin "quiero": se entiende como plato
    assert nombres(r["plan"])["lunes"] == ["Pollo al curry con arroz basmati"]  # no se pierde lo anterior
    assert nombres(r["plan"])["martes"][0].startswith("Lentejas")
    assert r["plan"]["dias"]["martes"][0]["raciones"] == 1
