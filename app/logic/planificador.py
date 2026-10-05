"""Planificador determinista: elige recetas, escala cantidades y respeta presupuesto y dietas.

El LLM nunca decide precios ni cantidades; solo pide acciones y este módulo las ejecuta.
"""
import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from app.data.catalogo import get_receta, get_recetas
from app.logic.carrito import EPS, en_casa_de, escalar_receta, total_plan
from app.logic.ideas import puntuacion_ligera
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
    fijos: list[tuple[Optional[str], Optional[str], str]] = field(default_factory=list)  # (dia, momento, receta_id) pedidos por el usuario
    semilla: int = 0  # orden de las recetas: misma semilla, mismo plan (cada sesión usa la suya, para variar)
    favoritas: set[str] = field(default_factory=set)  # recetas con 👍: van primero
    prefiere_barato: bool = False  # dijo "muy caro": primero las más baratas
    prefiere_facil: bool = False  # dijo "mucho trabajo": primero las de menos ingredientes
    prefiere_ligero: bool = False  # pidió comer "más ligero": primero ensaladas, cremas, plancha...


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


def slots_fijos(p: Peticion, dias: list[str]) -> dict[tuple[str, str], Receta]:
    """Platos pedidos por el usuario, colocados en su hueco (dia, momento). Sin día: el primero del plan."""
    resultado = {}
    for dia, momento, receta_id in p.fijos:
        receta = get_receta(receta_id)
        dia = next((d for d in dias if dia and norm(d) == norm(dia)), None) if dia else dias[0]
        if receta is None or dia is None:
            continue
        resultado[(dia, momento if momento in p.momentos else p.momentos[0])] = receta
    return resultado


def _seleccion_inicial(p: Peticion, dias: list[str]) -> dict[tuple[str, str], Receta]:
    fijos = slots_fijos(p, dias)
    ids_fijos = {r.id for r in fijos.values()}
    pools = {
        t: [r for r in _pool(t, p.excluir, p.rechazadas) if r.id not in ids_fijos] for t in ("cocinar", "listo_para_comer")
    }
    for pool in pools.values():  # mezcla estable: evita cinco platos de pollo seguidos (las recetas van por familias)
        random.Random(p.semilla).shuffle(pool)
        # Gustos aprendidos del feedback (dentro de cada grupo se mantiene el orden de la mezcla)
        pool.sort(key=lambda r: (
            r.id not in p.favoritas,
            r.precio_estimado if p.prefiere_barato else 0,
            len(r.ingredientes) if p.prefiere_facil else 0,
            -puntuacion_ligera(r) if p.prefiere_ligero else 0,
        ))
    usadas = {"cocinar": 0, "listo_para_comer": 0}
    asignacion = {}
    for dia in dias:
        tipo = "listo_para_comer" if any(norm(dia) == norm(s) for s in p.sin_cocinar) else "cocinar"
        for momento in p.momentos:
            if (dia, momento) in fijos:
                asignacion[(dia, momento)] = fijos[(dia, momento)]
                continue
            pool = pools[tipo]
            if not pool:
                raise DatosInvalidos(f"Con esas condiciones no me quedan platos de tipo {tipo.replace('_', ' ')}")
            asignacion[(dia, momento)] = pool[usadas[tipo] % len(pool)]  # sin repetir hasta agotar el pool
            usadas[tipo] += 1
    return asignacion


def _ajustar_a_presupuesto(asignacion, p: Peticion, extras: list[Ingrediente], fijos) -> None:
    """Cambia, de uno en uno, el plato que más abarata el total hasta cumplir el presupuesto."""
    pools = {t: _pool(t, p.excluir, p.rechazadas) for t in ("cocinar", "listo_para_comer")}
    while _coste(asignacion, p.comensales, extras) > p.presupuesto:
        actual_total = _coste(asignacion, p.comensales, extras)
        usadas = {r.id for r in asignacion.values()}
        mejor = None  # (total, slot, receta)
        for slot, actual in asignacion.items():
            if slot in fijos:
                continue  # lo que pidió el usuario no se toca
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
        _ajustar_a_presupuesto(asignacion, p, extras, slots_fijos(p, dias))
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
    filtro: Optional[Callable[[Receta], bool]] = None,
    orden: Optional[Callable[[Receta, Receta], tuple]] = None,
    solo_ids: Optional[set[str]] = None,
) -> PlanResponse:
    """Sustituye el plato de `dia` (y `momento`, si se indica) por otro.

    Sin criterio: otro del mismo tipo y precio parecido. Con `filtro`/`orden` ("por algo de pescado", "por lentejas"):
    el que mejor encaje, de cualquier tipo. `solo_ids`: cambia solo esos platos del día ("cambia las hamburguesas")."""
    clave = next((d for d in plan.dias if norm(d) == norm(dia)), None)
    if clave is None:
        raise NoEncontrado(f"El plan no tiene el día {dia!r}")
    objetivos = [
        r for r in plan.dias[clave]
        if (momento is None or r.momento == momento) and (solo_ids is None or r.id in solo_ids)
    ]
    if not objetivos:
        raise NoEncontrado(f"El {dia} no tiene {momento}")

    excluir, rechazadas = excluir or set(), rechazadas or set()
    total_actual = total_plan(plan)
    nuevo = plan
    for objetivo in objetivos:
        usadas = {r.id for rs in nuevo.dias.values() for r in rs}
        if filtro is None:
            candidatas = [r for r in _pool(objetivo.tipo, excluir, rechazadas) if r.id not in usadas]
            candidatas.sort(key=lambda r: abs(r.precio_estimado - objetivo.precio_estimado))
        else:
            todas = _pool("cocinar", excluir, rechazadas) + _pool("listo_para_comer", excluir, rechazadas)
            candidatas = [r for r in todas if r.id not in usadas and filtro(r)]
            candidatas.sort(key=lambda r: orden(r, objetivo) if orden else abs(r.precio_estimado - objetivo.precio_estimado))
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
            raise SinAlternativa(clave)  # el día; el mensaje lo redacta quien llama, según lo que se pidió
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


def poner_plato(plan: PlanResponse, receta: Receta, dia: str, momento: Optional[str], comensales: int) -> PlanResponse:
    """Pone `receta` en `dia` (sustituye el plato de ese momento, o el primero del día; si el día no está, lo añade)."""
    dia = next((d for d in DIAS_SEMANA if norm(d) == norm(dia)), None)
    if dia is None:
        raise DatosInvalidos("Ese no es un día de la semana")
    dias = {d: list(rs) for d, rs in plan.dias.items()}
    actuales = dias.get(dia, [])
    indice = next((k for k, r in enumerate(actuales) if momento and r.momento == momento), 0 if actuales and not momento else None)
    nueva = escalar_receta(receta, comensales, momento or (actuales[indice].momento if indice is not None else "comida"))
    if indice is None:
        actuales.append(nueva)
        actuales.sort(key=lambda r: MOMENTOS.index(r.momento or "comida"))
    else:
        actuales[indice] = nueva
    dias[dia] = actuales
    dias = dict(sorted(dias.items(), key=lambda kv: orden_semana(kv[0])))
    recetas = [r for rs in dias.values() for r in rs]
    return plan.model_copy(update={"id": uuid.uuid4().hex[:8], "dias": dias, "en_casa": en_casa_de(recetas)})
