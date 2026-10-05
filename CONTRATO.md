# Contrato Frontend ↔ Backend (borrador v0)

Un solo endpoint para todo lo de Merche. El frontend manda la entrada del usuario
más el historial; el backend responde con un mensaje, y opcionalmente un bloque
estructurado y chips de respuesta rápida.

> Búsqueda de productos: fuera de este contrato (el frontend la resuelve solo, por ahora).

## Reparto de responsabilidades

| Backend | Frontend |
|---|---|
| Entender el texto libre (días, comensales, presupuesto…) | Mostrar el mensaje y los bloques |
| Elegir recetas y productos **reales** del catálogo | Calcular la **lista de la compra** a partir del plan |
| Calcular las cantidades ya escaladas a `comensales` | Dejar al usuario editar (quitar, cantidad, marcar/desmarcar días) |
| Decidir cuándo pedir feedback y sobre qué | Guardar la lista y avisar al backend (`lista_guardada`) |

La lista de la compra **no la envía el backend**: el frontend la deriva del plan
(ingredientes de los días marcados + extras, sumando cantidades repetidas).

## `POST /chat`

### Petición

```json
{
  "entrada": { "texto": "comidas de lunes a jueves para 4, 90 €, el martes no cocino" },
  "historial": [
    { "autor": "merche", "texto": "¡Hola! …", "bloque": null },
    { "autor": "usuario", "texto": "…" }
  ]
}
```

- `historial`: últimos ~10 mensajes, del más antiguo al más reciente, **sin** la entrada actual.
  Cada mensaje de Merche incluye el `bloque` que envió (para que sepa qué plan propuso).
- `entrada` es **una** de estas cuatro:

| Entrada | Cuándo |
|---|---|
| `{ "texto": "…" }` | el usuario escribe |
| `{ "evento": { "tipo": "abrir" } }` | el usuario abre Merche con la conversación vacía (historial `[]`). El backend puede saludar o empezar con un feedback |
| `{ "evento": { "tipo": "feedback", "sujeto": { "tipo": "receta", "id": "r1" }, "valor": "positivo" } }` | tap 👍/👎 (`valor`: `"positivo"` \| `"negativo"`) |
| `{ "evento": { "tipo": "lista_guardada", "lista": [ { "producto_id": "2833", "cantidad": 2 } ] } }` | el usuario guarda su lista final |

### Respuesta (siempre la misma forma, también para eventos)

```json
{
  "mensaje": "¡Listo! Te he preparado el plan de la semana.",
  "bloque": null,
  "sugerencias": ["Cambia el martes", "Algo más barato"]
}
```

- `mensaje` (obligatorio): texto del chat.
- `bloque` (opcional, `null` o ausente = solo texto): un **Plan** o un **Feedback**, distinguidos por `tipo`.
- `sugerencias` (opcional): máx. 4 chips cortos. Al pulsar uno se envía como `entrada.texto`.

## Bloque `plan`

```json
{
  "tipo": "plan",
  "comensales": 4,
  "presupuesto": 90,
  "dias": [
    {
      "dia": "Lunes",
      "recetas": [
        {
          "id": "r1",
          "nombre": "Espaguetis a la carbonara",
          "tipo": "cocinar",
          "imagen": "https://…",
          "ingredientes": [
            { "producto": { "id": "p1", "nombre": "Espaguetis", "detalle": "Hacendado · 500 g", "precio": 0.95, "imagen": "https://…" }, "cantidad": 1 }
          ]
        }
      ]
    }
  ],
  "extras": [
    { "producto": { "id": "p9", "nombre": "Leche entera", "detalle": "Hacendado · 1 L", "precio": 0.89, "imagen": "https://…" }, "cantidad": 2 }
  ]
}
```

Reglas:

- `dias` puede ser `[]`: una petición del tipo "necesito ingredientes para una pasta" es un plan con solo `extras`.
- `dia`: etiqueta única dentro del plan ("Lunes"); varias `recetas` por día.
- `extras`: productos necesarios que no pertenecen a ninguna receta.
- `receta.tipo = "listo_para_comer"`: se modela como receta con **un solo ingrediente** (el propio producto), para que la lista funcione igual.
- `ingredientes[].cantidad`: unidades del producto ya escaladas a `comensales` (entero ≥ 1).
- **No hay `precio` ni `total`** en recetas ni en el plan: el frontend los calcula (`precio × cantidad`).
- Un plan nuevo **sustituye por completo** al anterior (también tras "cambia el martes"). El frontend conserva las ediciones del usuario (productos quitados, cantidades) para los productos que sigan existiendo.

### `Producto`

```json
{ "id": "2833", "nombre": "…", "detalle": "Bandeja · 600 g", "precio": 4.92, "imagen": "https://…" }
```

Siempre un producto **real** del catálogo. Mapeo desde el JSON del catálogo:
`id` ← `id` (como string), `nombre` ← `display_name`, `precio` ← `float(price_instructions.unit_price)`,
`imagen` ← `thumbnail`, `detalle` ← packaging + tamaño (ej. `"Bandeja · 600 g"`).

## Bloque `feedback`

```json
{
  "tipo": "feedback",
  "sujeto": { "tipo": "receta", "id": "r1", "nombre": "Espaguetis a la carbonara", "imagen": "https://…" }
}
```

- `sujeto.tipo`: `"receta"` o `"producto"`. El backend decide.
- La pregunta va en el `mensaje` ("¿Qué tal salió la carbonara?"); el bloque pone los botones 👍👎.
- La respuesta del usuario vuelve como evento `feedback`; el backend puede contestar con texto y `sugerencias` (ej. "Estaba soso", "Muy caro").

## Errores

Cualquier respuesta no 2xx, timeout (el frontend corta a los 30 s) o JSON inválido muestra
"Merche no ha podido responder, inténtalo de nuevo". El frontend ignora campos desconocidos.

## Abierto

- `presupuesto` y `comensales` ¿siempre rellenos o pueden ser `null`?
- Identidad de usuario: de momento un usuario de demo fijo (sin login).
