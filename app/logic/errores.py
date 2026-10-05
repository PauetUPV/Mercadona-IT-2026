class NoEncontrado(Exception):
    """El recurso pedido (producto, receta, día...) no existe."""


class DatosInvalidos(Exception):
    """La petición es válida a nivel de esquema pero no se puede atender."""


class Inviable(DatosInvalidos):
    """El presupuesto no alcanza ni para el plan más barato posible."""

    def __init__(self, minimo: float):
        super().__init__(f"El plan más barato posible cuesta {minimo:.2f} €")
        self.minimo = minimo


class SinAlternativa(DatosInvalidos):
    """No hay otro plato que cumpla las condiciones (tipo, dieta, presupuesto)."""
