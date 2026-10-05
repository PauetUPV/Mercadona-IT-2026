"""Opiniones inventadas para enseñar el informe de Mercadona (un solo usuario no da volumen en una demo).

    PYTHONPATH=. python scripts/generar_opiniones_demo.py

Las añade a `.estado/opiniones.jsonl`; después, `GET /informe`. Para empezar de cero, borra ese fichero
y `.estado/opiniones_analisis.jsonl`.
"""
import random
from datetime import datetime, timedelta

from app.logic import opiniones

TIENDAS = ["Valencia - Ruzafa", "Valencia - Benimaclet", "Paterna", "Alboraya"]

# (texto, veces, tiendas en las que pasa; None = cualquiera)
COMENTARIOS = [
    ("Las latas de atún vienen con demasiado aceite", 6, None),
    ("El atún en lata trae muchísimo aceite, casi más que atún", 3, None),
    ("La pechuga de pollo olía mal al abrirla, y eso que no estaba caducada", 4, ["Paterna"]),
    ("El pollo estaba en mal estado", 2, ["Paterna"]),
    ("No había hummus ningún día de esta semana", 3, ["Alboraya"]),
    ("La bolsa de espinacas es demasiado grande para una persona, se me estropea la mitad", 3, None),
    ("Estaría bien que la lasaña lista para comer viniera también en tamaño individual", 2, None),
    ("El aceite de oliva ha subido mucho de precio", 2, None),
    ("Me encanta el pan de pueblo, está buenísimo", 3, None),
    ("En la receta de lentejas falta decir cuánto tiempo hay que cocerlas", 2, None),
    ("Los tomates estaban muy duros y sin sabor", 2, ["Valencia - Ruzafa", "Alboraya"]),
]


def main() -> None:
    azar = random.Random(2026)
    ahora = datetime.now()
    cliente = 0
    for texto, veces, tiendas in COMENTARIOS:
        for _ in range(veces):
            cliente += 1
            fecha = ahora - timedelta(days=azar.randint(0, 13), hours=azar.randint(0, 12))
            opiniones.registrar(
                f"demo-{cliente:02d}", texto=texto, tienda=azar.choice(tiendas or TIENDAS), fecha=fecha.isoformat(timespec="seconds")
            )
    print(f"{cliente} opiniones añadidas")


if __name__ == "__main__":
    main()
