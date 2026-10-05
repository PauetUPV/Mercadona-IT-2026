class NoEncontrado(Exception):
    """El recurso pedido (producto, receta, día...) no existe."""


class DatosInvalidos(Exception):
    """La petición es válida a nivel de esquema pero no se puede atender."""
