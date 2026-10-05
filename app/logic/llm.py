"""Integración con el LLM. Proveedor: Gemini."""
import logging
import os
from typing import Optional, TypeVar
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash").strip().replace('"', '').replace("'", "")
# Instrucciones (system prompt) del LLM
SYSTEM_PROMPT = """
Eres un asistente virtual de Mercadona. Eres amable, directo y servicial. 
Respondes siempre en español de España. Si te preguntan por productos, 
asumes que son de la marca Hacendado, Bosque Verde o Deliplus si aplica.
"""

# Inicializamos el cliente una sola vez para que sea más rápido
cliente_gemini = genai.Client(api_key=LLM_API_KEY) if LLM_API_KEY else None

def consultar_llm(prompt: str) -> str:
    """Envía el mensaje a Gemini y devuelve la respuesta en texto."""
    if not cliente_gemini:
        return "Error interno: La API Key del LLM no está configurada en el archivo .env"
    

    try:
        respuesta = cliente_gemini.models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            )
        )
        # Solución: Si respuesta.text es None, devuelve este mensaje por defecto
        return respuesta.text or "Lo siento, la IA no devolvió ninguna respuesta."
        
    except Exception as e:
        return f"Error de comunicación con la IA: {str(e)}"


T = TypeVar("T", bound=BaseModel)
log = logging.getLogger(__name__)


def disponible() -> bool:
    return cliente_gemini is not None


def generar_json(prompt: str, esquema: type[T], sistema: str, temperatura: float = 0.2) -> Optional[T]:
    """Pide a Gemini una respuesta con la forma de `esquema`. Devuelve None si no hay LLM o falla
    (el llamador usa entonces su plan B), para que el chat nunca se caiga por el LLM."""
    if not cliente_gemini:
        return None
    try:
        respuesta = cliente_gemini.models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=sistema,
                response_mime_type="application/json",
                response_schema=esquema,
                temperature=temperatura,
                http_options=types.HttpOptions(timeout=15000),  # ms: si Gemini tarda, plan B
            ),
        )
        return esquema.model_validate_json(respuesta.text)
    except Exception as e:  # red, cuota, JSON inválido...
        log.warning("Gemini falló (%s: %s); se usa el plan B", type(e).__name__, e)
        return None
