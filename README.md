# Mercadona IT 2026

Backend FastAPI de **Merche**, la asistente que planifica la comida de la semana con productos reales de Mercadona.
Capas: `app/api` → `app/logic` → `app/data` (+ `app/models` con los esquemas pydantic).

## Arranque

```bash
python -m venv venv
venv\Scripts\activate        # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
# .env con LLM_API_KEY (Gemini). Sin clave el chat funciona igualmente con el plan B por reglas
uvicorn main:app --reload
pytest                       # 73 tests, sin red ni Gemini
```

Swagger en http://localhost:8000/docs

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/chat` | **El principal.** Mensaje del usuario → texto de Merche (+ plan si ha cambiado) |
| GET | `/chat/{session_id}` | Historial y plan vigente (recargar la página) |
| POST | `/lista` | El usuario guarda su lista final de la compra |
| GET | `/bienvenida` | Primer mensaje de Merche al abrir (saludo, o pregunta de feedback si procede) |
| POST | `/feedback` | Valoración 👍/👎; Merche encadena la siguiente pregunta |
| POST | `/opinion` | Queja o sugerencia en texto libre (también se puede decir por chat) |
| GET | `/informe` | **Lado Mercadona:** lo que opinan los clientes, ordenado por el sistema de agentes |
| GET | `/productos?q=&categoria=&precio_max=&limite=` | Búsqueda en el catálogo real |
| GET | `/health` | Comprobación de vida |

Contrato detallado para el frontend, con ejemplos: [docs/contrato.md](docs/contrato.md).

## Cómo funciona un mensaje

```
mensaje → Gemini clasifica (1 llamada) → el código ejecuta y comprueba viabilidad → se guarda el estado → respuesta
```

- **El LLM solo entiende y propone texto** (`app/logic/agente.py`). Platos, cantidades, precios y viabilidad los decide el código
  (`app/logic/planificador.py`) con el catálogo real. Si falla Gemini (cuota, red, 503), se usa un intérprete por reglas (`interprete.py`).
- **Estado de la sesión** (`app/logic/sesiones.py`): preferencias (personas, presupuesto, días, dieta...), plan vigente, listas y feedback.
  Se guarda en memoria y en `.estado/` (ignorado por git), así que sobrevive a reinicios.
- **Feedback para Mercadona** (`app/logic/opiniones.py`, `mas.py`): valoraciones y quejas de todas las sesiones se guardan juntas y
  cuatro agentes (analista, catálogo, agregador, redactor) las convierten en el informe de `/informe` (ver contrato).
- **Reglas de precio**: si el presupuesto no alcanza ni para el plan más barato, no hay plan y se explica por qué (ver contrato).

## Datos

- `app/data/mercadona_catalog/`: catálogo real de Mercadona
  ([datania/mercadona-catalog](https://huggingface.co/datasets/datania/mercadona-catalog), MIT), versionado en el repo.
- `app/data/mock_data.json`: **78 recetas** (58 para cocinar y 20 listas para comer) con ingredientes y cantidades reales, instrucciones y
  etiquetas de alérgenos. Se generan con `PYTHONPATH=. python scripts/generar_mock_data.py` (la despensa mapea cada ingrediente a un producto real
  y convierte gramos/ml en fracción de envase).

## Pendiente

- Valoración de productos (hoy el feedback pregunta por recetas) y que el feedback influya más en los planes
- Ampliar el recetario o cargarlo de una fuente externa si hace falta más variedad
- Persistencia en base de datos si el proyecto crece (hoy: ficheros JSON en `.estado/`)
