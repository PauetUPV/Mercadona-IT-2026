"""Integración con el LLM. Proveedor, modelo e instrucciones: pendientes de decidir."""
import os

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

# TODO: instrucciones (system prompt) del LLM
SYSTEM_PROMPT = ""


def consultar_llm(prompt: str) -> str:
    # TODO: elegir proveedor, instalar su cliente e implementar
    raise NotImplementedError("LLM aún no configurado")
