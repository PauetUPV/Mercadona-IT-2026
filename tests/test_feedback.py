"""Feedback completo: qué se pregunta tras una compra y qué aprende Merche de cada respuesta."""
from fastapi.testclient import TestClient

from app.logic import sesiones
from app.logic.planificador import Peticion, generar_plan
from main import app

client = TestClient(app)


def chat(mensaje, sid="f", **extra):
    r = client.post("/chat", json={"mensaje": mensaje, "session_id": sid, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def guardar(sid, lineas=()):
    r = client.post("/lista", json={"session_id": sid, "lineas": [{"producto_id": p, "unidades": 1} for p in lineas]})
    assert r.status_code == 200, r.text


def valorar(sid, sujeto, valor, motivo=None):
    body = {"session_id": sid, "sujeto": {"tipo": sujeto["tipo"], "id": sujeto["id"]}, "valor": valor}
    if motivo:
        body["motivo"] = motivo
    return client.post("/feedback", json=body).json()


def abrir(sid, anterior=None):
    params = {"session_id": sid, **({"sesion_anterior": anterior} if anterior else {})}
    return client.get("/bienvenida", params=params).json()


def recetas(plan):
    return [r for rs in plan["dias"].values() for r in rs]


def test_solo_pregunta_por_lo_que_se_compro():
    plan = chat("somos 2, de lunes a miércoles")["plan"]
    martes = plan["dias"]["martes"][0]
    guardar("f", [i["producto"]["id"] for i in martes["ingredientes"]])  # solo compró lo del martes
    sujetos = sesiones.buscar("f").listas[0]["sujetos"]
    assert martes["id"] in [s["id"] for s in sujetos]
    assert len(sujetos) < 3 or all(
        any(i["producto"]["id"] in {x["producto"]["id"] for x in martes["ingredientes"]} for i in r["ingredientes"])
        for r in recetas(plan) if r["id"] in [s["id"] for s in sujetos]
    )


def test_pregunta_por_productos_sueltos_tambien():
    chat("somos 2, de lunes a martes")
    plan = chat("añade leche")["plan"]
    guardar("f")
    tipos = [s["tipo"] for s in sesiones.buscar("f").listas[0]["sujetos"]]
    assert tipos[-1] == "producto" and plan["extras"][0]["producto"]["id"] == sesiones.buscar("f").listas[0]["sujetos"][-1]["id"]


def test_pulgar_arriba_vuelve_a_salir_en_el_siguiente_plan():
    plan = chat("somos 2, solo el lunes", "fav")["plan"]
    receta = plan["dias"]["lunes"][0]
    guardar("fav")
    r = valorar("fav", {"tipo": "receta", "id": receta["id"]}, "positivo")
    assert "Lo volveré a proponer" in r["mensaje"]
    assert sesiones.buscar("fav").favoritas == [receta["id"]]
    otra = chat("hazme un plan para toda la semana", "fav")["plan"]  # con 7 días, el favorito va primero
    assert otra["dias"]["lunes"][0]["id"] == receta["id"]


def test_muy_caro_hace_planes_mas_baratos():
    p = Peticion(comensales=2, dias=["lunes", "martes", "miércoles"])
    barato = Peticion(comensales=2, dias=["lunes", "martes", "miércoles"], prefiere_barato=True)
    coste = lambda plan: sum(r.precio_estimado for rs in plan.dias.values() for r in rs)  # noqa: E731
    assert coste(generar_plan(barato)) <= coste(generar_plan(p))

    chat("somos 2", "caro")
    guardar("caro")
    sujeto = abrir("caro")["feedback"]
    r = valorar("caro", sujeto, "negativo")
    assert "Muy caro" in r["sugerencias"] and "Mucho trabajo" in r["sugerencias"]
    r = valorar("caro", sujeto, "negativo", "Muy caro")
    assert "más baratas" in r["mensaje"] and sesiones.buscar("caro").prefiere_barato
    assert sujeto["id"] in sesiones.buscar("caro").rechazadas


def test_mucho_trabajo_hace_planes_mas_sencillos():
    normal = generar_plan(Peticion(comensales=2, dias=["lunes", "martes", "miércoles"]))
    facil = generar_plan(Peticion(comensales=2, dias=["lunes", "martes", "miércoles"], prefiere_facil=True))
    n = lambda plan: sum(len(r.ingredientes) for rs in plan.dias.values() for r in rs)  # noqa: E731
    assert n(facil) <= n(normal)


def test_producto_rechazado_no_se_vuelve_a_elegir_y_el_favorito_si():
    chat("somos 2", "prod")
    leche = chat("añade leche", "prod")["plan"]["extras"][0]["producto"]
    valorar("prod", {"tipo": "producto", "id": leche["id"]}, "negativo", "No me gustó")
    chat("quita la leche", "prod")
    otra = chat("añade leche", "prod")["plan"]["extras"][0]["producto"]
    assert otra["id"] != leche["id"] and otra["nombre"].lower().startswith("leche")
    valorar("prod", {"tipo": "producto", "id": otra["id"]}, "positivo")
    chat("quita la leche", "prod")
    assert chat("añade leche", "prod")["plan"]["extras"][0]["producto"]["id"] == otra["id"]


def test_volver_empieza_de_cero_pero_conserva_la_memoria():
    plan = chat("somos 3 y sin gluten", "vieja")["plan"]
    guardar("vieja")
    primero = abrir("vieja")["feedback"]
    valorar("vieja", primero, "positivo")

    # "Volver": sesión nueva que viene de la anterior
    r = abrir("nueva", anterior="vieja")
    assert r["feedback"]["id"] != primero["id"]  # sigue preguntando por lo pendiente de aquella compra
    nueva = sesiones.buscar("nueva")
    assert nueva.mensajes[-1].texto == r["mensaje"] and len(nueva.mensajes) == 1  # conversación nueva
    assert nueva.plan is None and nueva.comensales is None  # la semana empieza de cero
    assert nueva.excluir == ["gluten"] and nueva.favoritas == [primero["id"]]  # la memoria se queda
    assert len(recetas(plan)) >= 2


def test_volver_desde_el_chat_tambien_hereda():
    chat("somos 2, soy vegetariano", "a1")
    chat("hola, quiero un plan", "a2", sesion_anterior="a1")
    assert sesiones.buscar("a2").excluir == ["carne", "pescado"]
    chat("somos 2", "a3", sesion_anterior="no-existe")  # anterior desconocida: empieza limpia
    assert sesiones.buscar("a3").excluir == []


def test_preferencias_aprendidas_se_pueden_consultar():
    plan = chat("somos 2, solo el lunes", "pref")["plan"]
    guardar("pref")
    valorar("pref", {"tipo": "receta", "id": plan["dias"]["lunes"][0]["id"]}, "positivo")
    sesion = sesiones.buscar("pref")
    sesion.prefiere_facil = True
    r = chat("¿qué tengo apuntado de mis preferencias?", "pref")
    assert "te gustaron" in r["mensaje"] and "sencillos" in r["mensaje"]


# --- Tienda, "¿qué tal la compra?" y comentarios para Mercadona ---------------------------


def test_al_guardar_pregunta_la_tienda():
    chat("somos 2", "tienda")
    r = client.post("/lista", json={"session_id": "tienda", "lineas": []}).json()
    assert r["mensaje"] == "Lista guardada. ¿En qué tienda vas a hacer la compra?"
    assert r["sugerencias"] == ["Paterna", "Alboraya"]


def test_el_siguiente_chat_pregunta_que_tal_la_compra():
    chat("somos 2, de lunes a martes", "compra")
    guardar("compra")
    r = abrir("compra-2", anterior="compra")  # nuevo chat
    assert "¿Qué tal fue la compra?" in r["mensaje"] and r["feedback"]["nombre"] in r["mensaje"]
    valorar("compra-2", r["feedback"], "positivo")
    r = abrir("compra-3", anterior="compra-2")  # ya contó algo: pregunta directamente por el siguiente plato
    assert "¿Qué tal fue la compra?" not in r["mensaje"] and "¿Qué tal salió" in r["mensaje"]


def test_comentario_se_envia_a_mercadona_y_propone_la_semana_siguiente():
    plan = chat("somos 2", "op")["plan"]
    r = chat("Oye, las latas de atún vienen con demasiado aceite", "op")
    assert r["enviado"] == {"destinatario": "Mercadona", "puntos": ["Las latas de atún vienen con demasiado aceite"]}
    assert "Mercadona" in r["mensaje"] and r["mensaje_conclusion"] == "¿Preparamos lo de la semana que viene?"
    assert r["sugerencias"] == ["Hazme un plan para la semana", "Ahora no, gracias"]
    assert "plan" not in r and sesiones.buscar("op").plan.id == plan["id"]  # no toca el plan
    assert sesiones.buscar("op").opiniones[0]["puntos"] == ["Las latas de atún vienen con demasiado aceite"]
    assert "No te he entendido" not in chat("Ahora no, gracias", "op")["mensaje"]


def test_comentario_con_gemini_usa_sus_puntos_clave(monkeypatch):
    from app.logic import llm
    from app.logic.interprete import Interpretacion

    monkeypatch.setattr(llm, "generar_json", lambda *a, **k: Interpretacion(
        accion="opinion", puntos_clave=["Atún en lata: demasiado aceite", "Pan de molde: llega aplastado"]))
    r = chat("el atún trae un montón de aceite y encima el pan llega chafado", "opg")
    assert r["enviado"]["puntos"] == ["Atún en lata: demasiado aceite", "Pan de molde: llega aplastado"]
