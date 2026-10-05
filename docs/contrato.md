# Contrato de la API (para el frontend)

Especificación completa y siempre al día: `http://localhost:8000/docs` (Swagger) y `/openapi.json`
(se puede generar un cliente tipado a partir de ahí). Este documento resume lo esencial.

> **Contrato v3: ya implementado en el backend.** Lo marcado como **(NUEVO)** o **(CAMBIA)** es lo pactado con
> el equipo de interfaz (respecto a la v1). Resumen de los cambios:
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
> 9. **(CAMBIA)** Se elimina `/sustituir`: cambiar un plato se hace por chat ("cambia el martes"). Con él se retiran también
>    `/plan`, `/catalogo`, `/categorias`, `/dashboard` y `/productos/{id}`: el frontend solo necesita los endpoints de la tabla "Endpoints".
> 10. **(NUEVO)** `POST /lista`: el usuario guarda su lista final.
> 11. **(NUEVO)** Chips de respuesta rápida (`sugerencias`), feedback iniciado por Merche (`feedback`) y `GET /bienvenida` (ver abajo). `POST /feedback`: valoración 👍/👎.

## Idea general

- **El historial y el estado de la conversación los guarda el backend**, por `session_id`, en memoria y en disco
  (`.estado/<session_id>.json`), así que sobreviven a un reinicio del servidor. El frontend solo manda el mensaje nuevo
  (y el `plan`, si el usuario lo ha editado). Ver "Qué recuerda el backend".
- **(CAMBIA) El plan solo viene cuando es relevante.** Si la respuesta no trae `plan` (ausente o `null`), significa
  **"nada ha cambiado"**: el frontend conserva el último plan. Si trae `plan`, es el plan completo y **sustituye** al anterior.
  Decidir cuándo incluirlo (nuevo plan, cambio de plato, nuevo presupuesto…) es cosa del backend; una respuesta
  tipo "de nada" o una pregunta aclaratoria no lleva plan.
- El `session_id` lo puede inventar el frontend (cualquier string); si no se envía, el backend crea uno y lo devuelve.
  **(NUEVO)** El frontend genera un `session_id` nuevo cada vez que el usuario empieza una conversación de cero
  (botón "volver"), para que el backend no arrastre contexto que el usuario cree borrado.
- Si el servidor no encuentra la sesión (por ejemplo, otra máquina o `.estado/` borrado), el frontend puede reenviar el `plan`
  que ya tiene en su siguiente `/chat` (campo `plan` de la petición) o empezar de nuevo.
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

Gemini (con reglas simples como plan B si falla) clasifica el mensaje. Entiende: personas, presupuesto en €, días ("lunes a viernes",
"fin de semana", "toda la semana"), comida y/o cena, dietas y alergias (vegetariano, sin gluten, sin lactosa...), "el martes no cocino",
"cambia el lunes", "añade leche" / "quita la leche", **platos concretos** ("quiero pollo al curry", "lentejas el martes", "pizza esta noche"),
"para mí" / "solo yo" (1 persona), **"hoy", "mañana" y "esta noche"** (se convierten al nombre del día), y charla en general.
Si pide un plato que no existe, lo dice y propone el más parecido; si el plato choca con su dieta, también lo avisa.
**Negaciones**: "no quiero pollo al curry", "nada de pizza", "sin cebolla" (por ingrediente), "no me apetecen las lentejas" se rechazan:
se quitan del plan (sustituyéndolos) y no vuelven a salir. También entiende "no somos 4, somos 3", "ya no soy vegetariano",
"no quiero cocinar el martes", "no quiero cenas" y "no tengo presupuesto". Lo rechazado nunca se toma como petición.

**Cambiar platos**: "cambia el lunes", "cambia el lunes y el martes", "cambia todo", "cambia las hamburguesas" (por nombre),
"cambia la pasta por arroz" (por ingrediente), "cámbiame el martes por lentejas", "cambia el jueves por algo más ligero",
"cambia el viernes por algo vegetariano". Lo que va tras "por" elige el plato nuevo **solo para ese hueco** (no cambia la dieta
guardada). Si no hay nada que encaje, lo dice y el plan no cambia. El resto de días se queda igual.

**Ideas sin plan**: "¿qué puedo cenar esta noche con pasta?", "el martes no me apetece cocinar, ¿qué me recomiendas?",
"algo especial para el domingo", "tengo pollo y arroz, ¿qué hago?" → Merche propone hasta 3 recetas (según ingredientes, estilo,
dieta y gustos) **sin crear ni cambiar el plan**, con chips "Quiero X esta noche/el martes" para elegir. Merche no da por hecho que
el usuario quiere un plan semanal: un plato suelto ("quiero pollo al curry" + "somos 2") crea un plan **solo para ese día**.
Un menú de varios días ("¿me propones un menú ligero para la semana?") sí es un plan, con su estilo.

**Preguntas** ("¿qué como el martes?", "¿cuál es el menú?", "¿cómo se hace?", "¿y qué lleva?", "¿cuánto me va a costar?",
"¿qué tengo que tener en casa?", "¿para cuántos era?"): se responden con los datos guardados de la sesión y **nunca traen `plan`**
(una pregunta no cambia nada). Merche recuerda de qué plato se hablaba, así que "¿y qué lleva?" funciona sin repetir el nombre.
Lo concreto lo contesta el código (exacto); las preguntas abiertas ("¿esto es sano?") las contesta Gemini con el plan completo en el contexto. Los datos se acumulan durante la sesión
(por ejemplo, "mejor 25 euros" regenera el plan con los mismos comensales y la misma dieta).
Si faltan los comensales, la respuesta **no lleva `plan`** y `mensaje` pregunta por ellos.

Las respuestas **sin `plan`** (no hay cambio) son: preguntas aclaratorias, charla, peticiones rechazadas
(ver "Reglas de precio y viabilidad") y cualquier cosa que no se haya podido hacer. Siempre llevan `mensaje`.

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
- **(NUEVO)** `etiquetas`: lista de `carne`, `pescado`, `gluten`, `lactosa`, `huevo`, `soja` presentes en la receta (el frontend puede ignorarla o mostrarla como aviso de alérgenos).
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
  "mensaje": "Lista guardada. ¿En qué tienda vas a hacer la compra?",   // opcional
  "sugerencias": ["Paterna", "Alboraya"]                                // opcional: chips de tienda
}
```

- **Tienda (solo informativa):** el frontend muestra las `sugerencias` como chips. La elección se guarda solo en la lista local
  (pestaña "Listas") y Merche contesta en local; **no se envía a ningún sitio**.

- `unidades` aquí son **envases enteros** ya editados por el usuario (pueden diferir de lo que salía del plan).
- Si viene `mensaje`, el frontend lo muestra como burbuja de Merche.
- El frontend guarda además la lista en su propia pestaña "Listas" (en local); el backend solo necesita registrarla.

## Endpoints

Estos son todos los que necesita el frontend:

| Método | Ruta | Uso |
|---|---|---|
| POST | `/chat` | **El principal.** Mensaje del usuario -> texto de Merche (+ `plan` si cambia) |
| GET | `/chat/{session_id}` | Recargar la página: historial y plan vigente |
| POST | `/lista` | Guardar la lista final del usuario (ver arriba) |
| GET | `/bienvenida?session_id=` | **(NUEVO)** Primer mensaje de Merche al abrir la conversación (ver abajo) |
| POST | `/feedback` | **(NUEVO)** Valoración 👍/👎 (ver abajo) |
| POST | `/voz` | **(NUEVO)** Audio -> texto con Gemini (ver abajo) |
| GET | `/productos?q=&categoria=&precio_max=&limite=` | Buscar en el catálogo real (búsqueda de productos del frontend) |
| GET | `/health` | Comprobación |

Retirados respecto a la v1: `/plan`, `/sustituir`, `/catalogo`, `/categorias`, `/dashboard`, `/productos/{id}`.

## Errores

`404 {"detail": "..."}` (no existe) y `422 {"detail": ...}` (datos no válidos: comensales ≤ 0, días vacíos o repetidos, mensaje vacío...).
Las respuestas del chat que no entienden algo **no** son errores: vienen con 200 y un `mensaje` explicativo.
El frontend ignora campos desconocidos, así que se pueden añadir campos sin avisar.

## (NUEVO) Chips de respuesta rápida: `sugerencias`

`/chat` y `/bienvenida` pueden devolver `sugerencias: string[]` (**máx. 4**, cortos). Son botones: **al pulsar uno, el frontend lo envía tal cual
como `mensaje` a `/chat`** (con el mismo `session_id`). Los genera el backend según lo que acaba de pasar; ejemplos:
`["Somos 2", "Somos 4", "Para 1 persona"]` (al preguntar comensales), `["Cambia el lunes", "Quiero comida y cena", "Soy vegetariano", "Añade leche"]`
(tras un plan), `["Mejor 50 euros", "Para 1 persona", "Solo de lunes a miércoles"]` (tras un presupuesto imposible).
Si el campo no viene, no hay chips; el frontend los quita cuando el usuario escribe o pulsa otro mensaje.

## (NUEVO) Feedback iniciado por Merche

Después de que el usuario **guarde una lista** (`/lista`), Merche puede preguntar qué tal salió un plato. Para ello `/chat`, `/bienvenida` y `/feedback`
pueden devolver un campo `feedback`:

```json
{ "mensaje": "¡Hola otra vez! ¿Qué tal salió «Pollo al horno con patatas»?",
  "feedback": { "tipo": "receta", "id": "r1", "nombre": "Pollo al horno con patatas", "imagen": "https://..." } }
```

El frontend muestra la pregunta (`mensaje`) con la tarjeta del plato y los botones 👍/👎, y responde con `POST /feedback`.

### GET /bienvenida?session_id=...

Se llama **al abrir la conversación** (o la pestaña del chat). Devuelve la misma forma que `/chat` (`session_id`, `mensaje`, `sugerencias?`, `feedback?`; sin `plan`)
y se guarda en el historial (no se duplica si se llama dos veces seguidas). Según el estado de la sesión:

| Estado | Respuesta |
|---|---|
| Sesión nueva | Saludo + chips `["Somos 2", "Somos 4", "Para 1 persona"]` |
| Plan en marcha, sin lista guardada | "Tienes un plan en marcha..." + chips |
| Lista guardada y platos por valorar | Pregunta de feedback con `feedback` (el primer plato sin valorar) |
| Lista guardada y todo valorado | Agradecimiento + chip "Hazme un plan para la semana" |

Sin `session_id`, crea una sesión nueva y devuelve su id.

### POST /feedback

Petición: `{ "session_id", "sujeto": { "tipo": "receta" | "producto", "id": "r1" }, "valor": "positivo" | "negativo", "motivo"?: "Estaba soso" }`

Respuesta: `{ "mensaje"?: "...", "sugerencias"?: ["Estaba soso", "Muy caro", "No me gustó"], "feedback"?: { ... } }`

- 👍: `mensaje` de agradecimiento; si quedan platos por valorar, trae `feedback` con el siguiente (y el `mensaje` ya lo pregunta).
- 👎 **sin `motivo`**: `mensaje` "¿Qué falló?" + `sugerencias` (chips). Al pulsar uno, el frontend reenvía el mismo POST con `motivo`; entonces Merche
  agradece y sigue con el siguiente plato, si lo hay.
- Una receta con 👎 **no se vuelve a proponer** en esa sesión.
- **Máximo 3 platos por lista guardada**, para no agobiar; después `feedback` deja de venir.
- 404 si la sesión no existe.

### Qué aprende Merche del feedback

- Al guardar la lista, el backend apunta **qué platos y productos se compraron** (los que tienen algún producto en `lineas`):
  solo pregunta por esos. Pregunta por recetas y también por los productos sueltos (`extras`, `tipo: "producto"`).
- 👍 receta: vuelve a salir en los siguientes planes. 👎 receta: no vuelve a salir (salvo que el usuario la pida).
- 👍 producto: se elige ese al pedir "añade X". 👎 producto: no se vuelve a elegir.
- Motivos del 👎 (`sugerencias`: "Estaba soso", "Muy caro", "Mucho trabajo", "No me gustó"): "Muy caro" hace que los planes
  prioricen platos baratos; "Mucho trabajo", platos con menos ingredientes.
- "¿Qué tengo apuntado?" en el chat devuelve también estos gustos.

### (NUEVO) "Volver" conserva la memoria: `sesion_anterior`

Al empezar de cero, el frontend crea un `session_id` nuevo y envía **una vez** el anterior como `sesion_anterior`
(en el cuerpo de `/chat` o como parámetro de `/bienvenida`). La sesión nueva empieza con la conversación, el plan y los datos
de la semana vacíos, pero **hereda la memoria del usuario**: listas guardadas (y sus preguntas pendientes), valoraciones,
platos que le gustan o no, productos preferidos, preferencias de precio y esfuerzo, y su dieta (`excluir`).

## (NUEVO) Comentarios para Mercadona: `enviado`

Si el usuario comenta algo de un producto o de la compra ("las latas de atún vienen con demasiado aceite", "el pan llegó duro",
"echo de menos el tofu ahumado"), `/chat` responde **sin `plan`** y con:

```json
{
  "mensaje": "Gracias por contárnoslo. Se lo he hecho llegar a Mercadona.",
  "enviado": { "destinatario": "Mercadona", "puntos": ["Las latas de atún vienen con demasiado aceite"] },
  "mensaje_conclusion": "¿Preparamos lo de la semana que viene?",
  "sugerencias": ["Hazme un plan para la semana", "Ahora no, gracias"]
}
```

- El frontend pinta `enviado` como una tarjeta "Enviado a Mercadona" con los `puntos` (lo esencial del comentario).
- No se envía a ningún sitio real: se guarda en la sesión (`opiniones`).

## (NUEVO) Pestaña "Listas"

Las listas guardadas con "Añadir en una nueva lista" (con su tienda, productos, envases y total) y los productos sueltos
añadidos desde la búsqueda se guardan en el navegador (`localStorage`) y se ven en la pestaña "Listas". El backend solo
registra qué se compró para preguntar luego "¿qué tal fue la compra?" (al abrir el siguiente chat, con `/bienvenida`).

## (NUEVO) Mensajes de voz: POST /voz

El usuario pulsa el micrófono de la barra (aparece cuando está vacía), habla y vuelve a pulsar. La interfaz convierte la
grabación a **WAV 16 kHz mono** (Chrome graba WebM/Opus, que Gemini no acepta) y la envía:

```
POST /voz            Content-Type: audio/wav        (cuerpo: el audio tal cual; también acepta MP3, OGG, FLAC, AAC)
-> 200 { "texto": "Somos dos y el martes no me apetece cocinar" }
```

Ese texto se envía después a `/chat` como un mensaje escrito (misma ruta, mismo historial, mismas reglas).

| Respuesta | Cuándo |
|---|---|
| 200 `{texto}` | Transcrito (Gemini, ~2 s) |
| 422 | Sin audio, formato no admitido, demasiado largo (> 10 MB) o "No te he entendido. ¿Puedes repetirlo?" |
| 503 | Gemini no disponible: "Ahora mismo no puedo escuchar audios. Escríbemelo, por favor." (la voz no tiene plan B) |

En Swagger (`/docs`) se puede probar subiendo un `.wav`.

## Reglas de precio y viabilidad

El backend **no concede lo imposible**. Estas comprobaciones las hace el código (no el LLM) antes de devolver un plan:

| Caso | Qué pasa |
|---|---|
| El presupuesto no alcanza ni para el plan más barato posible | Sin `plan`; `mensaje` dice que no puede ser, cuánto cuesta aproximadamente lo más barato y qué se puede recortar. No se guarda ese presupuesto, pero sí se recuerda lo demás (personas, dieta, días). |
| Más de 12 comensales, presupuesto <= 0, día que no existe | Sin `plan`; `mensaje` explica el límite. |
| Dieta/alergias que no dejan ningún plato posible | Sin `plan`; `mensaje` lo explica. |
| "Cambia el martes" y no hay otro plato que cumpla presupuesto y dieta | Sin `plan`; el plan no cambia. |
| "Añade leche" y con ello se pasa del presupuesto | Se añade, y `mensaje` lo avisa ("te pasas del presupuesto"). |
| Producto que no existe en el catálogo | Sin `plan`; `mensaje` dice que no lo encuentra. |

- Cuando hay presupuesto, el planificador **abarata el plan** (cambia platos por otros más baratos) hasta que cabe; solo si ni así cabe, lo rechaza.
- **Excepción a "`mensaje` no cita totales":** el rechazo por presupuesto sí menciona el importe mínimo aproximado, porque es la información útil.
  Usa la misma regla de envases enteros que el frontend, así que coincide salvo que el usuario haya editado el plan.
- Los precios son los del catálogo de Mercadona descargado (se actualiza semanalmente); no son precios en tiempo real.
- Cuando algo falla, **el texto lo escribe el código** y no el LLM, para que lo que se le dice al usuario sea exacto.

## Qué recuerda el backend (estado de la sesión)

Cada `session_id` tiene un estado que se actualiza en cada mensaje y se guarda en `.estado/<session_id>.json`.
Es lo que permite que "mejor 25 euros" o "cambia el lunes" funcionen sin repetir todo:

| Bloque | Contenido | Se actualiza cuando... |
|---|---|---|
| Conversación | `mensajes` (usuario/asistente) | cada turno |
| Preferencias | `comensales`, `presupuesto`, `dias`, `momentos` (comida/cena), `sin_cocinar` (días), `excluir` (etiquetas de dieta/alergia), `rechazadas` (recetas con 👎) | el usuario lo dice o da feedback |
| Platos pedidos | `fijos`: platos que el usuario pidió por nombre, con su día | "quiero X"; se respetan al rehacer el plan (p. ej. "mejor 40 euros") hasta que pide cambiar ese día |
| Plan | `plan` vigente | se genera o cambia un plato/extra; **si el frontend envía `plan`, manda sobre el guardado** |
| Listas | listas guardadas con `/lista` | el usuario pulsa "guardar" |
| Feedback | valoraciones de `/feedback` | el usuario valora |

Clasificación de lo que dice el usuario: cada mensaje se convierte en una acción: `plan` (datos o plan nuevo), `pedir_plato`, `cambiar_plato`,
`anadir_extra`, `quitar_extra` o `charla`, más los datos que traiga (personas, presupuesto, días, momentos, `excluir`...).
`excluir` usa etiquetas fijas que llevan las recetas: `carne`, `pescado`, `gluten`, `lactosa`, `huevo`, `soja`
(vegetariano = carne + pescado; vegano = carne + pescado + huevo + lactosa). Cada receta del plan trae sus `etiquetas`.

## Cómo funciona el agente (Gemini)

Un turno de `/chat`:

```
mensaje -> Gemini clasifica (UNA llamada) -> el código ejecuta la acción y comprueba la viabilidad
        -> se actualiza el estado de la sesión -> texto de la respuesta (+ plan si cambió)
```

- Gemini solo **entiende** el mensaje (acción + datos) y propone el texto de la respuesta. Qué platos, cantidades y precios hay lo decide
  siempre el código con el catálogo real. Si el texto del LLM cita precios, se descarta; si la acción falla, el texto lo pone el código.
- **Una sola llamada por mensaje**: la clave gratuita permite unas 5 peticiones por minuto. Si Gemini falla, tarda más de 15 s o se queda
  sin cuota, el chat **no se cae**: se usa un intérprete por reglas y plantillas (`app/logic/interprete.py`, `mensajes.py`).
- Las instrucciones del LLM están en `app/logic/agente.py` (`SISTEMA_INTERPRETE`); la conexión, en `app/logic/llm.py`.
- Configuración en `.env`: `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` y `LLM_MODELOS_RESERVA` (por defecto
  `gemini-3.5-flash-lite,gemini-3.7-flash`): si el modelo principal está saturado (503), sin cuota (429) o no existe, se prueba el siguiente
  antes de caer al plan B. Sin clave, todo funciona con el plan B. El log `[merche]` de la terminal dice qué modelo respondió en cada mensaje.

## Probar y conectar

```bash
# Backend (puerto 8000)
python -m venv venv
venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload
pytest                      # 184 tests, sin red ni Gemini (siempre simulado)

# Probar a mano: Swagger en http://localhost:8000/docs, o con curl:
curl -X POST localhost:8000/chat -H "content-type: application/json" -d '{"session_id":"demo","mensaje":"Somos 2, 60 euros y el martes no cocino"}'
```

- **Frontend:** llama a `http://localhost:8000` (CORS abierto). Mientras no haya backend se puede trabajar con las respuestas de ejemplo de este documento.
- El primer arranque en frío puede tardar unos segundos (carga el catálogo). Si hay errores raros con la sesión, borra `.estado/`.

### Ejemplo de memoria entre mensajes

```
> Quiero pollo al curry          < ¡Apuntado: Pollo al curry con arroz basmati! ¿Para cuántas personas y qué día?   (sin plan; chips: "Solo para mí, hoy", ...)
> Es solo para mí y para hoy     < plan de 1 persona: hoy, pollo al curry
> Y mañana algo de lentejas      < plan: hoy pollo al curry + mañana lentejas (no se pierde lo anterior)
```
