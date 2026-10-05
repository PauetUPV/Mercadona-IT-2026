"""Regenera app/data/mock_data.json (recetas mock con ingredientes del catálogo real)."""
import json
from pathlib import Path


def ing(producto_id, unidades=1):
    return {"producto_id": producto_id, "unidades": unidades}


def receta(id, nombre, tipo, ingredientes, extras=(), raciones=2):
    return {
        "id": id,
        "nombre": nombre,
        "tipo": tipo,
        "raciones": raciones,
        "ingredientes": ingredientes,
        "extras": list(extras),
    }


RECETAS = [
    receta("r1", "Pollo al horno con patatas", "cocinar", [ing("2787"), ing("69386"), ing("69312", 0.5), ing("4640", 0.05)], extras=["sal", "pimienta"]),
    receta("r2", "Espaguetis con tomate y queso", "cocinar", [ing("35904", 0.5), ing("17108"), ing("22216", 0.3), ing("4640", 0.03)], extras=["sal", "agua"]),
    receta("r3", "Macarrones con carne", "cocinar", [ing("6250", 0.5), ing("2869", 0.5), ing("17108"), ing("22216", 0.2)], extras=["sal", "agua"]),
    receta("r4", "Lentejas estofadas", "cocinar", [ing("26030", 2), ing("69586", 0.5), ing("69310", 0.5), ing("4640", 0.03)], extras=["sal", "agua", "pimentón"]),
    receta("r5", "Garbanzos con espinacas", "cocinar", [ing("26029", 2), ing("35781"), ing("61251", 0.3), ing("4640", 0.03)], extras=["sal", "agua", "pimentón"]),
    receta("r6", "Tortilla de patata", "cocinar", [ing("31310"), ing("69386"), ing("69089", 0.3), ing("4640", 0.1)], extras=["sal"]),
    receta("r7", "Ensalada completa con atún", "cocinar", [ing("68130"), ing("60369", 2), ing("12911"), ing("31010")], extras=["sal", "vinagre"]),
    receta("r8", "Merluza con calabacín y patata", "cocinar", [ing("24324"), ing("69338", 2), ing("69386", 0.5), ing("4640", 0.03)], extras=["sal", "limón"]),
    receta("r9", "Hamburguesas con ensalada", "cocinar", [ing("2872"), ing("13803"), ing("68130", 0.5), ing("60369")], extras=["sal", "pimienta"]),
    receta("r10", "Arroz con pollo", "cocinar", [ing("22279", 2), ing("2777"), ing("69310")], extras=["sal", "agua"]),
    receta("r11", "Crema de calabacín con pan", "cocinar", [ing("35870", 2), ing("12049.1", 0.5), ing("22216", 0.2)], extras=["sal", "pimienta"]),
    receta("r12", "Tallarines salteados con verduras", "cocinar", [ing("6246", 0.5), ing("69586", 0.5), ing("69312"), ing("4640", 0.03)], extras=["sal", "salsa de soja"]),
    receta("l1", "Lasaña boloñesa (lista para comer)", "listo_para_comer", [ing("4487", 2)]),
    receta("l2", "Pollo asado Hacendado", "listo_para_comer", [ing("13706")]),
    receta("l3", "Ensalada de pasta (lista para comer)", "listo_para_comer", [ing("13241", 2)]),
    receta("l4", "Pizza carnívora", "listo_para_comer", [ing("12083")]),
    receta("l5", "Tortilla de patata con cebolla (lista para comer)", "listo_para_comer", [ing("60089")]),
    receta("l6", "Salmón con verduras (listo para comer)", "listo_para_comer", [ing("13243", 2)]),
    receta("l7", "Gazpacho y pan", "listo_para_comer", [ing("39900"), ing("12049.1", 0.5)]),
]

if __name__ == "__main__":
    destino = Path(__file__).parent.parent / "app" / "data" / "mock_data.json"
    destino.write_text(json.dumps({"recetas": RECETAS}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(RECETAS)} recetas -> {destino}")
