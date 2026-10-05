# Mercadona IT 2026

Backend FastAPI. Capas: `app/api` → `app/logic` → `app/data` (+ `app/models` con los esquemas pydantic).

## Arranque

```bash
python -m venv venv
venv\Scripts\activate        # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
uvicorn main:app --reload
pytest                       # tests
```

Swagger en http://localhost:8000/docs

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/chat` | Mensaje del usuario → texto del asistente + plan vigente (historial guardado en el backend) |
| GET | `/chat/{session_id}` | Historial y plan de una sesión |
| GET | `/health` | Comprobación de vida |
| POST | `/plan` | Genera plan (días, comensales, presupuesto, restricciones) + carrito |
| POST | `/sustituir` | Cambia el plato de un día; recibe el plan actual y devuelve el plan y carrito nuevos |
| GET | `/catalogo` | Recetas mock |
| GET | `/categorias` | Árbol de categorías de Mercadona |
| GET | `/productos?q=&categoria=&precio_max=&limite=` | Búsqueda en el catálogo real |
| GET | `/productos/{id}` | Detalle de un producto |
| GET | `/dashboard` | Métricas de los planes generados (en memoria) |

Contrato detallado para el frontend, con ejemplos: [docs/contrato.md](docs/contrato.md).

Errores: 404 si no existe el producto/día, 422 si los datos no son válidos.

## Datos

- `app/data/mercadona_catalog/`: catálogo real de Mercadona
  ([datania/mercadona-catalog](https://huggingface.co/datasets/datania/mercadona-catalog), MIT),
  versionado en el repo. Se indexa y normaliza en memoria al arrancar.
- `app/data/mock_data.json`: recetas mock con ingredientes (ids reales del catálogo).
  Se regenera con `python scripts/generar_mock_data.py`; el precio de cada receta se calcula.

## Cómo funciona (sin LLM)

- Carrito: suma los ingredientes de todas las recetas, escala por comensales y compra envases enteros.
- Plan: elige recetas sin repetir; los días con "no cocino" llevan platos `listo_para_comer`;
  si hay presupuesto, abarata el plan cambiando platos hasta cumplirlo (o hasta no poder más: `dentro_presupuesto=false`).
- Sustitución: otro plato del mismo tipo, sin repetir y de precio parecido.
- Dashboard: planes, sustituciones, gasto medio, recetas más usadas, ahorro frente al presupuesto.

## Pendiente (necesita decisiones)

- Proveedor/modelo LLM e instrucciones (`app/logic/llm.py`, `.env`)
- Gemini (otra persona): sustituir `interpretar()` y `mensajes.py` (ver docs/contrato.md); hoy el chat usa reglas simples
- Persistencia real del historial (hoy en memoria) y criterio de "ahorro"
- Recetas reales / gestión de alérgenos y dietas
