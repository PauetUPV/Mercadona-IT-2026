# Contrato de la API (para el frontend)

Especificación completa y siempre al día: `http://localhost:8000/docs` (Swagger) y `/openapi.json`
(se puede generar un cliente tipado a partir de ahí). Este documento resume lo esencial.

> **Cambios acordados con el frontend (v2).** Lo marcado como **(NUEVO)** o **(CAMBIA)** es lo pactado con
> el equipo de interfaz y **aún no está implementado**. Resumen de lo que cambia respecto a la v1:
>
> 1. **(CAMBIA)** `plan` solo viene en la respuesta cuando es relevante (ya no en todas).
> 2. **(CAMBIA)** `dias` pasa de `{dia: receta}` a `{dia: [recetas]}`: varias recetas por día.
> 3. **(CAMBIA)** Renombre de "extras": lo que se supone en casa (sal, agua…) pasa a `en_casa` (string[]).
>    `extras` pasa a significar **productos comprables que no pertenecen a ninguna receta** (leche, café…).
> 4. **(NUEVO)** Regla de redondeo de `unidades` (ver "Unidades y carrito").
> 5. **(CAMBIA)** `/sustituir` acepta `session_id` y `receta_id`.
> 6. **(NUEVO)** `POST /lista`: el usuario guarda su lista final.
> 7. **(PENDIENTE, más adelante)** feedback y chips de respuesta rápida (ver al final).

## Idea general

- **El historial lo guarda el backend** (en memoria, por `session_id`). El frontend solo manda el mensaje nuevo.
- **(CAMBIA) El plan solo viene cuando es relevante.** Si la respuesta no trae `plan` (ausente o `null`), significa
  **"nada ha cambiado"**: el frontend conserva el último plan. Si trae `plan`, es el plan completo y **sustituye** al anterior.
  Decidir cuándo incluirlo (nuevo plan, cambio de plato, nuevo presupuesto…) es cosa del backend; una respuesta
  tipo "de nada" o una pregunta aclaratoria no lleva plan.
- El `session_id` lo puede inventar el frontend (cualquier string); si no se envía, el backend crea uno y lo devuelve.
  **(NUEVO)** El frontend genera un `session_id` nuevo cada vez que el usuario empieza una conversación de cero
  (botón "volver"), para que el backend no arrastre contexto que el usuario cree borrado.
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
Si faltan los comensales, la respuesta **no lleva `plan`** y `mensaje` pregunta por ellos.

Respuesta (recortada; los `ingredientes` y las `lineas` reales traen más elementos):

```json
{
  "session_id": "demo",
  "mensaje": "¡Listo! Plan para 2 persona(s). lunes: Pollo al horno con patatas y Ensalada de pasta; martes: Lasaña boloñesa (lista para comer). Total de la compra: 16,77 €, dentro de tu presupuesto de 30,00 €.",
  "plan": {
    "id": "af91ab62",
    "dias": {
      "lunes": [
        {
          "id": "r1",
          "nombre": "Pollo al horno con patatas",
          "tipo": "cocinar",
          "momento": "comida",
          "raciones": 2,
          "ingredientes": [
            { "producto_id": "2787", "unidades": 1.0 },
            { "producto_id": "4640", "unidades": 0.25 }
          ],
          "en_casa": ["sal", "pimienta"],
          "precio_estimado": 7.2
        },
        {
          "id": "r2",
          "nombre": "Ensalada de pasta",
          "tipo": "cocinar",
          "momento": "cena",
          "raciones": 2,
          "ingredientes": [
            { "producto_id": "4640", "unidades": 0.25 }
          ],
          "en_casa": [],
          "precio_estimado": 4.2
        }
      ],
      "martes": [
        {
          "id": "l1",
          "nombre": "Lasaña boloñesa (lista para comer)",
          "tipo": "listo_para_comer",
          "momento": "comida",
          "raciones": 2,
          "ingredientes": [
            { "producto_id": "4487", "unidades": 2.0 }
          ],
          "en_casa": [],
          "precio_estimado": 5.5
        }
      ]
    },
    "extras": [
      { "producto_id": "3314", "unidades": 1 }
    ],
    "en_casa": ["pimienta", "sal"],
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
    "comensales": 2,
    "presupuesto": 30.0,
    "dentro_presupuesto": true
  }
}
```

Campos relevantes del plan:
- **(CAMBIA)** `dias`: **lista de recetas por día** (`tipo`: `cocinar` | `listo_para_comer`). Las claves son los nombres de día tal cual.
  Cada receta puede llevar un `momento` opcional (`"comida"` | `"cena"`); el frontend de momento lo ignora.
  Un `listo_para_comer` es una receta con **un solo ingrediente** (el propio producto).
- `ingredientes`: `{producto_id, unidades}`; el frontend busca el producto en `carrito.lineas` por `producto_id`,
  así que **todo `producto_id` de una receta o de `extras` debe aparecer en `carrito.lineas`**.
- **(CAMBIA)** `extras`: **productos que el usuario necesita pero que no son de ninguna receta** (leche, café…),
  con la misma forma que un ingrediente (`{producto_id, unidades}`). **Sí llevan precio y entran en el carrito.**
  No dependen de los días: si el usuario desmarca un día, los extras se quedan. Se añaden desde el chat
  ("añade leche") o desde la búsqueda.
- **(NUEVO)** `en_casa`: lo que se supone que ya hay en casa (sal, agua…). Es lo que antes se llamaba `extras`:
  solo texto, **no** lleva precio ni entra en el carrito. Existe a nivel de plan y de receta.
- `carrito.lineas`: productos reales de Mercadona con `unidades` (envases enteros) y `subtotal`; `carrito.total` es el precio de la compra.
  **Incluye los ingredientes de todas las recetas y los `extras`.**
- `presupuesto` / `dentro_presupuesto`: `false` significa que ni el plan más barato que encuentra cabe en el presupuesto.
- `id` del plan: identifica el plan; cambia cada vez que cambia su contenido (nuevo plan o plato sustituido).

### (NUEVO) Unidades y carrito

- En `ingredientes` y `extras`, `unidades` puede ser **fraccionaria**: es la fracción de un envase que gasta esa receta
  (0.25 = un cuarto del aceite). Así dos recetas que comparten el aceite no obligan a comprar dos envases.
- En `carrito.lineas`, `unidades` son **envases enteros**:

  ```
  carrito.unidades = ceil( suma de unidades de ese producto en todas las recetas y extras seleccionados )
  ```

  Con una pequeña tolerancia (`ceil(x - 1e-9)`) para que `2.0000000001` no se convierta en 3.
  `subtotal = unidades × precio`.
- El frontend usa esta misma regla para **recalcular la lista en local** cuando el usuario desmarca un día, sin llamar al
  backend. Con todos los días marcados, su resultado debe coincidir con `carrito` (lo comprobamos en desarrollo);
  si no coincide, manda el `carrito` del backend.

## GET /chat/{session_id}

Para recargar la página: `{ "session_id", "historial": [{"rol": "usuario"|"asistente", "texto"}], "plan" }`. 404 si no existe.
Aquí `plan` es el último plan vigente de la sesión (o `null` si aún no hay).

## (NUEVO) POST /lista

El usuario ha revisado el plan, editado la lista (quitar productos, cambiar cantidades) y pulsa "guardar".
Es la señal de qué se compró de verdad; el backend la necesita para poder preguntar luego "¿qué tal salió?".

Petición:

```json
{
  "session_id": "demo",
  "plan_id": "af91ab62",           // opcional
  "nombre": "Comidas de la semana", // opcional
  "lineas": [
    { "producto_id": "4640", "unidades": 1 },
    { "producto_id": "3314", "unidades": 2 }
  ]
}
```

Respuesta:

```json
{
  "lista_id": "l_91c2",
  "mensaje": "Guardada. Luego te pregunto qué tal salió."   // opcional
}
```

- `unidades` aquí son **envases enteros** ya editados por el usuario (pueden diferir del carrito original).
- Si viene `mensaje`, el frontend lo muestra como burbuja de Merche.
- El frontend guarda además la lista en su propia pestaña "Listas" (en local); el backend solo necesita registrarla.

## Otros endpoints

| Método | Ruta | Uso |
|---|---|---|
| POST | `/plan` | Generar plan sin chat: `{comensales, presupuesto?, dias[], restricciones?}` → plan |
| POST | `/sustituir` | **(CAMBIA)** `{plan, dia, receta_id?, session_id?, comensales?}` → plan nuevo (ver abajo) |
| POST | `/lista` | **(NUEVO)** Guardar la lista final del usuario (ver arriba) |
| GET | `/productos?q=&categoria=&precio_max=&limite=` | Buscar en el catálogo real (el frontend usa este para la búsqueda) |
| GET | `/productos/{id}` | Detalle de producto |
| GET | `/categorias` | Árbol de categorías |
| GET | `/catalogo` | Lista de recetas disponibles |
| GET | `/dashboard` | Métricas: planes, sustituciones, gasto medio, recetas más usadas, ahorro vs presupuesto |
| GET | `/health` | Comprobación |

### (CAMBIA) `/sustituir`

Sigue sin necesitar sesión, pero con tres ajustes:

- `receta_id` (opcional): como ahora hay varias recetas por día, indica **cuál** se sustituye. Si falta y el día
  tiene una sola, se sustituye esa.
- `session_id` (opcional): si viene, el plan de la sesión **se actualiza** con la sustitución. Sin esto, un mensaje
  posterior como "mejor 25 euros" regeneraría desde el plan antiguo y deshaciría el cambio en silencio.
- Devuelve el plan nuevo completo (con `id` nuevo).

Cambiar un plato por **chat** ("cambia el martes") sigue siendo la vía principal; el frontend usará `/sustituir` solo
para un botón "cambiar" en cada receta.

## Errores

`404 {"detail": "..."}` (no existe) y `422 {"detail": ...}` (datos no válidos: comensales ≤ 0, días vacíos o repetidos, mensaje vacío...).
Las respuestas del chat que no entienden algo **no** son errores: vienen con 200 y un `mensaje` explicativo.
El frontend ignora campos desconocidos, así que se pueden añadir campos sin avisar.

## (PENDIENTE, más adelante) Feedback y chips

No hace falta para la primera integración; se apunta aquí para no pintarnos en una esquina. Propuesta, todo **opcional y aditivo**
(no rompe nada de lo anterior):

- **Chips de respuesta rápida:** campo `sugerencias: string[]` (máx. 4, cortos) en la respuesta de `/chat`.
  Al pulsar uno, el frontend lo envía como `mensaje`.
- **Feedback:** campo `feedback` en la respuesta de `/chat` cuando Merche quiere preguntar cómo salió algo:
  `{ "sujeto": { "tipo": "receta" | "producto", "id": "r1", "nombre": "...", "imagen": "..." } }`.
  La pregunta va en `mensaje`; el frontend pinta 👍👎.
- **Respuesta al feedback:** `POST /feedback` con `{ session_id, sujeto: {tipo, id}, valor: "positivo" | "negativo" }`;
  puede devolver `{ mensaje, sugerencias? }` (por ejemplo "¿Qué falló?" con chips "Estaba soso", "Muy caro").
- **Apertura:** a decidir cómo arranca Merche una conversación cuando quiere empezar ella (p. ej. pedir feedback al abrir
  la pestaña): un `GET /bienvenida?session_id=` o un `mensaje` especial.

## Para quien integre Gemini

Solo hay dos puntos de enganche, ambos con una función que se puede reescribir sin tocar el resto:
- `app/logic/interprete.py::interpretar(mensaje) -> Interpretacion`: del texto del usuario a datos estructurados.
- `app/logic/mensajes.py`: textos del asistente (`plan_nuevo`, `plan_sustituido`...).

Configuración en `.env` (`LLM_PROVIDER=gemini`, `LLM_API_KEY`, `LLM_MODEL`) y `app/logic/llm.py`.
Los precios y el carrito los calcula siempre el código con el catálogo real; el LLM no debe inventarlos.
