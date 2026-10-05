from fastapi.testclient import TestClient

from app.logic import llm, mas, opiniones
from main import app

client = TestClient(app)


def informe():
    r = client.get("/informe")
    assert r.status_code == 200, r.text
    return r.json()


def tema(inf, sujeto, categoria):
    return next(t for t in inf["temas"] if t["sujeto"] == sujeto and t["categoria"] == categoria)


def test_informe_vacio():
    inf = informe()
    assert inf["opiniones"] == 0 and inf["temas"] == [] and "no hay opiniones" in inf["resumen"]


def test_queja_por_chat_llega_al_informe():
    r = client.post("/chat", json={"mensaje": "Tengo una queja: las latas de atún vienen con demasiado aceite"}).json()
    assert "Mercadona" in r["mensaje"] and "plan" not in r
    inf = informe()
    t = tema(inf, "Atun", "calidad")
    assert t["tipo"] == "queja" and t["menciones"] == 1 and not t["alerta"] and t["producto_id"]
    assert inf["opiniones"] == 1 and inf["clientes"] == 1


def test_pedir_plan_no_es_una_opinion():
    r = client.post("/chat", json={"mensaje": "Somos 2, 60 euros, es demasiado para nosotros"}).json()
    assert r["plan"] and opiniones.todas() == []


def test_opinion_endpoint():
    sid = client.post("/chat", json={"mensaje": "somos 2"}).json()["session_id"]
    ok = client.post("/opinion", json={"session_id": sid, "texto": "La leche estaba caducada", "tienda": "Valencia-Ruzafa"})
    assert ok.status_code == 200 and ok.json()["mensaje"]
    assert client.post("/opinion", json={"session_id": "x", "texto": "hola"}).status_code == 404
    assert client.post("/opinion", json={"session_id": sid, "texto": ""}).status_code == 422
    t = tema(informe(), "Leche", "seguridad")
    assert t["alerta"] and t["tiendas"] == {"Valencia-Ruzafa": 1}  # seguridad: avisa con un solo caso


def test_quejas_repetidas_son_alerta_y_se_agrupan_por_tienda_y_fecha():
    for k, (tienda, fecha) in enumerate([("A", "2026-10-01T10:00:00"), ("A", "2026-10-03T10:00:00"), ("B", "2026-10-02T10:00:00")]):
        opiniones.registrar(f"s{k}", texto="El atún viene con demasiado aceite", tienda=tienda, fecha=fecha)
    opiniones.registrar("s9", texto="Me encanta el pan de pueblo")
    inf = informe()
    t = inf["temas"][0]  # las alertas van primero
    assert (t["sujeto"], t["menciones"], t["clientes"], t["alerta"]) == ("Atun", 3, 3, True)
    assert t["tiendas"] == {"A": 2, "B": 1} and (t["desde"], t["hasta"]) == ("2026-10-01", "2026-10-03")
    assert tema(inf, "Pan", "otro")["tipo"] == "elogio"
    assert "Atun" in inf["resumen"]


def test_valoraciones_cuentan_una_vez_y_el_motivo_se_analiza():
    r = client.post("/chat", json={"mensaje": "somos 2"}).json()
    sid, receta = r["session_id"], r["plan"]["dias"]["lunes"][0]
    cuerpo = {"session_id": sid, "sujeto": {"tipo": "receta", "id": receta["id"]}, "valor": "negativo"}
    client.post("/feedback", json=cuerpo)  # primero sin motivo...
    client.post("/feedback", json={**cuerpo, "motivo": "Estaba soso"})  # ...y luego con él: es la misma valoración
    inf = informe()
    assert inf["valoraciones"] == [{"tipo": "receta", "id": receta["id"], "nombre": receta["nombre"], "positivos": 0, "negativos": 1}]
    t = tema(inf, receta["nombre"], "sabor")
    assert t["sujeto_tipo"] == "receta" and t["menciones"] == 1


def test_con_gemini_simulado_analiza_una_vez_y_redacta(monkeypatch):
    a = opiniones.registrar("s1", texto="las latas de atun traen muchisimo aceite")
    b = opiniones.registrar("s2", texto="ojalá hubiera hummus sin ajo")
    llamadas = []

    def falso(prompt, esquema, sistema, temperatura=0.2):
        llamadas.append(esquema.__name__)
        if esquema is mas._Lote:
            return mas._Lote(
                analisis=[
                    mas.Analisis(id=a.id, tipo="queja", categoria="calidad", producto="atún", resumen="El atún en lata lleva demasiado aceite."),
                    mas.Analisis(id=b.id, tipo="sugerencia", categoria="otro", producto="hummus", resumen="Pide hummus sin ajo."),
                    mas.Analisis(id="inventado", tipo="queja", categoria="otro", resumen="No existe."),
                ]
            )
        return mas._Redaccion(resumen="Resumen del redactor.", acciones=[{"tema": 0, "accion": "Hablar con el proveedor."}, {"tema": 99, "accion": "x"}])

    monkeypatch.setattr(llm, "generar_json", falso)
    monkeypatch.setattr(llm, "disponible", lambda: True)
    inf = informe()
    assert inf["resumen"] == "Resumen del redactor." and len(inf["temas"]) == 2  # el id inventado se ignora
    assert inf["temas"][0]["accion"] == "Hablar con el proveedor."
    assert tema(inf, "Atún", "calidad")["ejemplos"] == ["El atún en lata lleva demasiado aceite."]
    informe()
    assert llamadas == ["_Lote", "_Redaccion", "_Redaccion"]  # lo ya analizado no se vuelve a preguntar
