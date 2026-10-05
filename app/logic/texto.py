import unicodedata

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MOMENTOS = ["comida", "cena"]


def norm(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar."""
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def orden_semana(dia: str) -> int:
    ordenados = [norm(d) for d in DIAS_SEMANA]
    return ordenados.index(norm(dia)) if norm(dia) in ordenados else len(ordenados)


FECHA_HOY = None  # en tests se fija una fecha (datetime.date); en producción, la de hoy


def hoy() -> str:
    """Nombre del día de hoy ("lunes"...)."""
    from datetime import date

    return DIAS_SEMANA[(FECHA_HOY or date.today()).weekday()]


def dia_mas(dia: str, n: int) -> str:
    return DIAS_SEMANA[(DIAS_SEMANA.index(dia) + n) % 7]
