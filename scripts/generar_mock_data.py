"""Regenera app/data/mock_data.json (recetas mock con ingredientes del catálogo real).

Las `unidades` de cada ingrediente son para `raciones` (2) personas; el planificador las escala.
`etiquetas` sirve para filtrar dietas y alergias: carne, pescado, gluten, lactosa, huevo, soja.
"""
import json
from pathlib import Path


def ing(producto_id, unidades=1):
    return {"producto_id": producto_id, "unidades": unidades}


def receta(id, nombre, tipo, ingredientes, instrucciones=None, en_casa=(), etiquetas=(), raciones=2):
    return {
        "id": id,
        "nombre": nombre,
        "tipo": tipo,
        "raciones": raciones,
        "ingredientes": ingredientes,
        "instrucciones": instrucciones,
        "en_casa": list(en_casa),
        "etiquetas": list(etiquetas),
    }


def listo(id, nombre, ingredientes, etiquetas=()):
    return receta(id, nombre, "listo_para_comer", ingredientes, None, (), etiquetas)


RECETAS = [
    receta("r1", "Pollo al horno con patatas", "cocinar",
           [ing("2787"), ing("69386"), ing("69312", 0.5), ing("4640", 0.05)],
           "Precalienta el horno a 200 °C. Pon el pollo, las patatas y el pimiento en una bandeja con un chorrito de aceite, sazona y hornea 45 minutos hasta que esté dorado.",
           ["sal", "pimienta"], ["carne"]),
    receta("r2", "Espaguetis con tomate y queso", "cocinar",
           [ing("35904", 0.5), ing("17108"), ing("22216", 0.3), ing("4640", 0.03)],
           "Cuece los espaguetis en agua con sal según el envase. Calienta el tomate frito, mézclalo con la pasta escurrida y gratina con el queso rallado.",
           ["sal", "agua"], ["gluten", "lactosa"]),
    receta("r3", "Macarrones con carne", "cocinar",
           [ing("6250", 0.5), ing("2869", 0.5), ing("17108"), ing("22216", 0.2)],
           "Cuece los macarrones. Sofríe la carne picada, añade el tomate frito y cocina 10 minutos. Mezcla con la pasta y espolvorea queso rallado.",
           ["sal", "agua"], ["carne", "gluten", "lactosa"]),
    receta("r4", "Lentejas estofadas", "cocinar",
           [ing("26030", 2), ing("69586", 0.5), ing("69310", 0.5), ing("4640", 0.03)],
           "Sofríe la zanahoria y el pimiento troceados, añade las lentejas cocidas con un poco de agua y pimentón, y cuece 15 minutos.",
           ["sal", "agua", "pimentón"], []),
    receta("r5", "Garbanzos con espinacas", "cocinar",
           [ing("26029", 2), ing("35781"), ing("61251", 0.3), ing("4640", 0.03)],
           "Sofríe el ajo con pimentón, añade las espinacas congeladas y, cuando se deshagan, los garbanzos escurridos. Cocina 10 minutos.",
           ["sal", "agua", "pimentón"], []),
    receta("r6", "Tortilla de patata", "cocinar",
           [ing("31310"), ing("69386"), ing("69089", 0.3), ing("4640", 0.1)],
           "Pocha las patatas y la cebolla en aceite hasta que estén tiernas. Mézclalas con los huevos batidos y cuaja la tortilla por ambos lados.",
           ["sal"], ["huevo"]),
    receta("r7", "Ensalada completa con atún", "cocinar",
           [ing("68130"), ing("60369", 2), ing("12911"), ing("31010")],
           "Trocea la lechuga y el tomate, añade el atún escurrido y el huevo cocido en cuartos. Aliña con aceite, vinagre y sal.",
           ["sal", "vinagre"], ["pescado", "huevo"]),
    receta("r8", "Merluza con calabacín y patata", "cocinar",
           [ing("24324"), ing("69338", 2), ing("69386", 0.5), ing("4640", 0.03)],
           "Descongela la merluza. Cuece las patatas en rodajas, saltea el calabacín y cocina la merluza a la plancha 3 minutos por lado. Sirve con limón.",
           ["sal", "limón"], ["pescado"]),
    receta("r9", "Hamburguesas con ensalada", "cocinar",
           [ing("2872"), ing("13803"), ing("68130", 0.5), ing("60369")],
           "Haz las hamburguesas a la plancha 4 minutos por lado. Monta en el pan con lechuga y tomate.",
           ["sal", "pimienta"], ["carne", "gluten"]),
    receta("r10", "Arroz con pollo", "cocinar",
           [ing("22279", 2), ing("2777"), ing("69310")],
           "Dora el pollo troceado con el pimiento en una sartén 12 minutos. Añade el arroz cocido y saltea 3 minutos más.",
           ["sal", "agua"], ["carne"]),
    receta("r11", "Crema de calabacín con pan", "cocinar",
           [ing("35870", 2), ing("12049.1", 0.5), ing("22216", 0.2)],
           "Calienta la crema 5 minutos, sirve con queso rallado por encima y acompaña con pan.",
           ["sal", "pimienta"], ["gluten", "lactosa"]),
    receta("r12", "Tallarines salteados con verduras", "cocinar",
           [ing("6246", 0.5), ing("69586", 0.5), ing("69312"), ing("4640", 0.03)],
           "Cuece los tallarines. Saltea la zanahoria y el pimiento en tiras con un poco de aceite, añade la pasta y salsa de soja.",
           ["sal", "salsa de soja"], ["gluten", "soja"]),
    listo("l1", "Lasaña boloñesa (lista para comer)", [ing("4487", 2)], ["carne", "gluten", "lactosa"]),
    listo("l2", "Pollo asado Hacendado", [ing("13706")], ["carne"]),
    listo("l3", "Ensalada de pasta (lista para comer)", [ing("13241", 2)], ["gluten"]),
    listo("l4", "Pizza carnívora", [ing("12083")], ["carne", "gluten", "lactosa"]),
    listo("l5", "Tortilla de patata con cebolla (lista para comer)", [ing("60089")], ["huevo"]),
    listo("l6", "Salmón con verduras (listo para comer)", [ing("13243", 2)], ["pescado"]),
    listo("l7", "Gazpacho y pan", [ing("39900"), ing("12049.1", 0.5)], ["gluten"]),
]

if __name__ == "__main__":
    destino = Path(__file__).parent.parent / "app" / "data" / "mock_data.json"
    destino.write_text(json.dumps({"recetas": RECETAS}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(RECETAS)} recetas -> {destino}")
