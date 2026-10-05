"""Integración con el LLM. Proveedor: Gemini."""
import logging
import os
import time
from typing import Callable, Optional, TypeVar
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash").strip().replace('"', '').replace("'", "")
# Modelos de reserva: si el principal está saturado (503), sin cuota (429) o no existe (404), se prueba el siguiente
LLM_MODELOS_RESERVA = [
    m.strip() for m in os.getenv("LLM_MODELOS_RESERVA", "gemini-3.5-flash-lite,gemini-3.7-flash").split(",") if m.strip()
]
# Instrucciones (system prompt) del LLM
SYSTEM_PROMPT = """
Eres un asistente virtual de Mercadona. Eres amable, directo y servicial. 
Respondes siempre en español de España. Si te preguntan por productos, 
asumes que son de la marca Hacendado, Bosque Verde o Deliplus si aplica.
"""

# Log propio ("merche"): dice en cada mensaje si respondió Gemini o el plan B. Nivel con LOG_LEVEL en .env (DEBUG por defecto)
log = logging.getLogger("merche")
if not log.handlers:
    _salida = logging.StreamHandler()
    _salida.setFormatter(logging.Formatter("%(asctime)s [merche] %(levelname)s %(message)s", "%H:%M:%S"))
    log.addHandler(_salida)
    log.setLevel(os.getenv("LOG_LEVEL", "DEBUG").upper())
    log.propagate = False

# Inicializamos el cliente una sola vez para que sea más rápido
cliente_gemini = genai.Client(api_key=LLM_API_KEY) if LLM_API_KEY else None
if cliente_gemini:
    log.info("Gemini ACTIVO (modelo %s)", LLM_MODEL)
else:
    log.warning("Gemini DESACTIVADO: no hay LLM_API_KEY (existe .env en %s?). Todo ira por el plan B", os.getcwd())

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


def disponible() -> bool:
    return cliente_gemini is not None


def _con_modelos(tarea: str, llamada: Callable[[str], T], timeout_ms: int) -> Optional[T]:
    """Ejecuta `llamada(modelo)` con el modelo principal y, si está saturado/sin cuota/no existe, con los de reserva.
    Devuelve None si no hay LLM o todos fallan (el llamador usa su plan B)."""
    if not cliente_gemini:
        log.debug("Gemini no configurado -> plan B")
        return None
    inicio = time.time()
    modelos = [LLM_MODEL] + [m for m in LLM_MODELOS_RESERVA if m != LLM_MODEL]
    for intento, modelo in enumerate(modelos):
        try:
            resultado = llamada(modelo)
            log.debug("Gemini (%s) respondio en %.1f s (%s)", modelo, time.time() - inicio, tarea)
            return resultado
        except Exception as e:  # red, cuota, JSON inválido...
            recuperable = any(c in str(e) for c in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND"))
            if recuperable and intento < len(modelos) - 1:
                log.debug("Gemini %s no disponible (%s), pruebo %s", modelo, str(e)[:40], modelos[intento + 1])
                continue
            log.warning("Gemini fallo tras %.1f s (%s: %s) -> plan B", time.time() - inicio, type(e).__name__, str(e)[:200])
            return None
    return None


def generar_json(prompt: str, esquema: type[T], sistema: str, temperatura: float = 0.2) -> Optional[T]:
    """Pide a Gemini una respuesta con la forma de `esquema`. Devuelve None si no hay LLM o falla
    (el llamador usa entonces su plan B), para que el chat nunca se caiga por el LLM."""

    def llamada(modelo: str) -> T:
        respuesta = cliente_gemini.models.generate_content(
            model=modelo,
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

    return _con_modelos(esquema.__name__, llamada, 15000)


INSTRUCCION_TRANSCRIPCION = (
    "Transcribe literalmente lo que dice la persona del audio, en español de España, con su puntuación. "
    "Devuelve SOLO el texto dicho, sin comillas, sin explicaciones y sin traducir. "
    "Si no se entiende nada o no hay voz, devuelve un texto vacío."
)


def transcribir(audio: bytes, mime: str) -> Optional[str]:
    """Audio -> texto con Gemini. None si no hay LLM o falla; "" si no se entendió nada."""

    def llamada(modelo: str) -> str:
        respuesta = cliente_gemini.models.generate_content(
            model=modelo,
            contents=[types.Part.from_bytes(data=audio, mime_type=mime), INSTRUCCION_TRANSCRIPCION],
            config=types.GenerateContentConfig(temperature=0, http_options=types.HttpOptions(timeout=20000)),
        )
        return (respuesta.text or "").strip().strip('"').strip()

    return _con_modelos("transcripcion", llamada, 20000)
