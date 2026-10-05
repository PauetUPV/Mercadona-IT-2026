from app.data import catalogo


def test_normalizar_producto():
    p = catalogo.normalizar_producto(
        {
            "id": "1",
            "display_name": "Pollo",
            "price_instructions": {"unit_price": "5.22", "reference_price": "5.5", "reference_format": "kg"},
            "categories": [{"name": "Carne", "categories": [{"name": "Aves y pollo"}]}],
        }
    )
    assert p.precio == 5.22
    assert p.categoria == "Carne"
    assert p.subcategoria == "Aves y pollo"


def test_normalizar_producto_incompleto():
    p = catalogo.normalizar_producto({"id": 7, "display_name": "X"})
    assert p.id == "7" and p.precio == 0.0 and p.categoria == ""


def test_get_producto():
    assert catalogo.get_producto("10000").nombre.startswith("Medio pollo")
    assert catalogo.get_producto("no-existe") is None


def test_buscar_sin_acentos_y_filtros():
    res = catalogo.buscar_productos(texto="calabacin", categoria="fruta y verdura", precio_max=1.0)
    assert res and all(p.precio <= 1.0 and p.categoria == "Fruta y verdura" for p in res)


def test_buscar_limite():
    assert len(catalogo.buscar_productos(limite=3)) == 3


def test_recetas_referencian_productos_existentes():
    for receta in catalogo.get_recetas():
        assert receta.ingredientes
        for ing in receta.ingredientes:
            assert catalogo.get_producto(ing.producto.id), f"{receta.id}: falta {ing.producto.id}"
        assert receta.precio_estimado > 0
