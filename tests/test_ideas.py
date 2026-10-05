"""Ideas sueltas y que Merche no fuerce un plan semanal cuando el usuario no lo pide."""
import datetime

import pytest
from fastapi.testclient import TestClient

from app.data.catalogo import get_receta
from app.logic import sesiones, texto
from app.logic.ideas import puntuacion_ligera
from app.logic.interprete import interpretar
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def hoy_es_lunes(monkeypatch):
    monkeypatch.setattr(texto, "FECHA_HOY", datetime.date(2026, 10, 5))


def chat(mensaje, sid="i"):
    r = client.post("/chat", json={"mensaje": mensaje, "session_id": sid})
    assert r.status_code == 200, r.text
    return r.json()


# Las frases de ejemplo de la pantalla de inicio de la interfaz
@pytest.mark.parametrize(
    "mensaje, accion, extra",
    [
        ("Hola Merche, ¿qué puedo cenar esta noche con pasta?", "sugerir", {"dia": "lunes", "momento": "cena", "ingredientes": ["pasta"]}),
        ("El martes no me apetece cocinar, ¿qué me recomiendas?", "sugerir", {"dia": "martes", "sin_cocinar": ["martes"]}),
        ("Quiero preparar algo especial para el domingo, ¿me das ideas?", "sugerir", {"dia": "domingo", "estilo": "especial"}),
        ("Tengo pollo y arroz en la nevera, ¿qué receta me sugieres?", "sugerir", {"ingredientes": ["pollo", "arroz"]}),
        ("Quiero comer más ligero esta semana, ¿me propones un menú?", "plan", {"estilo": "ligero"}),
        ("Somos 4 en casa y tenemos 90 € para la semana, ¿me ayudas con las comidas?", "plan", {"comensales": 4}),
    ],
)
def test_frases_de_ejemplo_de_la_interfaz(mensaje, accion, extra):
    i = interpretar(mensaje)
    assert i.accion == accion
    for campo, valor in extra.items():
        assert getattr(i, campo) == valor, campo


def test_ideas_con_ingredientes_no_crean_plan():
    r = chat("Tengo pollo y arroz en la nevera, ¿qué receta me sugieres?")
    assert "plan" not in r and r["mensaje"].startswith("Te propongo:")
    assert r["mensaje_conclusion"] == "¿Te apetece alguna?"
    assert sesiones.buscar("i").plan is None
    primera = r["mensaje"].split(": ", 1)[1].split(",")[0].split(" o ")[0].rstrip(".")
    assert "pollo" in primera.lower() or "arroz" in primera.lower()  # la mejor usa lo que tiene


def test_ideas_sin_cocinar_son_platos_listos():
    r = chat("El martes no me apetece cocinar, ¿qué me recomiendas?")
    assert r["mensaje"].startswith("Te propongo para el martes:")
    assert all(s.endswith(" el martes") for s in r["sugerencias"])


def test_cena_de_esta_noche_y_el_chip_la_pone_solo_hoy():
    r = chat("Hola Merche, ¿qué puedo cenar esta noche con pasta?")
    assert r["mensaje"].startswith("Te propongo para esta noche:")
    chip = r["sugerencias"][0]
    assert chip.endswith(" esta noche")
    r = chat(chip)  # elige una idea: falta saber cuántos son, pero el día ya lo sabe
    assert "plan" not in r and "¿Para cuántas personas es?" in r["mensaje"]
    r = chat("somos 2")
    assert list(r["plan"]["dias"]) == ["lunes"]  # solo hoy: no un plan de lunes a viernes
    assert r["plan"]["dias"]["lunes"][0]["momento"] == "cena"


def test_un_plato_suelto_no_se_convierte_en_plan_semanal():
    chat("quiero pollo al curry", "suelto")
    r = chat("somos 2", "suelto")
    assert list(r["plan"]["dias"]) == ["lunes"]  # antes: lunes a viernes


def test_algo_especial_prefiere_platos_mas_elaborados():
    r = chat("Quiero preparar algo especial para el domingo, ¿me das ideas?")
    assert r["mensaje"].startswith("Te propongo para el domingo:")


def test_menu_ligero_semanal_prioriza_platos_ligeros():
    chat("Quiero comer más ligero esta semana, ¿me propones un menú?", "lig")
    assert sesiones.buscar("lig").prefiere_ligero
    plan = chat("somos 2", "lig")["plan"]
    recetas = [get_receta(r["id"]) for rs in plan["dias"].values() for r in rs]
    assert sum(puntuacion_ligera(r) for r in recetas) / len(recetas) > 0


def test_ideas_respetan_la_dieta():
    chat("soy vegetariano", "veg")
    r = chat("¿qué puedo cenar con pollo?", "veg")
    assert "No tengo recetas con pollo" in r["mensaje"]


def test_pregunta_por_el_menu_con_plan_sigue_siendo_consulta():
    plan = chat("somos 2", "con")["plan"]
    r = chat("¿qué como el martes?", "con")
    assert r["mensaje"] == f"El martes: {plan['dias']['martes'][0]['nombre']}."


def test_gemini_pedir_plato_sin_plato_se_trata_como_datos(monkeypatch):
    from app.logic import llm
    from app.logic.interprete import Interpretacion

    chat("Quiero arroz con pollo y verduras", "gx")  # plan B: pedir_plato pendiente de personas
    monkeypatch.setattr(llm, "generar_json", lambda *a, **k: Interpretacion(accion="pedir_plato", comensales=1))
    r = chat("solo para mí", "gx")
    assert "None" not in r["mensaje"]
    assert r["plan"]["dias"]["lunes"][0]["nombre"] == "Arroz con pollo y verduras"
    assert r["plan"]["dias"]["lunes"][0]["raciones"] == 1
