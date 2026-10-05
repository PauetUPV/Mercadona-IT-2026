from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.data.catalogo import _indice
from app.logic.errores import DatosInvalidos, NoEncontrado


@asynccontextmanager
async def lifespan(app: FastAPI):
    _indice()  # precarga el catálogo para que la primera petición no sea lenta
    yield


app = FastAPI(title="Mercadona IT 2026", lifespan=lifespan)

# CORS: imprescindible para que el frontend (en otro puerto) pueda llamar a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en hackatón, vale con esto
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NoEncontrado)
async def no_encontrado(request: Request, exc: NoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DatosInvalidos)
async def datos_invalidos(request: Request, exc: DatosInvalidos):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.include_router(router)
