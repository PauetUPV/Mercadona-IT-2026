# Contrato de la API (para el frontend)

Especificación completa y siempre al día: `http://localhost:8000/docs` (Swagger) y `/openapi.json`
(se puede generar un cliente tipado a partir de ahí). Este documento resume lo esencial.

> **Cambios acordados con el frontend (v3).** Lo marcado como **(NUEVO)** o **(CAMBIA)** es lo pactado con
> el equipo de interfaz y **aún no está implementado**. Resumen de lo que cambia respecto a la v1:
>
> 1. **(CAMBIA)** `plan` solo viene en la respuesta cuando es relevante (ya no en todas).
> 2. **(NUEVO)** El frontend envía `plan` en la petición cada vez que el usuario lo ha editado (días, recetas, extras o cantidades).
> 3. **(NUEVO)** La respuesta puede llevar `mensaje_conclusion`: un segundo texto que va **después** del plan.
> 4. **(CAMBIA)** `dias` pasa de `{dia: receta}` a `{dia: [recetas]}`: varias recetas por día.
> 5. **(CAMBIA)** **Sin `carrito` ni totales.** Cada ingrediente lleva el producto completo dentro (`producto`). El plan ya no trae
>    `comensales`, `presupuesto`, `total` ni `dentro_presupuesto`: el frontend calcula la lista y los precios.
> 6. **(CAMBIA)** Renombre de "extras": lo que se supone en casa (sal, agua…) pasa a `en_casa` (string[]).
>    `extras` pasa a significar **productos comprables que no pertenecen a ninguna receta** (leche, café…).
> 7. **(NUEVO)** Las recetas llevan `instrucciones` (cómo prepararlas).
> 8. **(NUEVO)** Regla de redondeo de `unidades` (ver "Unidades y lista de la compra").
> 9. **(CAMBIA)** Se elimina `/sustituir`: cambiar un plato se hace por chat ("cambia el martes").
> 10. **(NUEVO)** `POST /lista`: el usuario guarda su lista final.
> 11. **(PENDIENTE, más adelante)** feedback y chips de respuesta rápida (ver al final).

## Idea general

- **El historial lo guarda el backend** (en memoria, por `session_id`). El frontend solo manda el mensaje nuevo.
- **(CAMBIA) El plan solo viene cuando es relevante.** Si la respuesta no trae `plan` (ausente o `null`), significa
  **"nada ha cambiado"**: el frontend conserva el último plan. Si trae `plan`, es el plan completo y **sustituye** al anterior.
  Decidir cuándo incluirlo (nuevo plan, cambio de plato, nuevo presupuesto…) es cosa del backend; una respuesta
  tipo "de nada" o una pregunta aclaratoria no lleva plan.
- El `session_id` lo puede inventar el frontend (cualquier string); si no se envía, el backend crea uno y lo devuelve.
  **(NUEVO)** El frontend genera un `session_id` nuevo cada vez que el usuario empieza una conversación de cero
  (botón "volver"), para que el backend no arrastre contexto que el usuario cree borrado.
- Si el servidor se reinicia, se pierden sesiones. Para recuperarse, el frontend puede reenviar el `plan` que ya tiene
  en su siguiente `/chat` (el campo `plan` de la petición) o empezar de nuevo.
- **(NUEVO)** Los nombres de día son siempre estos, en minúsculas y con tilde:
  `lunes`, `martes`, `miércoles`, `jueves`, `viernes`, `sábado`, `domingo`. El frontend los ordena él mismo
  (no depende del orden de las claves del JSON).
- CORS abierto a cualquier origen.

## POST /chat

Petición:

```json
{
  "session_id": "demo",            // opcional
  "mensaje": "Somos 2, 30 euros y el martes no cocino",
  "plan": { }                      // opcional: el plan tal como lo ve el usuario, si lo ha editado (ver abajo)
}
```

El backend entiende (provisionalmente, con reglas; luego Gemini): personas, presupuesto en €, días ("lunes a viernes",
"fin de semana", "toda la semana"), "el martes no cocino" y "cambia el lunes". Los datos se acumulan durante la sesión
(por ejemplo, "mejor 25 euros" regenera el plan con los mismos comensales).
Si faltan los comensales, la respuesta **no lleva `plan`** y `mensaje` pregunta por ellos.

### (NUEVO) `plan` en la petición

Cuando el usuario edita el plan antes de escribir, el frontend envía en su **siguiente mensaje** el plan tal como lo ve
ahora, con **la misma forma que recibió** en la respuesta. Así "cambia el martes" o "mejor 25 euros" se aplican sobre
lo que el usuario realmente ve y no sobre el plan original.

- El backend lo toma como **plan vigente** de la sesión (manda sobre el que tenía guardado).
- Se envía tras **cualquier edición**: desmarcar un día, quitar una receta, quitar un producto, cambiar una cantidad.
  Si no hay ediciones desde el último plan, el campo no se envía.
- Cómo se refleja cada edición en el JSON:
  - día desmarcado o receta quitada → desaparece de `dias`;
  - producto o extra quitado → desaparece de los `ingredientes` / `extras` que lo contenían;
  - **cantidad cambiada** (el usuario pide N envases de un producto) → el frontend reescala las `unidades` de ese producto
    en todas las recetas y extras donde aparece, de modo que su suma sea N. Por ejemplo, el aceite con 0.25 + 0.25 y el usuario
    pide 2 envases → pasa a 1.0 + 1.0. Si el producto solo está en `extras`, se cambia su `unidades` directamente.

### Respuesta

Recortada: en las listas reales hay más recetas e ingredientes. Los productos aparecen **dentro de cada ingrediente**
(el mismo producto se repite en cada receta que lo usa).

```json
{
  "session_id": "demo",
  "mensaje": "¡Listo! Plan para 2 persona(s). lunes: Pollo al horno con patatas y Ensalada de pasta; martes: Lasaña boloñesa (lista para comer).",
  "mensaje_conclusion": "¿Qué opinas?",   // opcional: texto que va DESPUÉS del plan
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
            { "unidades": 1.0,  "producto": { "id": "2787", "nombre": "Muslos de pollo", "precio": 4.5, "...": "..." } },
            { "unidades": 0.25, "producto": { "id": "4640", "nombre": "Aceite de oliva 1º Hacendado", "precio": 3.9, "...": "..." } }
          ],
          "instrucciones": "Precalienta el horno a 200°C. Coloca el pollo y las patatas en una bandeja, sazona con sal y pimienta, y hornea durante 45 minutos o hasta que estén dorados y cocidos.",
          "precio_estimado": 7.2
        },
        {
          "id": "r2",
          "nombre": "Ensalada de pasta",
          "tipo": "cocinar",
          "momento": "cena",
          "raciones": 2,
          "ingredientes": [
            { "unidades": 0.25, "producto": { "id": "4640", "nombre": "Aceite de oliva 1º Hacendado", "precio": 3.9, "...": "..." } }
          ],
          "instrucciones": "...",
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
            { "unidades": 2.0, "producto": { "id": "4487", "nombre": "Lasaña boloñesa", "precio": 2.75, "...": "..." } }
          ],
          "precio_estimado": 5.5
        }
      ]
    },
    "extras": [
      { "unidades": 1, "producto": { "id": "3314", "nombre": "Leche entera", "precio": 0.89, "...": "..." } }
    ],
    "en_casa": ["pimienta", "sal"]
  }
}
```

Forma completa de un `producto` (es la que antes iba en `carrito.lineas[].producto`):

```json
{
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
}
```

Campos relevantes del plan:
- **(CAMBIA)** `dias`: **lista de recetas por día** (`tipo`: `cocinar` | `listo_para_comer`). Cada receta puede llevar un
  `momento` opcional (`"comida"` | `"cena"`); el frontend de momento lo ignora.
  Un `listo_para_comer` es una receta con **un solo ingrediente** (el propio producto).
- **(CAMBIA)** `ingredientes`: `{unidades, producto}`. Ya no hay `producto_id` suelto ni `carrito`: el producto
  va completo dentro de cada ingrediente. `precio` es el precio de **un envase**.
- **(NUEVO)** `instrucciones`: texto de preparación de la receta (opcional en `listo_para_comer`).
- **(CAMBIA)** `extras`: **productos que el usuario necesita pero que no son de ninguna receta** (leche, café…),
  con la misma forma que un ingrediente (`{unidades, producto}`). Llevan precio y entran en la lista de la compra.
  No dependen de los días: si el usuario desmarca un día, los extras se quedan. Se añaden desde el chat
  ("añade leche") o desde la búsqueda.
- **(NUEVO)** `en_casa`: lo que se supone que ya hay en casa (sal, agua…). Es lo que antes se llamaba `extras`:
  solo texto, sin precio ni lista de la compra. A nivel de plan; en cada receta es opcional.
- **(CAMBIA)** El plan **no** lleva `comensales`, `presupuesto`, `total` ni `dentro_presupuesto`. El backend sigue manejando
  comensales y presupuesto dentro de la sesión, pero no los devuelve. Los precios y totales los calcula solo el frontend,
  así que **`mensaje` no debe citar totales** (podrían no coincidir con lo que ve el usuario).
- Las recetas **no tienen imagen propia**: el frontend usa el `thumbnail` del primer ingrediente.
- `id` del plan: identifica el plan; cambia cada vez que cambia su contenido (nuevo plan o plato sustituido).

### (NUEVO) Unidades y lista de la compra

Ya no hay `carrito`: **el frontend calcula la lista de la compra** a partir del plan, para poder recalcularla al instante
cuando el usuario desmarca un día.

- En `ingredientes` y `extras`, `unidades` puede ser **fraccionaria**: es la fracción de un envase que gasta esa receta
  (0.25 = un cuarto del aceite). Así dos recetas que comparten el aceite no obligan a comprar dos envases.
- La lista de la compra, en **envases enteros**, es:

  ```
  envases(producto) = ceil( suma de unidades de ese producto en todas las recetas y extras seleccionados )
  subtotal(producto) = envases × producto.precio
  total = suma de subtotales
  ```

  Con una pequeña tolerancia (`ceil(x - 1e-9)`) para que `2.0000000001` no se convierta en 3.
- Los totales se calculan **solo en el frontend** (en la lista de la compra y en el resumen del plan). El backend no los devuelve;
  internamente puede usar la misma regla para ajustar el plan a un presupuesto.

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
  "plan_id": "af91ab62",            // opcional
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

- `unidades` aquí son **envases enteros** ya editados por el usuario (pueden diferir de lo que salía del plan).
- Si viene `mensaje`, el frontend lo muestra como burbuja de Merche.
- El frontend guarda además la lista en su propia pestaña "Listas" (en local); el backend solo necesita registrarla.

## Otros endpoints

| Método | Ruta | Uso |
|---|---|---|
| POST | `/plan` | Generar plan sin chat: `{comensales, presupuesto?, dias[], restricciones?}` → plan |
| POST | `/lista` | **(NUEVO)** Guardar la lista final del usuario (ver arriba) |
| GET | `/productos?q=&categoria=&precio_max=&limite=` | Buscar en el catálogo real (el frontend usa este para la búsqueda) |
| GET | `/productos/{id}` | Detalle de producto |
| GET | `/categorias` | Árbol de categorías |
| GET | `/catalogo` | Lista de recetas disponibles |
| GET | `/dashboard` | Métricas: planes, sustituciones, gasto medio, recetas más usadas, ahorro vs presupuesto |
| GET | `/health` | Comprobación |

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
Los precios y las cantidades los calcula siempre el código con el catálogo real; el LLM no debe inventarlos.
