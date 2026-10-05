"""Mensajes de voz: POST /voz transcribe con Gemini (simulado aquí) y el texto se usa luego en /chat."""
from fastapi.testclient import TestClient

from app.logic import llm
from main import app

client = TestClient(app)
WAV = b"RIFF" + b"\x00" * 100  # el contenido da igual: Gemini está simulado


def voz(contenido=WAV, tipo="audio/wav"):
    headers = {"Content-Type": tipo} if tipo else {}
    return client.post("/voz", content=contenido, headers=headers)


def test_transcribe_y_devuelve_el_texto(monkeypatch):
    recibido = {}

    def falso(audio, mime):
        recibido.update(audio=audio, mime=mime)
        return "Somos dos y el martes no cocino"

    monkeypatch.setattr(llm, "transcribir", falso)
    r = voz(tipo="audio/wav; codecs=1")
    assert r.status_code == 200 and r.json() == {"texto": "Somos dos y el martes no cocino"}
    assert recibido == {"audio": WAV, "mime": "audio/wav"}


def test_el_texto_dictado_funciona_en_el_chat(monkeypatch):
    monkeypatch.setattr(llm, "transcribir", lambda a, m: "Somos dos de lunes a martes")
    texto = voz().json()["texto"]
    r = client.post("/chat", json={"session_id": "voz", "mensaje": texto}).json()
    assert list(r["plan"]["dias"]) == ["lunes", "martes"]


def test_errores_de_entrada():
    assert voz(tipo=None).status_code == 422  # sin Content-Type
    assert voz(tipo="text/plain").status_code == 422
    assert voz(contenido=b"").status_code == 422


def test_sin_gemini_avisa_de_que_no_puede_escuchar():
    r = voz()  # en los tests Gemini está desactivado
    assert r.status_code == 503 and "Escríbemelo" in r.json()["detail"]


def test_si_no_se_entiende_nada(monkeypatch):
    monkeypatch.setattr(llm, "transcribir", lambda a, m: "")
    r = voz()
    assert r.status_code == 422 and "No te he entendido" in r.json()["detail"]


def test_transcribir_usa_los_modelos_de_reserva(monkeypatch):
    class Respuesta:
        text = ' "Hola Merche" '

    class Modelos:
        probados = []

        def generate_content(self, model, contents, config):
            self.probados.append(model)
            if model == "principal":
                raise RuntimeError("503 UNAVAILABLE")
            return Respuesta()

    modelos = Modelos()
    monkeypatch.setattr(llm, "cliente_gemini", type("C", (), {"models": modelos})())
    monkeypatch.setattr(llm, "LLM_MODEL", "principal")
    monkeypatch.setattr(llm, "LLM_MODELOS_RESERVA", ["reserva"])
    assert llm.transcribir(b"x", "audio/wav") == "Hola Merche" and modelos.probados == ["principal", "reserva"]
