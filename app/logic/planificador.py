"""Planificador determinista: elige recetas, escala cantidades y respeta presupuesto y dietas.

El LLM nunca decide precios ni cantidades; solo pide acciones y este módulo las ejecuta.
"""
import math
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.data.catalogo import get_recetas
from app.logic.carrito import EPS, en_casa_de, escalar_receta, total_plan
from app.logic.errores import DatosInvalidos, Inviable, NoEncontrado, SinAlternativa
from app.logic.texto import DIAS_SEMANA, MOMENTOS, norm, orden_semana
from app.models.schemas import Ingrediente, PlanResponse, Producto, Receta

MAX_COMENSALES = 12


@dataclass
class Peticion:
    comensales: int
    dias: list[str]
    presupuesto: Optional[float] = None
    momentos: list[str] = field(default_factory=lambda: ["comida"])
    sin_cocinar: set[str] = field(default_factory=set)  # días en los que solo hay platos listos
    excluir: set[str] = field(default_factory=set)  # etiquetas: carne, gluten, lactosa...
    rechazadas: set[str] = field(default_factory=set)  # ids de receta que no se quieren


def _validar(p: Peticion) -> list[str]:
    if not 1 <= p.comensales <= MAX_COMENSALES:
        raise DatosInvalidos(f"Solo puedo planificar para entre 1 y {MAX_COMENSALES} personas")
    if p.presupuesto is not None and p.presupuesto <= 0:
        raise DatosInvalidos("El presupuesto tiene que ser mayor que 0")
    if not p.dias:
        raise DatosInvalidos("Hay que indicar al menos un día")
    dias = []
    for d in p.dias:
        canon = next((x for x in DIAS_SEMANA if norm(x) == norm(d)), None)
        if canon is None:
            raise DatosInvalidos(f"{d!r} no es un día de la semana")
        if canon not in dias:
            dias.append(canon)
    return sorted(dias, key=orden_semana)


def _pool(tipo: str, excluir: set[str], rechazadas: set[str]) -> list[Receta]:
    return [
        r
        for r in get_recetas()
        if r.tipo == tipo and not (set(r.etiquetas) & excluir) and r.id not in rechazadas
    ]


def _coste(asignacion: dict[tuple[str, str], Receta], comensales: int, extras: list[Ingrediente]) -> float:
    """Coste en envases enteros de una asignación (dia, momento) -> receta."""
    unidades: dict[str, float] = {}
    precio: dict[str, float] = {}
    for r in asignacion.values():
        factor = comensales / r.raciones
        for i in r.ingredientes:
            unidades[i.producto.id] = unidades.get(i.producto.id, 0.0) + i.unidades * factor
            precio[i.producto.id] = i.producto.precio
    for e in extras:
        unidades[e.producto.id] = unidades.get(e.producto.id, 0.0) + e.unidades
        precio[e.producto.id] = e.producto.precio
    return round(sum(max(1, math.ceil(u - EPS)) * precio[pid] for pid, u in unidades.items()), 2)


def _seleccion_inicial(p: Peticion, dias: list[str]) -> dict[tuple[str, str], Receta]:
    pools = {t: _pool(t, p.excluir, p.rechazadas) for t in ("cocinar", "listo_para_comer")}
    usadas = {"cocinar": 0, "listo_para_comer": 0}
    asignacion = {}
    for dia in dias:
        tipo = "listo_para_comer" if any(norm(dia) == norm(s) for s in p.sin_cocinar) else "cocinar"
        for momento in p.momentos:
            pool = pools[tipo]
            if not pool:
                raise DatosInvalidos(f"Con esas condiciones no me quedan platos de tipo {tipo.replace('_', ' ')}")
            asignacion[(dia, momento)] = pool[usadas[tipo] % len(pool)]  # sin repetir hasta agotar el pool
            usadas[tipo] += 1
    return asignacion


def _ajustar_a_presupuesto(asignacion, p: Peticion, extras: list[Ingrediente]) -> None:
    """Cambia, de uno en uno, el plato que más abarata el total hasta cumplir el presupuesto."""
    pools = {t: _pool(t, p.excluir, p.rechazadas) for t in ("cocinar", "listo_para_comer")}
    while _coste(asignacion, p.comensales, extras) > p.presupuesto:
        actual_total = _coste(asignacion, p.comensales, extras)
        usadas = {r.id for r in asignacion.values()}
        mejor = None  # (total, slot, receta)
        for slot, actual in asignacion.items():
            libres = [r for r in pools[actual.tipo] if r.id not in usadas]
            candidatas = libres or [r for r in pools[actual.tipo] if r.id != actual.id]
            for cand in candidatas:
                total = _coste({**asignacion, slot: cand}, p.comensales, extras)
                if total < actual_total - EPS and (mejor is None or total < mejor[0]):
                    mejor = (total, slot, cand)
        if mejor is None:
            return
        asignacion[mejor[1]] = mejor[2]


def _construir(asignacion, comensales: int, extras: list[Ingrediente]) -> PlanResponse:
    dias: dict[str, list[Receta]] = {}
    for (dia, momento), receta in sorted(asignacion.items(), key=lambda kv: (orden_semana(kv[0][0]), MOMENTOS.index(kv[0][1]))):
        dias.setdefault(dia, []).append(escalar_receta(receta, comensales, momento))
    recetas = [r for rs in dias.values() for r in rs]
    return PlanResponse(id=uuid.uuid4().hex[:8], dias=dias, extras=list(extras), en_casa=en_casa_de(recetas))


def generar_plan(p: Peticion, extras: Optional[list[Ingrediente]] = None) -> PlanResponse:
    """Plan nuevo. Lanza `Inviable` si ni el plan más barato cabe en el presupuesto."""
    extras = extras or []
    dias = _validar(p)
    asignacion = _seleccion_inicial(p, dias)
    if p.presupuesto is not None:
        _ajustar_a_presupuesto(asignacion, p, extras)
        coste = _coste(asignacion, p.comensales, extras)
        if coste > p.presupuesto + EPS:
            raise Inviable(coste)
    return _construir(asignacion, p.comensales, extras)


def cambiar_plato(
    plan: PlanResponse,
    dia: str,
    momento: Optional[str] = None,
    presupuesto: Optional[float] = None,
    excluir: Optional[set[str]] = None,
    rechazadas: Optional[set[str]] = None,
) -> PlanResponse:
    """Sustituye el plato de `dia` (y `momento`, si se indica) por otro del mismo tipo y precio parecido."""
    clave = next((d for d in plan.dias if norm(d) == norm(dia)), None)
    if clave is None:
        raise NoEncontrado(f"El plan no tiene el día {dia!r}")
    objetivos = [r for r in plan.dias[clave] if momento is None or r.momento == momento]
    if not objetivos:
        raise NoEncontrado(f"El {dia} no tiene {momento}")

    excluir, rechazadas = excluir or set(), rechazadas or set()
    total_actual = total_plan(plan)
    nuevo = plan
    for objetivo in objetivos:
        usadas = {r.id for rs in nuevo.dias.values() for r in rs}
        candidatas = [r for r in _pool(objetivo.tipo, excluir, rechazadas) if r.id not in usadas]
        candidatas.sort(key=lambda r: abs(r.precio_estimado - objetivo.precio_estimado))
        elegida = None
        for cand in candidatas:
            escalada = escalar_receta(cand, objetivo.raciones, objetivo.momento)
            dias = {d: [escalada if r is objetivo else r for r in rs] for d, rs in nuevo.dias.items()}
            tentativa = nuevo.model_copy(update={"dias": dias})
            total = total_plan(tentativa)
            if presupuesto is None or total <= presupuesto or total <= total_actual:
                elegida = tentativa
                break
        if elegida is None:
            raise SinAlternativa(f"No tengo otro plato parecido para el {clave} que cumpla las condiciones")
        nuevo = elegida
    recetas = [r for rs in nuevo.dias.values() for r in rs]
    return nuevo.model_copy(update={"id": uuid.uuid4().hex[:8], "en_casa": en_casa_de(recetas)})


def anadir_extra(plan: PlanResponse, producto: Producto, unidades: float = 1) -> PlanResponse:
    extras = [e for e in plan.extras]
    for i, e in enumerate(extras):
        if e.producto.id == producto.id:
            extras[i] = e.model_copy(update={"unidades": e.unidades + unidades})
            break
    else:
        extras.append(Ingrediente(unidades=unidades, producto=producto))
    return plan.model_copy(update={"id": uuid.uuid4().hex[:8], "extras": extras})


def quitar_extra(plan: PlanResponse, consulta: str) -> tuple[PlanResponse, Optional[Producto]]:
    """Quita de `extras` el primer producto cuyo nombre contenga la consulta."""
    q = norm(consulta)
    for i, e in enumerate(plan.extras):
        if q and q in norm(e.producto.nombre):
            extras = plan.extras[:i] + plan.extras[i + 1 :]
            return plan.model_copy(update={"id": uuid.uuid4().hex[:8], "extras": extras}), e.producto
    raise NoEncontrado(f"No tienes {consulta!r} entre los productos extra")
