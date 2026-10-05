from app.data.catalogo import get_recetas
from app.models.schemas import PeticionPlan


def generar_plan(peticion: PeticionPlan) -> dict:
    recetas = get_recetas()
    # TODO: lógica real (presupuesto, días, restricciones)
    return {dia: recetas[0] for dia in peticion.dias}
