"""Cambiar platos: por día, varios días, por nombre, por ingrediente, todo, y "por X" como criterio solo para ese hueco."""
import datetime

import pytest
from fastapi.testclient import TestClient

from app.data.catalogo import get_receta
from app.logic import llm, sesiones, texto
from app.logic.interprete import Interpretacion, interpretar
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def hoy_es_lunes(monkeypatch):
    monkeypatch.setattr(texto, "FECHA_HOY", datetime.date(2026, 10, 5))


def chat(mensaje, sid="cb"):
    r = client.post("/chat", json={"mensaje": mensaje, "session_id": sid})
    assert r.status_code == 200, r.text
    return r.json()


def nombres(plan):
    return {d: rs[0]["nombre"] for d, rs in plan["dias"].items()}


@pytest.mark.parametrize(
    "mensaje, esperado",
    [
        ("cambia el lunes por algo de pescado", {"dias_cambio": ["lunes"], "por": "pescado"}),
        ("cámbiame el martes por lentejas", {"dias_cambio": ["martes"], "por": "lentejas"}),
        ("cambia las hamburguesas", {"objetivo": "hamburguesas", "dias_cambio": []}),
        ("cambia la pasta por arroz", {"objetivo": "pasta", "por": "arroz"}),
        ("cambia el lunes y el martes", {"dias_cambio": ["lunes", "martes"]}),
        ("cambia todo", {"todo": True}),
        ("cambia el jueves por algo más ligero", {"dias_cambio": ["jueves"], "estilo": "ligero"}),
        ("¿puedes cambiar el plato del viernes por algo vegetariano?", {"dias_cambio": ["viernes"], "por": "vegetariano", "excluir": []}),
        ("pon otra cosa el miércoles", {"dias_cambio": ["miércoles"], "por": None}),
    ],
)
def test_interpretacion_de_cambios(mensaje, esperado):
    i = interpretar(mensaje)
    assert i.accion == "cambiar_plato"
    for campo, valor in esperado.items():
        assert getattr(i, campo) == valor, (campo, getattr(i, campo))


def test_cambiar_por_pescado():
    antes = nombres(chat("somos 2, sin presupuesto")["plan"])
    r = chat("cambia el lunes por algo de pescado")
    nuevo = r["plan"]["dias"]["lunes"][0]
    assert "pescado" in nuevo["etiquetas"] and nuevo["nombre"] != antes["lunes"]
    assert {d: n for d, n in nombres(r["plan"]).items() if d != "lunes"} == {d: n for d, n in antes.items() if d != "lunes"}


def test_cambiar_por_un_plato_concreto():
    chat("somos 2")
    r = chat("cámbiame el martes por lentejas")
    assert r["plan"]["dias"]["martes"][0]["nombre"].startswith("Lentejas")


def test_por_algo_vegetariano_no_cambia_la_dieta_ni_borra_dias():
    plan = chat("somos 2")["plan"]
    r = chat("¿puedes cambiar el plato del viernes por algo vegetariano?")
    viernes = r["plan"]["dias"]["viernes"][0]
    assert not ({"carne", "pescado"} & set(viernes["etiquetas"]))
    assert list(r["plan"]["dias"]) == list(plan["dias"])  # antes: se quedaba solo el viernes
    assert sesiones.buscar("cb").excluir == []  # y el usuario no pasa a ser vegetariano


def test_cambiar_varios_dias_y_todo():
    antes = nombres(chat("somos 2")["plan"])
    r = chat("cambia el lunes y el martes")
    despues = nombres(r["plan"])
    assert despues["lunes"] != antes["lunes"] and despues["martes"] != antes["martes"]
    assert despues["miércoles"] == antes["miércoles"]
    assert r["mensaje"].startswith("Hecho. Ahora tienes el lunes,")
    todo = nombres(chat("cambia todo")["plan"])
    assert all(todo[d] != despues[d] for d in todo)


def test_cambiar_un_plato_por_su_nombre():
    plan = chat("somos 2")["plan"]
    dia, nombre = next(iter(nombres(plan).items()))
    r = chat(f"cambia {nombre.lower()}")
    assert r["plan"]["dias"][dia][0]["nombre"] != nombre
    r = chat("cambia el sushi")
    assert "plan" not in r and "No tienes «sushi» en el plan" in r["mensaje"]


def test_cambiar_la_pasta_por_arroz():
    chat("somos 2", "pasta")
    sesion = sesiones.buscar("pasta")
    con_pasta = [d for d, rs in sesion.plan.dias.items() if any(w in rs[0].nombre.lower() for w in ("espagueti", "macarr", "tallarin", "pasta"))]
    if not con_pasta:
        chat("quiero espaguetis carbonara el lunes", "pasta")
        con_pasta = ["lunes"]
    r = chat("cambia la pasta por arroz", "pasta")
    for d in con_pasta:
        assert "arroz" in r["plan"]["dias"][d][0]["nombre"].lower() or any(
            "arroz" in i["producto"]["nombre"].lower() for i in r["plan"]["dias"][d][0]["ingredientes"]
        )


def test_sin_dia_pregunta_y_dia_fuera_del_plan():
    chat("somos 2, de lunes a martes")
    assert "¿Qué día quieres cambiar?" in chat("cambia otro plato")["mensaje"]
    assert "no está en tu plan" in chat("cambia el domingo")["mensaje"]


def test_sin_alternativa_lo_dice_claro():
    chat("somos 2")
    r = chat("cambia el lunes por sushi")
    assert "plan" not in r and "No tengo otro plato con «sushi» para el lunes" in r["mensaje"]


def test_con_gemini_el_texto_del_cambio_lo_pone_el_codigo(monkeypatch):
    chat("somos 2")
    monkeypatch.setattr(llm, "generar_json", lambda *a, **k: Interpretacion(
        accion="cambiar_plato", dias_cambio=["viernes"], por="algo vegetariano",
        respuesta="¡Hecho! Te pongo una opción vegetariana riquísima."))
    r = chat("oye el viernes ponme algo vegetariano en vez de lo que hay")
    viernes = r["plan"]["dias"]["viernes"][0]
    assert r["mensaje"] == f"He cambiado el plato del viernes: ahora es {viernes['nombre']}."
    assert not ({"carne", "pescado"} & set(get_receta(viernes["id"]).etiquetas))


def test_por_pescado_prefiere_un_plato_de_pescado():
    chat("somos 2", "pez")
    r = chat("cambia el lunes por algo de pescado", "pez")
    nombre = r["plan"]["dias"]["lunes"][0]["nombre"].lower()
    assert any(p in nombre for p in ("merluza", "bacalao", "salmón", "sardina", "atún")) and not nombre.startswith("pasta")
