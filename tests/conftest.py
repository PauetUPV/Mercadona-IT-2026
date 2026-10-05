import pytest

from app.logic import llm, sesiones


@pytest.fixture(autouse=True)
def aislar(tmp_path, monkeypatch):
    """Tests sin red y sin tocar el disco real: sin Gemini y con un directorio de estado temporal."""
    monkeypatch.setattr(llm, "cliente_gemini", None)
    monkeypatch.setattr(sesiones, "DIRECTORIO", tmp_path / "estado")
    sesiones.reset()
    yield
    sesiones.reset()
