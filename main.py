from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.routes import router

# 1. Cargar las variables ocultas del .env (Tu código)
load_dotenv()

# 2. Inicializar la aplicación (Código de tu compañero)
app = FastAPI(title="Mercadona IT 2026")

# 3. CORS: imprescindible para que el frontend pueda llamar a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Incluir todas las rutas separadas
app.include_router(router)