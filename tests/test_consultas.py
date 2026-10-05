"""Preguntas sobre la sesión: se contestan con los datos guardados y nunca cambian el plan."""
import datetime

import pytest
from fastapi.testclient import TestClient

from app.logic import llm, sesiones, texto
from app.logic.carrito import total_plan
from app.logic.interprete import Interpretacion, interpretar
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def hoy_es_lunes(monkeypatch):
    monkeypatch.setattr(texto, "FECHA_HOY", datetime.date(2026, 10, 5))


def chat(mensaje, session_id="c"):
    r = client.post("/chat", json={"mensaje": mensaje, "session_id": session_id})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize(
    "mensaje, tema, dia",
    [
        ("¿qué como el martes?", "menu", "martes"),
        ("¿cuál es el menú de la semana?", "menu", None),
        ("¿qué hay de cena hoy?", "menu", "lunes"),
        ("¿cómo se hace la tortilla de patata?", "receta", None),
        ("¿qué lleva el plato del lunes?", "ingredientes", "lunes"),
        ("¿y qué lleva?", "ingredientes", None),
        ("¿cuánto me va a costar?", "coste", None),
        ("¿qué tengo que tener en casa?", "en_casa", None),
        ("¿para cuántos era?", "preferencias", None),
        ("¿esto es sano?", "otro", None),
    ],
)
def test_preguntas_se_clasifican_como_consulta(mensaje, tema, dia):
    i = interpretar(mensaje)
    assert (i.accion, i.tema, i.dia) == ("consultar", tema, dia)


@pytest.mark.parametrize(
    "mensaje, accion",
    [("¿me haces un plan para 3 personas?", "plan"), ("¿puedes añadir leche?", "anadir_extra"), ("¿puedes cambiar el martes?", "cambiar_plato")],
)
def test_peticiones_con_forma_de_pregunta_no_son_consultas(mensaje, accion):
    assert interpretar(mensaje).accion == accion


def test_una_pregunta_sobre_un_dia_no_borra_el_plan():
    plan = chat("somos 2")["plan"]
    r = chat("¿qué como el martes?")
    assert "plan" not in r  # antes: rehacía el plan solo con el martes
    assert r["mensaje"] == f"El martes: {plan['dias']['martes'][0]['nombre']}."
    assert list(sesiones.buscar("c").plan.dias) == list(plan["dias"])


def test_receta_e_ingredientes_con_memoria_del_ultimo_plato():
    plan = chat("somos 2")["plan"]
    martes = plan["dias"]["martes"][0]
    chat("¿qué como el martes?")
    r = chat("¿cómo se hace?")  # sin decir cuál: el del martes, del que acabamos de hablar
    assert martes["nombre"] in r["mensaje"]
    assert (martes["instrucciones"] or "listo para comer") in r["mensaje"]
    r = chat("¿y qué lleva?")
    for ing in martes["ingredientes"]:
        assert ing["producto"]["nombre"] in r["mensaje"]


def test_receta_que_no_esta_en_el_plan():
    chat("somos 2")
    r = chat("¿cómo se hace la tortilla de patata?")
    assert r["mensaje"].startswith("Tortilla de patata:") and "huevos batidos" in r["mensaje"]


def test_coste_coincide_con_la_regla_de_la_interfaz():
    chat("somos 2 y 100 euros")
    r = chat("¿cuánto me va a costar?")
    total = f"{total_plan(sesiones.buscar('c').plan):.2f}".replace(".", ",")
    assert total in r["mensaje"] and "Entra en tu presupuesto" in r["mensaje"]


def test_preferencias_y_en_casa():
    chat("somos 3, sin gluten")
    r = chat("¿para cuántos era?")
    assert "sois 3" in r["mensaje"] and "evitas gluten" in r["mensaje"]
    assert "sal" in chat("¿qué tengo que tener en casa?")["mensaje"]


def test_preguntas_sin_plan():
    r = chat("¿qué como el martes?", "vacia")  # sin plan: en vez de "no tienes plan", ideas para ese día
    assert r["mensaje"].startswith("Te propongo para el martes:") and "plan" not in r
    assert "¿De qué plato?" in chat("¿y qué lleva?", "vacia2")["mensaje"]


def test_los_chips_de_consulta_se_entienden():
    chat("somos 2")
    r = chat("¿qué como el miércoles?")
    assert r["sugerencias"][0] == "¿Cómo se hace el del miércoles?"
    r = chat(r["sugerencias"][0])
    assert "plan" not in r and sesiones.buscar("c").plan.dias["miércoles"][0].nombre in r["mensaje"]


def test_con_gemini_lo_concreto_lo_contesta_el_codigo(monkeypatch):
    chat("somos 2")
    monkeypatch.setattr(
        llm, "generar_json",
        lambda *a, **k: Interpretacion(accion="consultar", tema="menu", dia="martes", respuesta="El martes toca sushi"),
    )
    r = chat("oye, ¿y el martes qué toca?")
    assert "sushi" not in r["mensaje"] and r["mensaje"].startswith("El martes:")  # no se fía del texto del LLM


def test_con_gemini_lo_abierto_lo_contesta_gemini_con_el_plan_en_contexto(monkeypatch):
    chat("somos 2")
    prompts = []

    def falso(prompt, esquema, sistema, temperatura=0.2):
        prompts.append(prompt)
        return Interpretacion(accion="consultar", tema="otro", respuesta="Sí, es un menú bastante equilibrado.")

    monkeypatch.setattr(llm, "generar_json", falso)
    r = chat("¿esto es sano?")
    assert r["mensaje"] == "Sí, es un menú bastante equilibrado." and "plan" not in r
    assert '"ingredientes": [' in prompts[0] and '"instrucciones":' in prompts[0]  # Gemini ve el detalle del plan
