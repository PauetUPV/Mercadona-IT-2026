from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="Mercadona IT 2026")

# CORS: imprescindible para que el frontend (en otro puerto) pueda llamar a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en hackatón, vale con esto
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
