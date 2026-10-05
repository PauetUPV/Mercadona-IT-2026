# Contrato de la API (para el frontend)

Especificación completa y siempre al día: `http://localhost:8000/docs` (Swagger) y `/openapi.json`
(se puede generar un cliente tipado a partir de ahí). Este documento resume lo esencial.

## Idea general

- **El historial lo guarda el backend** (en memoria, por `session_id`). El frontend solo manda el mensaje nuevo.
- **Cada respuesta trae el plan completo vigente**: el frontend siempre pinta `plan`; `mensaje` es solo la burbuja de texto.
- El `session_id` lo puede inventar el frontend (cualquier string); si no se envía, el backend crea uno y lo devuelve.
- Si el servidor se reinicia, se pierden sesiones. Para recuperarse, el frontend puede reenviar el `plan` que ya tiene a `/sustituir`
  (que no necesita sesión) o empezar de nuevo con `/chat`.
- CORS abierto a cualquier origen.

## POST /chat

Petición:

```json
{
  "session_id": "demo",            // opcional
  "mensaje": "Somos 2, 30 euros y el martes no cocino",
  "comensales": 2,                 // opcional: si se envía, manda sobre lo interpretado del texto
  "presupuesto": 30,               // opcional
  "dias": ["lunes", "martes"]      // opcional
}
```

El backend entiende (provisionalmente, con reglas; luego Gemini): personas, presupuesto en €, días ("lunes a viernes",
"fin de semana", "toda la semana"), "el martes no cocino" y "cambia el lunes". Los datos se acumulan durante la sesión
(por ejemplo, "mejor 25 euros" regenera el plan con los mismos comensales).
Si faltan los comensales, `plan` viene `null` y `mensaje` pregunta por ellos.

Respuesta (recortada; los `ingredientes` y las `lineas` reales traen más elementos):

```json
{
  "session_id": "demo",
  "mensaje": "¡Listo! Plan para 2 persona(s). lunes: Pollo al horno con patatas; martes: Lasaña boloñesa (lista para comer). Total de la compra: 16,77 €, dentro de tu presupuesto de 30,00 €.",
  "plan": {
    "id": "af91ab62",
    "dias": {
      "lunes": {
        "id": "r1",
        "nombre": "Pollo al horno con patatas",
        "tipo": "cocinar",
        "raciones": 2,
        "ingredientes": [
          {
            "producto_id": "2787",
            "unidades": 1.0
          }
        ],
        "extras": [
          "sal",
          "pimienta"
        ],
        "precio_estimado": 7.2
      },
      "martes": {
        "id": "l1",
        "nombre": "Lasaña boloñesa (lista para comer)",
        "tipo": "listo_para_comer",
        "raciones": 2,
        "ingredientes": [
          {
            "producto_id": "4487",
            "unidades": 2.0
          }
        ],
        "extras": [],
        "precio_estimado": 5.5
      }
    },
    "carrito": {
      "lineas": [
        {
          "producto": {
            "id": "4640",
            "nombre": "Aceite de oliva 1º Hacendado",
            "precio": 3.9,
            "precio_referencia": 3.9,
            "formato_referencia": "L",
            "tamano": 1.0,
            "formato_tamano": "l",
            "categoria": "Aceite, especias y salsas",
            "subcategoria": "Aceite, vinagre y sal",
            "thumbnail": "https://prod-mercadona.imgix.net/images/fe860edbcb...",
            "url": "https://tienda.mercadona.es/product/4640/aceite-ol..."
          },
          "unidades": 1,
          "subtotal": 3.9
        }
      ],
      "total": 16.77
    },
    "total": 16.77,
    "extras": [
      "pimienta",
      "sal"
    ],
    "comensales": 2,
    "presupuesto": 30.0,
    "dentro_presupuesto": true
  }
}
```

Campos relevantes del plan:
- `dias`: receta por día (`tipo`: `cocinar` | `listo_para_comer`). Las claves son los nombres de día tal cual.
- `carrito.lineas`: productos reales de Mercadona con `unidades` (envases enteros) y `subtotal`; `carrito.total` es el precio de la compra.
- `extras`: cosas que se suponen en casa (sal, agua...). Se muestran, **no** llevan precio ni entran en el carrito.
- `presupuesto` / `dentro_presupuesto`: `false` significa que ni el plan más barato que encuentra cabe en el presupuesto.

## GET /chat/{session_id}

Para recargar la página: `{ "session_id", "historial": [{"rol": "usuario"|"asistente", "texto"}], "plan" }`. 404 si no existe.

## Otros endpoints

| Método | Ruta | Uso |
|---|---|---|
| POST | `/plan` | Generar plan sin chat: `{comensales, presupuesto?, dias[], restricciones?}` → plan |
| POST | `/sustituir` | `{plan, dia, comensales?}` → plan nuevo (sin sesión; sirve para botón "cambiar este plato") |
| GET | `/productos?q=&categoria=&precio_max=&limite=` | Buscar en el catálogo real |
| GET | `/productos/{id}` | Detalle de producto |
| GET | `/categorias` | Árbol de categorías |
| GET | `/catalogo` | Lista de recetas disponibles |
| GET | `/dashboard` | Métricas: planes, sustituciones, gasto medio, recetas más usadas, ahorro vs presupuesto |
| GET | `/health` | Comprobación |

## Errores

`404 {"detail": "..."}` (no existe) y `422 {"detail": ...}` (datos no válidos: comensales ≤ 0, días vacíos o repetidos, mensaje vacío...).
Las respuestas del chat que no entienden algo **no** son errores: vienen con 200 y un `mensaje` explicativo.

## Para quien integre Gemini

Solo hay dos puntos de enganche, ambos con una función que se puede reescribir sin tocar el resto:
- `app/logic/interprete.py::interpretar(mensaje) -> Interpretacion`: del texto del usuario a datos estructurados.
- `app/logic/mensajes.py`: textos del asistente (`plan_nuevo`, `plan_sustituido`...).

Configuración en `.env` (`LLM_PROVIDER=gemini`, `LLM_API_KEY`, `LLM_MODEL`) y `app/logic/llm.py`.
Los precios y el carrito los calcula siempre el código con el catálogo real; el LLM no debe inventarlos.
