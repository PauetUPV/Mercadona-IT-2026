from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

# Esto busca el archivo .env y carga las variables en memoria
load_dotenv()

# Guardamos la clave en una variable de Python de forma segura
CLAVE_IA = os.getenv("API_KEY_IA")

app = FastAPI()

# Definimos la estructura exacta del JSON que esperamos recibir
class MensajeUsuario(BaseModel):
    usuario_id: str
    texto: str
    categoria_producto: Optional[str] = None # Campo opcional
    es_cliente_plus: bool = False # Valor por defecto

@app.post("/chat")
def procesar_chat(datos: MensajeUsuario):
    # Aquí puedes ver cómo acceder a cada parte del JSON
    print(f"El usuario {datos.usuario_id} ha preguntado: {datos.texto}")
    
    # El servidor devolverá automáticamente este diccionario convertido en JSON
    return {
        "estado": "exito",
        "respuesta_bot": f"Procesando tu petición sobre: {datos.texto}",
        "datos_recibidos": {
            "id": datos.usuario_id,
            "plus": datos.es_cliente_plus
        }
    }