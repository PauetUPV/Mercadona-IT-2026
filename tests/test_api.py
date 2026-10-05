import pytest
from fastapi.testclient import TestClient

from app.logic import historial
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpiar_historial():
    historial.reset()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_productos_y_404():
    r = client.get("/productos", params={"q": "pollo", "limite": 5})
    assert r.status_code == 200 and 0 < len(r.json()) <= 5
    assert client.get("/productos/10000").status_code == 200
    assert client.get("/productos/nope").status_code == 404


def test_validacion_productos():
    assert client.get("/productos", params={"limite": 1000}).status_code == 422


def test_catalogo_y_categorias():
    assert len(client.get("/catalogo").json()) >= 15
    assert client.get("/categorias").status_code == 200


def test_plan_sustituir_dashboard():
    body = {"comensales": 2, "presupuesto": 100, "dias": ["lunes", "martes"]}
    plan = client.post("/plan", json=body).json()
    assert plan["id"] and plan["dentro_presupuesto"] is True

    nuevo = client.post("/sustituir", json={"plan": plan, "dia": "lunes", "comensales": 2}).json()
    assert nuevo["id"] == plan["id"]

    d = client.get("/dashboard").json()
    assert d["planes_generados"] == 1 and d["sustituciones"] == 1
    assert d["ahorro_total_vs_presupuesto"] > 0


def test_errores():
    assert client.post("/plan", json={"comensales": 0, "dias": ["lunes"]}).status_code == 422
    assert client.post("/plan", json={"comensales": 2, "dias": []}).status_code == 422
    assert client.post("/plan", json={"comensales": 2, "dias": ["a", "a"]}).status_code == 422
    plan = client.post("/plan", json={"comensales": 2, "dias": ["lunes"]}).json()
    r = client.post("/sustituir", json={"plan": plan, "dia": "viernes", "comensales": 2})
    assert r.status_code == 404
