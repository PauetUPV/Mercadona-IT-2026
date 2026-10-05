import pytest
from fastapi.testclient import TestClient

from app.logic import historial, sesiones
from app.logic.interprete import interpretar
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpiar():
    historial.reset()
    sesiones.reset()


def chat(mensaje, session_id=None, **extra):
    r = client.post("/chat", json={"mensaje": mensaje, "session_id": session_id, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def test_interpretar_datos():
    i = interpretar("Somos 4, tenemos 60 euros y el martes no cocino")
    assert i.comensales == 4 and i.presupuesto == 60
    assert i.sin_cocinar == ["martes"] and i.dias is None


def test_interpretar_rangos_y_numeros_en_texto():
    i = interpretar("para dos personas de lunes a miércoles, 35,5 €")
    assert i.comensales == 2 and i.presupuesto == 35.5
    assert i.dias == ["lunes", "martes", "miércoles"]


def test_interpretar_fin_de_semana():
    assert interpretar("plan para el fin de semana").dias == ["sábado", "domingo"]


def test_chat_pide_comensales():
    r = chat("hola, quiero un plan de comidas")
    assert r["plan"] is None or r["plan"]["comensales"] is None
    r = chat("el martes no cocino", r["session_id"])
    assert r["plan"] is None and "cuántas personas" in r["mensaje"]


def test_chat_plan_completo_y_conversacion():
    r = chat("Somos 4, tenemos 60 euros y el martes no cocino")
    sid = r["session_id"]
    plan = r["plan"]
    assert list(plan["dias"]) == ["lunes", "martes", "miércoles", "jueves", "viernes"]
    assert plan["dias"]["martes"]["tipo"] == "listo_para_comer"
    assert plan["comensales"] == 4 and plan["extras"]

    # cambiar un plato
    anterior = plan["dias"]["lunes"]["id"]
    r2 = chat("cambia el lunes", sid)
    assert r2["plan"]["id"] == plan["id"]
    assert r2["plan"]["dias"]["lunes"]["id"] != anterior

    # cambiar el presupuesto regenera el plan manteniendo lo anterior
    r3 = chat("mejor 25 euros", sid)
    assert r3["plan"]["presupuesto"] == 25 and r3["plan"]["comensales"] == 4
    assert r3["plan"]["dias"]["martes"]["tipo"] == "listo_para_comer"


def test_chat_campos_explicitos_mandan():
    r = chat("hazme el plan", comensales=3, presupuesto=50, dias=["lunes", "martes"])
    assert list(r["plan"]["dias"]) == ["lunes", "martes"] and r["plan"]["comensales"] == 3


def test_chat_sustituir_sin_plan_o_sin_dia():
    assert "plan" in chat("cambia el martes")["mensaje"]
    sid = chat("somos 2")["session_id"]
    assert "Qué día" in chat("cambia otro plato", sid)["mensaje"]


def test_chat_no_entiende():
    assert "No te he entendido" in chat("blablabla")["mensaje"]


def test_historial_de_sesion():
    sid = chat("somos 2")["session_id"]
    h = client.get(f"/chat/{sid}").json()
    assert [m["rol"] for m in h["historial"]] == ["usuario", "asistente"]
    assert h["plan"] is not None
    assert client.get("/chat/nope").status_code == 404


def test_session_id_propio_del_cliente():
    r = chat("somos 2", session_id="mi-sesion")
    assert r["session_id"] == "mi-sesion"


def test_chat_mensaje_vacio():
    assert client.post("/chat", json={"mensaje": ""}).status_code == 422
