from app.data.catalogo import get_recetas
from app.models.schemas import PeticionSustitucion


def sustituir_plato(peticion: PeticionSustitucion) -> dict:
    # TODO: lógica real de sustitución
    alternativas = [r for r in get_recetas() if r["id"] != peticion.receta_id]
    return alternativas[0]
