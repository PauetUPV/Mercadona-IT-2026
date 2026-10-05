from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.api.routes import router
from app.data.catalogo import _indice
from app.logic.errores import DatosInvalidos, NoEncontrado

# 1. Cargar las variables ocultas del .env
load_dotenv()

# 2. Precarga del catálogo al iniciar la app
@asynccontextmanager
async def lifespan(app: FastAPI):
    _indice()  # precarga el catálogo para que la primera petición no sea lenta
    yield

# 3. Inicializar la aplicación con el lifespan
app = FastAPI(title="Mercadona IT 2026", lifespan=lifespan)

# 4. Configuración CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Manejadores de errores personalizados
@app.exception_handler(NoEncontrado)
async def no_encontrado(request: Request, exc: NoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(DatosInvalidos)
async def datos_invalidos(request: Request, exc: DatosInvalidos):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

# 6. Incluir todas las rutas separadas
app.include_router(router)