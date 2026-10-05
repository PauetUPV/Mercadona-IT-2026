from fastapi.testclient import TestClient

from app.logic import llm, sesiones
from app.logic.carrito import total_plan
from app.logic.interprete import Interpretacion
from main import app

client = TestClient(app)


def chat(mensaje, session_id=None, plan=None):
    body = {"mensaje": mensaje, "session_id": session_id}
    if plan is not None:
        body["plan"] = plan
    r = client.post("/chat", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_pregunta_comensales_y_acumula():
    r = chat("quiero un plan de comidas")
    assert "plan" not in r and "cuántas personas" in r["mensaje"]
    r = chat("el martes no cocino", r["session_id"])
    assert "plan" not in r  # sigue sin comensales
    r = chat("somos 2", r["session_id"])
    plan = r["plan"]
    assert list(plan["dias"]) == ["lunes", "martes", "miércoles", "jueves", "viernes"]
    assert plan["dias"]["martes"][0]["tipo"] == "listo_para_comer"  # lo recordó de antes


def test_plan_completo_forma_del_contrato():
    r = chat("Somos 4, tenemos 60 euros y el martes no cocino")
    assert r["mensaje_conclusion"]
    plan = r["plan"]
    for campo in ("carrito", "total", "comensales", "presupuesto", "dentro_presupuesto"):
        assert campo not in plan
    receta = plan["dias"]["lunes"][0]
    assert receta["raciones"] == 4 and receta["momento"] == "comida" and receta["instrucciones"]
    ing = receta["ingredientes"][0]
    assert ing["unidades"] > 0 and ing["producto"]["precio"] > 0 and ing["producto"]["id"]
    assert plan["extras"] == [] and plan["en_casa"]


def test_cambiar_plato_solo_devuelve_plan_si_cambia():
    r = chat("somos 2")
    sid, antes = r["session_id"], r["plan"]
    r2 = chat("cambia el lunes", sid)
    assert r2["plan"]["id"] != antes["id"]
    assert r2["plan"]["dias"]["lunes"][0]["id"] != antes["dias"]["lunes"][0]["id"]
    assert r2["plan"]["dias"]["martes"] == antes["dias"]["martes"]
    assert "plan" not in chat("cambia el domingo", sid)  # no está en el plan: nada cambia
    assert "plan" not in chat("blablabla", sid)


def test_plan_editado_por_el_usuario_manda():
    r = chat("somos 2")
    sid, plan = r["session_id"], r["plan"]
    editado = {**plan, "dias": {d: rs for d, rs in plan["dias"].items() if d in ("lunes", "martes")}}
    r2 = chat("mejor 80 euros", sid, plan=editado)
    assert list(r2["plan"]["dias"]) == ["lunes", "martes"]  # respeta los días que dejó el usuario


def test_comida_y_cena():
    plan = chat("somos 2, comida y cena de lunes a martes")["plan"]
    assert [x["momento"] for x in plan["dias"]["lunes"]] == ["comida", "cena"]


def test_dieta_se_recuerda():
    sid = chat("somos 2 y soy vegetariano")["session_id"]
    plan = chat("de lunes a viernes", sid)["plan"]
    assert all("carne" not in x["etiquetas"] and "pescado" not in x["etiquetas"] for rs in plan["dias"].values() for x in rs)


def test_presupuesto_imposible_se_rechaza_y_no_cambia_nada():
    r = chat("somos 2 y 100 euros")
    sid, plan = r["session_id"], r["plan"]
    r2 = chat("mejor 3 euros", sid)
    assert "plan" not in r2 and "no puede ser" in r2["mensaje"]
    assert sesiones.buscar(sid).presupuesto == 100  # no se guarda un presupuesto imposible
    assert sesiones.buscar(sid).plan.id == plan["id"]


def test_tras_rechazar_el_presupuesto_recuerda_el_resto():
    r = chat("somos 3, soy celíaca y 5 euros")
    sid = r["session_id"]
    assert "plan" not in r and "no puede ser" in r["mensaje"]
    ses = sesiones.buscar(sid)
    assert (ses.comensales, ses.excluir, ses.presupuesto) == (3, ["gluten"], None)
    plan = chat("vale, 200 euros", sid)["plan"]  # basta con corregir el presupuesto
    assert plan["dias"]["lunes"][0]["raciones"] == 3


def test_peticiones_absurdas():
    assert "plan" not in chat("somos 50 personas")  # más de 12 comensales
    assert "plan" not in chat("somos 2 y 0 euros")


def test_extras():
    sid = chat("somos 2")["session_id"]
    r = chat("añade leche", sid)
    assert r["plan"]["extras"][0]["producto"]["nombre"].lower().startswith("leche")
    r = chat("añade zzzxxx", sid)
    assert "plan" not in r and "No he encontrado" in r["mensaje"]
    r = chat("quita la leche", sid)
    assert r["plan"]["extras"] == []


def test_extras_sin_plan():
    assert "plan" not in chat("añade leche")


def test_aviso_si_el_extra_pasa_del_presupuesto():
    sid = chat("somos 2 y 100 euros")["session_id"]
    ses = sesiones.buscar(sid)
    ses.presupuesto = total_plan(ses.plan)  # justo al límite
    sesiones.guardar(ses)
    assert "te pasas" in chat("añade leche", sid)["mensaje"]


def test_estado_sobrevive_a_reinicio():
    sid = chat("somos 3 y 70 euros")["session_id"]
    sesiones.reset()  # como un reinicio: la memoria se pierde, el disco no
    h = client.get(f"/chat/{sid}").json()
    assert h["plan"] is not None and len(h["historial"]) == 2
    assert "plan" in chat("cambia el lunes", sid)  # y sigue recordando comensales, presupuesto y plan


def test_historial_404():
    assert client.get("/chat/nope").status_code == 404


def test_session_id_propio_y_mensaje_vacio():
    assert chat("somos 2", session_id="mi-sesion")["session_id"] == "mi-sesion"
    assert client.post("/chat", json={"mensaje": ""}).status_code == 422


def test_lista_y_feedback():
    r = chat("somos 2")
    sid, plan = r["session_id"], r["plan"]
    pid = plan["dias"]["lunes"][0]["ingredientes"][0]["producto"]["id"]
    ok = client.post("/lista", json={"session_id": sid, "plan_id": plan["id"], "lineas": [{"producto_id": pid, "unidades": 2}]})
    assert ok.status_code == 200 and ok.json()["lista_id"].startswith("l_")
    assert sesiones.buscar(sid).listas[0]["lineas"][0]["unidades"] == 2
    assert client.post("/lista", json={"session_id": sid, "lineas": [{"producto_id": "nope", "unidades": 1}]}).status_code == 422
    assert client.post("/lista", json={"session_id": "x", "lineas": []}).status_code == 404

    receta_id = plan["dias"]["lunes"][0]["id"]
    fb = client.post("/feedback", json={"session_id": sid, "sujeto": {"tipo": "receta", "id": receta_id}, "valor": "negativo"})
    assert fb.status_code == 200 and fb.json()["sugerencias"]
    # una receta con feedback negativo no vuelve a salir
    plan2 = chat("de lunes a viernes", sid)["plan"]
    assert all(x["id"] != receta_id for rs in plan2["dias"].values() for x in rs)
    ko = client.post("/feedback", json={"session_id": "x", "sujeto": {"tipo": "receta", "id": "r1"}, "valor": "positivo"})
    assert ko.status_code == 404


def test_productos_y_health():
    r = client.get("/productos", params={"q": "pollo", "limite": 5})
    assert r.status_code == 200 and 0 < len(r.json()) <= 5
    assert client.get("/productos", params={"limite": 1000}).status_code == 422
    assert client.get("/health").json() == {"status": "ok"}


def test_endpoints_retirados():
    for ruta in ("/plan", "/sustituir", "/catalogo", "/dashboard"):
        assert client.post(ruta, json={}).status_code in (404, 405)


# --- Con Gemini (simulado) ---------------------------------------------------------------


def gemini_falso(monkeypatch, interpretacion, llamadas=None):
    def falso(prompt, esquema, sistema, temperatura=0.2):
        if llamadas is not None:
            llamadas.append(prompt)
        return interpretacion

    monkeypatch.setattr(llm, "generar_json", falso)


def test_una_sola_llamada_a_gemini_por_mensaje(monkeypatch):
    llamadas = []
    gemini_falso(
        monkeypatch,
        Interpretacion(
            accion="plan", comensales=2, presupuesto=50, excluir=["gluten", "inventado"],
            respuesta="Aquí tienes tu semana, con cariño.", conclusion="¿Qué tal?",
        ),
        llamadas,
    )
    r = chat("hola, necesitamos organizarnos la semana que somos pareja")
    assert len(llamadas) == 1
    assert r["mensaje"] == "Aquí tienes tu semana, con cariño." and r["mensaje_conclusion"] == "¿Qué tal?"
    assert all("gluten" not in x["etiquetas"] for rs in r["plan"]["dias"].values() for x in rs)
    assert sesiones.buscar(r["session_id"]).excluir == ["gluten"]  # la etiqueta inventada se descarta


def test_si_el_texto_de_gemini_cita_precios_se_descarta(monkeypatch):
    gemini_falso(monkeypatch, Interpretacion(accion="plan", comensales=2, respuesta="Te sale por 12,50 euros."))
    assert "euros" not in chat("somos 2")["mensaje"]


def test_si_la_accion_falla_el_texto_lo_pone_el_codigo(monkeypatch):
    gemini_falso(monkeypatch, Interpretacion(accion="plan", comensales=2, presupuesto=3, respuesta="¡Hecho, aquí tienes!"))
    r = chat("somos 2 y 3 euros")
    assert "plan" not in r and "no puede ser" in r["mensaje"] and "Hecho" not in r["mensaje"]


def test_charla_con_gemini(monkeypatch):
    gemini_falso(monkeypatch, Interpretacion(accion="charla", respuesta="¡De nada!"))
    r = chat("gracias")
    assert r["mensaje"] == "¡De nada!" and "plan" not in r


def test_si_gemini_falla_se_usa_el_plan_b(monkeypatch):
    gemini_falso(monkeypatch, None)
    assert chat("somos 2")["plan"] is not None


def test_el_prompt_lleva_el_estado_de_la_sesion(monkeypatch):
    llamadas = []
    gemini_falso(monkeypatch, None, llamadas)
    sid = chat("somos 2 y 60 euros")["session_id"]
    chat("cambia el lunes", sid)
    ultimo = llamadas[-1]
    assert '"comensales": 2' in ultimo and '"presupuesto_eur": 60' in ultimo and "cambia el lunes" in ultimo
    assert "Lunes" not in ultimo and '"lunes": [' in ultimo  # el plan actual va en el contexto
