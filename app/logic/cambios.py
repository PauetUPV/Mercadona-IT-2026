"""Cambiar platos del plan: "cambia el lunes", "cambia el lunes y el martes por algo de pescado", "cambia las hamburguesas",
"cambia la pasta por arroz", "cambia todo".

Qué se cambia: días, platos nombrados (por nombre o ingrediente) o todo.
Con qué: si dice "por X", el plato que mejor encaje con X (un plato concreto, un ingrediente, "algo ligero",
"algo vegetariano"...). Ese criterio es SOLO para el hueco: "por algo vegetariano" no cambia la dieta del usuario.
"""
import re
from typing import Callable, Optional

from app.data import catalogo
from app.logic import ideas, planificador
from app.logic.errores import NoEncontrado, SinAlternativa
from app.logic.interprete import Interpretacion, _estilo, _excluir_en
from app.logic.sesiones import Sesion
from app.logic.texto import DIAS_SEMANA, norm
from app.models.schemas import PlanResponse, Receta

_PALABRAS_CRITERIO = {"ligero", "ligera", "sano", "sana", "especial", "rapido", "rapida", "facil", "barato", "barata",
                      "vegetariano", "vegetariana", "vegano", "vegana", "gluten", "lactosa", "distinto", "diferente", "otro"}


def _tokens(texto: str) -> list[str]:
    return [t for t in catalogo._tokens_plato(texto) if t not in _PALABRAS_CRITERIO]


def criterio(por: Optional[str]) -> tuple[Optional[Callable[[Receta], bool]], Optional[Callable], str]:
    """(filtro, orden, descripción) para "por X". Sin "por": (None, None, "")."""
    if not por:
        return None, None, ""
    n = norm(por)
    tokens = _tokens(n)
    sin = set(_excluir_en(n)) | set(_excluir_en("sin " + n) if re.search(r"\b(?:gluten|lactosa)\b", n) else [])
    if re.search(r"\bsin carne\b", n):
        sin.add("carne")
    estilo = _estilo(n)

    def filtro(r: Receta) -> bool:
        return not (set(r.etiquetas) & sin) and (not tokens or ideas._coincidencias(r, tokens) > 0)

    def en_el_nombre(r: Receta) -> int:
        """Cuántas de las cosas pedidas dan nombre al plato: "pescado" -> Merluza…, Bacalao… (no Pasta con atún)."""
        nombre = norm(r.nombre)
        return sum(any(v in nombre for v in ideas.SINONIMOS.get(t.rstrip("s"), [t])) for t in tokens)

    def orden(r: Receta, original: Receta) -> tuple:
        por_estilo = {"ligero": -ideas.puntuacion_ligera(r), "especial": -r.precio_estimado,
                      "rapido": len(r.ingredientes), "barato": r.precio_estimado}.get(estilo or "", 0)
        return (
            -ideas._coincidencias(r, tokens),
            -en_el_nombre(r),  # "por lentejas": mejor "Lentejas…" que algo que solo las lleve
            r.tipo != original.tipo,  # a igualdad, mismo tipo (cocinar / listo)
            por_estilo,
            abs(r.precio_estimado - original.precio_estimado),
        )

    return filtro, orden, por


def _platos_que_coinciden(plan: PlanResponse, objetivo: str) -> list[tuple[str, Receta]]:
    """Platos del plan que el usuario nombra: por nombre ("las hamburguesas") o ingrediente ("la pasta")."""
    tokens = _tokens(norm(objetivo))
    if not tokens:
        return []
    encontrados = []
    for dia, recetas in plan.dias.items():
        for r in recetas:
            nombre = set(catalogo._tokens_plato(r.nombre))
            if set(tokens) <= nombre or ideas._coincidencias(r, tokens) == len(tokens):
                encontrados.append((dia, r))
    return encontrados


def cambiar(sesion: Sesion, i: Interpretacion) -> tuple[dict, Optional[PlanResponse]]:
    plan = sesion.plan
    if plan is None:
        return {"tipo": "sin_plan"}, None

    solo_ids = None
    if i.todo:
        dias = list(plan.dias)
    else:
        dias = [d for d in DIAS_SEMANA if any(norm(d) == norm(x) for x in (i.dias_cambio or ([i.dia] if i.dia else [])))]
        if not dias and i.objetivo:
            encontrados = _platos_que_coinciden(plan, i.objetivo)
            if not encontrados:
                return {"tipo": "rechazo", "exito": False, "motivo": f"No tienes «{i.objetivo}» en el plan."}, None
            dias = list(dict.fromkeys(d for d, _ in encontrados))
            solo_ids = {r.id for _, r in encontrados}
    if not dias:
        return {"tipo": "rechazo", "exito": False, "motivo": "¿Qué día quieres cambiar?"}, None
    fuera = [d for d in dias if d not in plan.dias]
    dias = [d for d in dias if d in plan.dias]
    if not dias:
        return {"tipo": "rechazo", "exito": False, "motivo": f"El {' ni el '.join(fuera)} no está en tu plan."}, None

    filtro, orden, descripcion = criterio(i.por)
    nuevo, hechos = plan, {}
    for dia in dias:
        try:
            nuevo = planificador.cambiar_plato(
                nuevo, dia, i.momento, sesion.presupuesto, set(sesion.excluir), set(sesion.rechazadas),
                filtro=filtro, orden=orden, solo_ids=solo_ids,
            )
        except NoEncontrado as e:
            return {"tipo": "rechazo", "exito": False, "motivo": str(e)}, None
        except SinAlternativa:
            con = f" con «{descripcion}»" if descripcion else ""
            return {
                "tipo": "sin_alternativa", "exito": False,
                "motivo": f"No tengo otro plato{con} para el {dia} que encaje con tu dieta y tu presupuesto.",
            }, None
        hechos[dia] = " y ".join(r.nombre for r in nuevo.dias[dia])

    sesion.plan = nuevo
    sesion.fijos = [f for f in sesion.fijos if f["dia"] not in hechos]
    primero = next(iter(hechos))
    sesion.ultima_receta = nuevo.dias[primero][0].id
    return {"tipo": "cambio_plato", "exito": True, "cambios": hechos, "dia": primero, "nuevo": hechos[primero],
            "no_estaban": fuera}, nuevo
