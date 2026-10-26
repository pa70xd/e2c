"""Torrey: las máquinas o fábricas de hielo se generan para el cliente
IMBERA (y se contestan en el hilo de Torrey)."""

from config.customers.torrey.reglas_torrey import CLIENTE_OS_HIELO, PATRON_HIELO
from parsers.imbera_parse.lector import normalizar


def es_hielo(fila: dict) -> bool:
    texto = f"{normalizar(fila.get('MODELO'))} {normalizar(fila.get('FALLA'))}"
    return bool(PATRON_HIELO.search(texto))


def cliente_os_hielo(fila: dict) -> str | None:
    """Cliente de la OS para la fila: IMBERA si es de hielo; None (el de
    Torrey) si no."""
    return CLIENTE_OS_HIELO if es_hielo(fila) else None
