"""Lectura de los Excel de garantías de Oxxo (Lay Out Repare; puede ser una
línea de cuartos fríos de Imbera) con el lector común
``parsers/core/lector.py``.

Este módulo solo aporta el vocabulario de columnas de Oxxo
(``config/customers/oxxo/columns_names.py``), traduce las columnas leídas a
las llaves canónicas y aplica el tope de filas. Las hojas ocultas se ignoran
(``hojas_ocultas="nunca"``): leerlas duplicaría OS.

Los valores nunca se imprimen."""

from __future__ import annotations

import pandas as pd

from parsers.core.lector import AdjuntoIlegible, es_adjunto_soportado, leer_adjunto

from config.customers.oxxo.columns_names import (
    MAX_FILAS_EXCEL,
    MIN_ALIAS_ENCABEZADO,
    NAMES_EXCEL,
)


class ExcelIlegible(Exception):
    """El archivo no se pudo abrir o no tiene un encabezado reconocible."""


def es_excel(nombre: str | None) -> bool:
    return es_adjunto_soportado(nombre or "")


def leer_filas(nombre: str, contenido: bytes) -> list[dict[str, str | None]]:
    """Filas del adjunto con llaves canónicas (NAMES_EXCEL), una por renglón
    con datos. ``ExcelIlegible`` si no abre, no tiene encabezado reconocible o
    tiene demasiadas filas."""
    try:
        tablas = leer_adjunto(
            nombre, contenido, NAMES_EXCEL, "nunca", min_coincidencias=MIN_ALIAS_ENCABEZADO
        )
    except (AdjuntoIlegible, ValueError) as e:
        raise ExcelIlegible(type(e).__name__) from e
    if not tablas:
        raise ExcelIlegible("sin_encabezado")

    filas: list[dict[str, str | None]] = []
    for tabla in tablas:
        canonicas: dict[str, str] = {}
        for columna in tabla.columnas:
            canonica = NAMES_EXCEL.get(columna)
            if canonica and canonica not in canonicas.values():
                canonicas[columna] = canonica
        for _, fila in tabla.df.iterrows():
            datos = {
                canonica: None if pd.isna(fila[columna]) else fila[columna]
                for columna, canonica in canonicas.items()
            }
            if any(datos.values()):
                filas.append(datos)
    if len(filas) > MAX_FILAS_EXCEL:
        raise ExcelIlegible("demasiadas_filas")
    return filas
