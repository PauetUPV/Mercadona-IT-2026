"""Regenera app/data/mock_data.json: recetas reales con ingredientes del catálogo de Mercadona.

    PYTHONPATH=. python scripts/generar_mock_data.py

- DESPENSA: ingrediente -> producto real del catálogo (+ etiquetas de alérgenos). Se elige UN producto por ingrediente.
- RECETAS: cantidades en g / ml (o unidades, si el producto se vende por piezas) para 2 raciones.
  El script convierte cada cantidad en fracción de envase con el tamaño real del producto
  (`unidades = cantidad / contenido_del_envase`), y calcula las etiquetas de la receta a partir de sus ingredientes.
- LISTOS: platos listos para comer; `unidades` = envases para 2 raciones.
"""
import json
import sys
from pathlib import Path

from app.data.catalogo import get_producto

# clave: (id de producto, etiquetas)    etiquetas: carne, pescado, gluten, lactosa, huevo, soja
DESPENSA = {
    # Carne y charcutería
    "pechuga": ("2787", ["carne"]),
    "contramuslo": ("2777", ["carne"]),
    "pollo_entero": ("2781", ["carne"]),
    "picada": ("2869", ["carne"]),
    "lomo": ("2817", ["carne"]),
    "costilla": ("2811", ["carne"]),
    "pavo": ("9995", ["carne"]),
    "albondigas": ("2871", ["carne"]),
    "burger": ("2872", ["carne"]),
    "bacon": ("16252", ["carne"]),
    "chorizo": ("54105", ["carne"]),
    "jamon": ("13988", ["carne"]),
    # Pescado
    "merluza": ("62113", ["pescado"]),
    "bacalao": ("87211", ["pescado"]),
    "atun": ("12911", ["pescado"]),
    "sardinas": ("18225", ["pescado"]),
    # Huevos y lácteos
    "huevos": ("31505", ["huevo"]),
    "leche": ("10380", ["lactosa"]),
    "nata": ("10117", ["lactosa"]),
    "mantequilla": ("20722", ["lactosa"]),
    "queso_rallado": ("22216", ["lactosa"]),
    "mozzarella": ("51050", ["lactosa"]),
    "queso_lonchas": ("50371", ["lactosa"]),
    # Verdura y fruta
    "cebolla": ("69089", []),
    "ajo": ("69297", []),
    "tomate": ("69912", []),
    "pimiento_rojo": ("69310", []),
    "pimiento_verde": ("69312", []),
    "zanahoria": ("69586", []),
    "calabacin": ("69338", []),
    "berenjena": ("69326", []),
    "champinon": ("26951", []),
    "espinaca": ("35781", []),
    "brocoli": ("69580", []),
    "judias_verdes": ("16313", []),
    "puerro": ("68408", []),
    "pepino": ("69584", []),
    "aguacate": ("3830", []),
    "limon": ("3210", []),
    "calabaza": ("3527", []),
    "patata": ("69386", []),
    "lechuga": ("68130", []),
    "coliflor": ("69220", []),
    "platano": ("3819", []),
    # Despensa
    "arroz": ("5044", []),
    "spaghetti": ("6245", ["gluten"]),
    "macarron": ("6250", ["gluten"]),
    "tallarines": ("6246", ["gluten"]),
    "lenteja": ("26030", []),
    "garbanzo": ("26029", []),
    "alubia": ("26019", []),
    "tomate_frito": ("17108", []),
    "tomate_triturado": ("16043", []),
    "aceite": ("4640", []),
    "vinagre": ("4940", []),
    "soja": ("17360", ["soja", "gluten"]),
    "pimenton": ("60573", []),
    "harina": ("29100", ["gluten"]),
    "pan_rallado": ("82219", ["gluten"]),
    "caldo_pollo": ("7313", ["carne"]),
    "caldo_verduras": ("7032", []),
    "maiz": ("16714", []),
    "guisantes": ("16416", []),
    "mayonesa": ("13406", ["huevo"]),
    "pan_molde": ("13810", ["gluten"]),
    "pan_hamburguesa": ("13803", ["gluten"]),
    "tortillas": ("80859", ["gluten"]),
    "masa_pizza": ("13985", ["gluten"]),
    "hummus": ("80858", []),
    "piquillo": ("16005", []),
}

SAL = ["sal"]
SAL_PIM = ["sal", "pimienta"]
SAL_AGUA = ["sal", "agua"]


def r(id, nombre, ingredientes, instrucciones, en_casa=SAL):
    return {"id": id, "nombre": nombre, "ingredientes": ingredientes, "instrucciones": instrucciones, "en_casa": list(en_casa)}


RECETAS = [
    r("r1", "Pollo al horno con patatas", [("contramuslo", 500), ("patata", 500), ("pimiento_rojo", 130), ("cebolla", 100), ("aceite", 30)],
      "Precalienta el horno a 200 °C. Pon el pollo, las patatas en rodajas, el pimiento y la cebolla en una bandeja, riega con aceite, sazona y hornea 45 minutos dándole la vuelta a mitad.", SAL_PIM),
    r("r2", "Pechuga a la plancha con ensalada", [("pechuga", 300), ("lechuga", 0.5), ("tomate", 300), ("aceite", 20), ("vinagre", 10)],
      "Salpimenta la pechuga y hazla a la plancha 4 minutos por lado. Trocea la lechuga y el tomate y aliña con aceite, vinagre y sal.", SAL_PIM),
    r("r3", "Pollo al ajillo", [("contramuslo", 500), ("ajo", 30), ("aceite", 40)],
      "Dora el pollo troceado y salpimentado en aceite. Añade los ajos laminados y cocina a fuego medio 20 minutos, hasta que el pollo esté hecho y dorado.", SAL_PIM + ["perejil"]),
    r("r4", "Pollo con tomate y arroz", [("contramuslo", 400), ("tomate_frito", 280), ("arroz", 150)],
      "Cuece el arroz en agua con sal. Dora el pollo, añade el tomate frito y cocina tapado 20 minutos. Sirve con el arroz.", SAL_AGUA),
    r("r5", "Arroz con pollo y verduras", [("arroz", 160), ("contramuslo", 300), ("pimiento_rojo", 130), ("guisantes", 100), ("caldo_pollo", 400)],
      "Sofríe el pollo troceado con el pimiento, añade el arroz y rehoga un minuto. Cubre con el caldo caliente, añade los guisantes y cuece 18 minutos.", SAL),
    r("r6", "Pavo en salsa de champiñones", [("pavo", 300), ("champinon", 200), ("nata", 100), ("cebolla", 80)],
      "Dora el pavo en tacos. Aparte, sofríe la cebolla y los champiñones laminados, añade la nata y el pavo y cocina 8 minutos.", SAL_PIM),
    r("r7", "Hamburguesas con ensalada", [("burger", 300), ("pan_hamburguesa", 160), ("lechuga", 0.5), ("tomate", 150)],
      "Haz las hamburguesas a la plancha 4 minutos por lado. Monta en el pan con lechuga y tomate en rodajas.", SAL),
    r("r8", "Albóndigas en salsa de tomate con arroz", [("albondigas", 400), ("tomate_frito", 280), ("arroz", 120)],
      "Dora las albóndigas, añade el tomate frito y cuece tapado 15 minutos. Acompaña con arroz cocido en agua con sal.", SAL_AGUA),
    r("r9", "Macarrones con carne y tomate", [("macarron", 160), ("picada", 200), ("tomate_frito", 280), ("queso_rallado", 30)],
      "Cuece los macarrones. Sofríe la carne picada, añade el tomate frito y cocina 10 minutos. Mezcla con la pasta y espolvorea queso rallado.", SAL_AGUA),
    r("r10", "Espaguetis a la boloñesa", [("spaghetti", 160), ("picada", 250), ("tomate_triturado", 200), ("cebolla", 80), ("zanahoria", 50)],
      "Sofríe la cebolla y la zanahoria picadas, añade la carne y dórala. Incorpora el tomate triturado y cuece 20 minutos. Sirve sobre los espaguetis cocidos.", SAL_AGUA),
    r("r11", "Espaguetis carbonara", [("spaghetti", 160), ("bacon", 100), ("huevos", 2), ("queso_rallado", 40)],
      "Cuece la pasta. Dora el bacon en tiras. Mezcla fuera del fuego la pasta con el bacon, los huevos batidos y el queso hasta que quede cremoso.", SAL_PIM),
    r("r12", "Pasta con atún y tomate", [("spaghetti", 160), ("atun", 160), ("tomate_frito", 280)],
      "Cuece la pasta. Calienta el tomate frito con el atún escurrido y mézclalo con los espaguetis.", SAL_AGUA),
    r("r13", "Macarrones gratinados con jamón y queso", [("macarron", 160), ("jamon", 100), ("tomate_frito", 140), ("queso_rallado", 60)],
      "Cuece los macarrones y mézclalos con el tomate y el jamón en dados. Pon en una fuente, cubre de queso y gratina 8 minutos.", SAL_AGUA),
    r("r14", "Tallarines salteados con verduras", [("tallarines", 200), ("zanahoria", 100), ("pimiento_rojo", 130), ("calabacin", 150), ("soja", 30), ("aceite", 20)],
      "Cuece los tallarines. Saltea la zanahoria, el pimiento y el calabacín en tiras con aceite, añade la pasta y la salsa de soja.", SAL_AGUA),
    r("r15", "Pasta con champiñones y nata", [("macarron", 160), ("champinon", 200), ("nata", 100), ("ajo", 10)],
      "Cuece la pasta. Saltea los champiñones laminados con el ajo, añade la nata y reduce 5 minutos. Mezcla con la pasta.", SAL_AGUA + ["pimienta"]),
    r("r16", "Lentejas estofadas con verduras", [("lenteja", 570), ("zanahoria", 100), ("pimiento_verde", 130), ("cebolla", 80), ("aceite", 20)],
      "Sofríe la cebolla, el pimiento y la zanahoria picados. Añade las lentejas cocidas con un poco de agua y cuece 15 minutos.", SAL + ["agua", "pimentón"]),
    r("r17", "Lentejas con chorizo", [("lenteja", 570), ("chorizo", 80), ("patata", 150), ("zanahoria", 80)],
      "Cuece la patata y la zanahoria en dados con el chorizo en rodajas durante 15 minutos. Añade las lentejas y cocina 8 minutos más.", SAL_AGUA),
    r("r18", "Garbanzos con espinacas", [("garbanzo", 570), ("espinaca", 250), ("ajo", 10), ("pimenton", 5), ("aceite", 20)],
      "Sofríe el ajo con el pimentón, añade las espinacas congeladas y, cuando se deshagan, los garbanzos escurridos. Cocina 10 minutos.", SAL),
    r("r19", "Garbanzos con calabaza y zanahoria", [("garbanzo", 570), ("calabaza", 250), ("zanahoria", 80), ("cebolla", 80), ("aceite", 20)],
      "Sofríe la cebolla, añade la calabaza y la zanahoria en dados y cuece con un poco de agua 15 minutos. Incorpora los garbanzos y cocina 5 minutos más.", SAL_AGUA),
    r("r20", "Alubias con patata y pimiento", [("alubia", 570), ("patata", 200), ("pimiento_rojo", 130), ("pimenton", 5), ("aceite", 20)],
      "Sofríe el pimiento, añade el pimentón y la patata en dados con agua y cuece 15 minutos. Incorpora las alubias y cocina 8 minutos.", SAL_AGUA),
    r("r21", "Alubias con chorizo", [("alubia", 570), ("chorizo", 80), ("cebolla", 80), ("pimenton", 5)],
      "Sofríe la cebolla con el chorizo en rodajas, añade el pimentón y las alubias con un poco de agua y cocina 12 minutos.", SAL_AGUA),
    r("r22", "Tortilla de patata", [("huevos", 4), ("patata", 400), ("cebolla", 100), ("aceite", 60)],
      "Pocha las patatas y la cebolla en aceite hasta que estén tiernas. Mézclalas con los huevos batidos y cuaja la tortilla por ambos lados.", SAL),
    r("r23", "Tortilla francesa con ensalada", [("huevos", 4), ("lechuga", 0.5), ("tomate", 300), ("aceite", 20), ("vinagre", 10)],
      "Bate los huevos con sal y cuaja la tortilla en una sartén con un poco de aceite. Sirve con lechuga y tomate aliñados.", SAL),
    r("r24", "Revuelto de champiñones y jamón", [("huevos", 4), ("champinon", 200), ("jamon", 80), ("aceite", 15)],
      "Saltea los champiñones laminados, añade el jamón en tiras y, por último, los huevos batidos removiendo hasta que cuajen.", SAL_PIM),
    r("r25", "Huevos al plato con tomate y chorizo", [("huevos", 4), ("tomate_frito", 280), ("chorizo", 60)],
      "Calienta el tomate con el chorizo en rodajas en una cazuela, casca los huevos encima y hornea o cuece tapado 8 minutos.", SAL),
    r("r26", "Revuelto de espinacas", [("huevos", 4), ("espinaca", 250), ("ajo", 10), ("aceite", 15)],
      "Saltea el ajo, añade las espinacas descongeladas y escurridas, y los huevos batidos. Remueve hasta que cuajen.", SAL),
    r("r27", "Ensalada completa con atún", [("lechuga", 1), ("tomate", 300), ("atun", 160), ("huevos", 2), ("cebolla", 40), ("aceite", 20), ("vinagre", 10)],
      "Trocea la lechuga y el tomate, añade el atún escurrido, el huevo cocido en cuartos y la cebolla en aros. Aliña con aceite, vinagre y sal.", SAL),
    r("r28", "Ensalada de pasta", [("macarron", 120), ("atun", 160), ("maiz", 110), ("tomate", 300), ("mayonesa", 40)],
      "Cuece la pasta, enfríala y mézclala con el atún, el maíz, el tomate en dados y la mayonesa.", SAL_AGUA),
    r("r29", "Ensalada de garbanzos", [("garbanzo", 570), ("tomate", 300), ("pepino", 150), ("cebolla", 40), ("aceite", 20), ("vinagre", 10)],
      "Escurre los garbanzos y mézclalos con el tomate, el pepino y la cebolla picados. Aliña con aceite, vinagre y sal.", SAL),
    r("r30", "Ensalada de pollo y aguacate", [("pechuga", 250), ("aguacate", 330), ("lechuga", 1), ("aceite", 20), ("limon", 20)],
      "Haz la pechuga a la plancha y córtala en tiras. Monta con la lechuga y el aguacate en láminas; aliña con aceite, limón y sal.", SAL_PIM),
    r("r31", "Merluza al horno con patatas", [("merluza", 400), ("patata", 400), ("cebolla", 80), ("limon", 30), ("aceite", 30)],
      "Hornea las patatas y la cebolla en rodajas con aceite 25 minutos a 200 °C. Coloca la merluza descongelada encima con limón y hornea 12 minutos más.", SAL_PIM),
    r("r32", "Merluza con calabacín", [("merluza", 300), ("calabacin", 300), ("aceite", 20)],
      "Saltea el calabacín en rodajas. Cocina la merluza a la plancha 3 minutos por lado y sirve sobre el calabacín.", SAL),
    r("r33", "Bacalao con tomate", [("bacalao", 250), ("tomate_frito", 280), ("cebolla", 80), ("aceite", 20)],
      "Sofríe la cebolla, añade el tomate frito y el bacalao desalado y cuece tapado 12 minutos.", SAL),
    r("r34", "Sardinas con ensalada", [("sardinas", 234), ("tomate", 300), ("lechuga", 0.5), ("cebolla", 40), ("vinagre", 10)],
      "Escurre las sardinas. Prepara una ensalada de tomate, lechuga y cebolla aliñada con vinagre y sirve las sardinas encima.", SAL),
    r("r35", "Crema de calabacín", [("calabacin", 400), ("patata", 200), ("cebolla", 80), ("aceite", 20)],
      "Pocha la cebolla, añade el calabacín y la patata en trozos con agua que los cubra y cuece 20 minutos. Tritura hasta que quede fina.", SAL_AGUA),
    r("r36", "Crema de calabaza y zanahoria", [("calabaza", 500), ("zanahoria", 100), ("cebolla", 80), ("aceite", 20)],
      "Sofríe la cebolla, añade la calabaza y la zanahoria troceadas con agua y cuece 20 minutos. Tritura.", SAL_AGUA),
    r("r37", "Pisto con huevo", [("calabacin", 200), ("pimiento_rojo", 130), ("pimiento_verde", 130), ("tomate_frito", 280), ("huevos", 2)],
      "Sofríe los pimientos y el calabacín en dados, añade el tomate frito y cuece 15 minutos. Sirve con un huevo frito encima.", SAL),
    r("r38", "Berenjenas gratinadas con tomate y queso", [("berenjena", 400), ("tomate_frito", 140), ("mozzarella", 125)],
      "Corta la berenjena en rodajas y hazla a la plancha. Monta en una fuente con tomate y mozzarella y gratina 10 minutos.", SAL),
    r("r39", "Salteado de pollo con verduras", [("pechuga", 250), ("calabacin", 200), ("zanahoria", 100), ("pimiento_rojo", 130), ("soja", 20)],
      "Saltea el pollo en tiras, añade las verduras cortadas y cocina 8 minutos. Termina con la salsa de soja.", SAL),
    r("r40", "Pizza casera de jamón y queso", [("masa_pizza", 280), ("tomate_frito", 140), ("mozzarella", 125), ("jamon", 60)],
      "Estira la masa, cubre con tomate, mozzarella y jamón y hornea 12 minutos a 220 °C.", []),
    r("r41", "Pizza de champiñones", [("masa_pizza", 280), ("tomate_frito", 140), ("mozzarella", 125), ("champinon", 100)],
      "Estira la masa, cubre con tomate, mozzarella y champiñones laminados y hornea 12 minutos a 220 °C.", []),
    r("r42", "Wraps de pollo", [("tortillas", 180), ("pechuga", 250), ("lechuga", 0.5), ("tomate", 150), ("mayonesa", 30)],
      "Haz el pollo a tiras a la plancha. Rellena las tortillas con pollo, lechuga, tomate y un poco de mayonesa y enrolla.", SAL),
    r("r43", "Quesadillas de jamón y queso", [("tortillas", 180), ("jamon", 100), ("queso_lonchas", 100)],
      "Rellena media tortilla con jamón y queso, dobla y dora en una sartén seca 2 minutos por lado.", []),
    r("r44", "Sándwich mixto con ensalada", [("pan_molde", 120), ("jamon", 80), ("queso_lonchas", 60), ("lechuga", 0.5), ("tomate", 150)],
      "Monta los sándwiches con jamón y queso y tuéstalos en la sandwichera. Sirve con lechuga y tomate aliñados.", SAL),
    r("r45", "Costillas al horno con patatas", [("costilla", 600), ("patata", 400), ("pimenton", 5)],
      "Adoba las costillas con sal y pimentón. Hornea con las patatas en rodajas 50 minutos a 190 °C.", SAL_PIM),
    r("r46", "Lomo con pimientos y patatas", [("lomo", 300), ("pimiento_verde", 250), ("patata", 300), ("aceite", 30)],
      "Fríe las patatas en rodajas y los pimientos. Haz los filetes de lomo a la plancha y sirve todo junto.", SAL),
    r("r47", "Lomo a la plancha con arroz", [("lomo", 300), ("arroz", 160), ("aceite", 10)],
      "Cuece el arroz. Haz los filetes de lomo salpimentados a la plancha 3 minutos por lado y sirve con el arroz.", SAL_AGUA),
    r("r48", "Patatas guisadas con costilla", [("costilla", 500), ("patata", 500), ("pimenton", 5), ("cebolla", 80)],
      "Sofríe la cebolla con las costillas troceadas, añade el pimentón, las patatas en trozos y agua. Cuece 30 minutos.", SAL_AGUA),
    r("r49", "Arroz tres delicias", [("arroz", 150), ("huevos", 2), ("jamon", 80), ("guisantes", 100), ("zanahoria", 50), ("soja", 15)],
      "Cuece el arroz. Saltea la zanahoria en dados, los guisantes y el jamón, añade el huevo en tortilla troceada, el arroz y la soja.", SAL_AGUA),
    r("r50", "Arroz a la cubana", [("arroz", 150), ("huevos", 2), ("tomate_frito", 140), ("platano", 170)],
      "Cuece el arroz y sírvelo con tomate frito caliente, un huevo frito y el plátano frito en rodajas.", SAL_AGUA),
    r("r51", "Arroz con verduras", [("arroz", 150), ("pimiento_rojo", 130), ("calabacin", 150), ("judias_verdes", 150), ("caldo_verduras", 400)],
      "Sofríe las verduras en trozos, añade el arroz, rehoga y cubre con el caldo caliente. Cuece 18 minutos.", SAL),
    r("r52", "Judías verdes con patatas", [("judias_verdes", 330), ("patata", 300), ("jamon", 60), ("aceite", 20)],
      "Cuece las judías y la patata en trozos 15 minutos. Escurre y saltea con el jamón en tacos y un chorrito de aceite.", SAL_AGUA),
    r("r53", "Coliflor gratinada", [("coliflor", 500), ("leche", 250), ("harina", 25), ("mantequilla", 25), ("queso_rallado", 40)],
      "Cuece la coliflor. Haz una bechamel con mantequilla, harina y leche, cubre la coliflor, añade queso y gratina 10 minutos.", SAL_AGUA + ["nuez moscada"]),
    r("r54", "Brócoli con patata y huevo", [("brocoli", 300), ("patata", 200), ("huevos", 2), ("aceite", 20)],
      "Cuece el brócoli y la patata en trozos. Sirve con un huevo cocido picado y aliña con aceite y sal.", SAL_AGUA),
    r("r55", "Pimientos del piquillo rellenos de atún", [("piquillo", 340), ("atun", 160), ("tomate_frito", 140), ("pan_rallado", 20)],
      "Rellena los pimientos con el atún escurrido mezclado con un poco de tomate. Cubre con tomate, espolvorea pan rallado y hornea 10 minutos.", []),
    r("r56", "Calabacines rellenos de carne", [("calabacin", 400), ("picada", 200), ("tomate_frito", 140), ("queso_rallado", 40)],
      "Vacía los calabacines partidos por la mitad, sofríe la pulpa con la carne y el tomate, rellena, cubre con queso y hornea 20 minutos.", SAL_PIM),
    r("r57", "Fajitas de pollo con pimientos", [("pechuga", 300), ("pimiento_rojo", 130), ("pimiento_verde", 130), ("cebolla", 80), ("tortillas", 180)],
      "Saltea el pollo en tiras con los pimientos y la cebolla. Calienta las tortillas y rellénalas.", SAL_PIM),
    r("r58", "Hummus con verduras y tortillas", [("hummus", 240), ("zanahoria", 100), ("pepino", 150), ("tortillas", 90)],
      "Sirve el hummus con palitos de zanahoria y pepino y las tortillas calientes cortadas en triángulos.", []),
]

# (id, nombre, id producto, envases para 2 raciones, etiquetas)
LISTOS = [
    ("l1", "Lasaña boloñesa", "4487", 2, ["carne", "gluten", "lactosa"]),
    ("l2", "Lasaña de pollo", "11994", 2, ["carne", "gluten", "lactosa"]),
    ("l3", "Lasaña de espinacas y requesón", "4491", 2, ["gluten", "lactosa"]),
    ("l4", "Pollo asado", "13706", 1, ["carne"]),
    ("l5", "Alitas de pollo asadas", "13705", 1, ["carne"]),
    ("l6", "Tortilla de patata y cebolla", "80895", 1, ["huevo"]),
    ("l7", "Tortilla de patata", "80771", 1, ["huevo"]),
    ("l8", "Spaghetti carbonara", "4265", 2, ["carne", "gluten", "lactosa", "huevo"]),
    ("l9", "Pollo al curry con arroz basmati", "4498", 2, ["carne"]),
    ("l10", "Arroz de pescado", "20893", 2, ["pescado"]),
    ("l11", "Arroz de verduras", "60621", 2, []),
    ("l12", "Cocido", "52990", 2, ["carne"]),
    ("l13", "Fabada", "26108", 1, ["carne"]),
    ("l14", "Ensalada de pasta italiana", "24083", 2, ["gluten"]),
    ("l15", "Canelones de carne", "16435", 2, ["carne", "gluten", "lactosa"]),
    ("l16", "Salmón con verduras", "13243", 2, ["pescado"]),
    ("l17", "Ensaladilla rusa", "80784", 2, ["huevo", "pescado"]),
    ("l18", "Albóndigas guisadas", "4797", 2, ["carne", "gluten"]),
    ("l19", "Pizza carnívora", "12083", 1, ["carne", "gluten", "lactosa"]),
    ("l20", "Gazpacho", "39900", 1, []),
]


def unidades(clave: str, cantidad: float) -> float:
    """Fracción de envase que equivale a `cantidad` (g/ml, o piezas) del ingrediente `clave`."""
    pid, _ = DESPENSA[clave]
    p = get_producto(pid)
    assert p is not None, f"{clave}: producto {pid} no existe"
    assert p.tamano, f"{clave}: {p.nombre} no tiene tamaño"
    contenido = p.tamano * 1000 if p.formato_tamano in ("kg", "l") else p.tamano  # g/ml, o piezas
    return round(cantidad / contenido, 4)


def construir() -> list[dict]:
    recetas = []
    for rec in RECETAS:
        etiquetas, ingredientes = set(), []
        for clave, cantidad in rec["ingredientes"]:
            etiquetas.update(DESPENSA[clave][1])
            u = unidades(clave, cantidad)
            if not 0.01 <= u <= 6:
                print(f"AVISO {rec['id']} {clave}: {u} envases ({cantidad})", file=sys.stderr)
            ingredientes.append({"producto_id": DESPENSA[clave][0], "unidades": u})
        recetas.append(
            {
                "id": rec["id"], "nombre": rec["nombre"], "tipo": "cocinar", "raciones": 2,
                "ingredientes": ingredientes, "instrucciones": rec["instrucciones"],
                "en_casa": rec["en_casa"], "etiquetas": sorted(etiquetas),
            }
        )
    for id_, nombre, pid, envases, etiquetas in LISTOS:
        assert get_producto(pid), f"{id_}: producto {pid} no existe"
        recetas.append(
            {
                "id": id_, "nombre": nombre, "tipo": "listo_para_comer", "raciones": 2,
                "ingredientes": [{"producto_id": pid, "unidades": envases}], "instrucciones": None,
                "en_casa": [], "etiquetas": sorted(etiquetas),
            }
        )
    return recetas


if __name__ == "__main__":
    recetas = construir()
    destino = Path(__file__).parent.parent / "app" / "data" / "mock_data.json"
    destino.write_text(json.dumps({"recetas": recetas}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(recetas)} recetas -> {destino}")
