"""Integración con el LLM. Proveedor: Gemini."""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

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