"""Lectura del formato "Lay Out Repare" (Imbera y Torrey) sobre el lector
común: renombra las columnas a sus nombres canónicos y se queda con las
tablas de datos.

  * Hojas: el lector común ya ignora las ocultas que no coinciden con el
    encabezado de la hoja de datos (catálogos). Aquí además se exige que el
    encabezado traiga ENCABEZADO_DATOS, para descartar una hoja visible
    que no sea de datos. RUTA va primero.
  * Fila basura: el lector descarta las filas sin ninguna columna clave;
    aquí se repite la regla con los nombres canónicos (CAMPOS_FILA_REAL).
"""

from __future__ import annotations

import pandas as pd

from config.customers.imbera.columns_names import (
    CAMPOS_FILA_REAL,
    COL_ARCHIVO,
    COL_FILA_EXCEL,
    COLUMNAS,
    ENCABEZADO_DATOS,
    HOJA_RUTA,
    NAMES_COLUMNS,
)
from parsers.core.lector import AdjuntoIlegible, normalizar_encabezado
from parsers.imbera_parse import lector
from parsers.imbera_parse.lector import celda_a_texto, normalizar

_ALIAS = {normalizar_encabezado(k): v for k, v in NAMES_COLUMNS.items()}


def renombrar(columnas: list[str]) -> dict[str, str]:
    """{columna del archivo: nombre canónico}; si dos columnas dan el mismo
    nombre canónico, gana la primera."""
    mapeo: dict[str, str] = {}
    usadas: set[str] = set()
    for columna in columnas:
        canonico = _ALIAS.get(columna)
        if canonico and canonico not in usadas:
            mapeo[columna] = canonico
            usadas.add(canonico)
    return mapeo


def leer_layout(content: bytes, archivo: str, nombre: str = "layout.xlsx") -> pd.DataFrame | None:
    """DataFrame con COLUMNAS + _ARCHIVO/_FILA_EXCEL (fila de la hoja), o
    None si el archivo no trae ninguna hoja con el encabezado del layout."""
    try:
        tablas = lector.leer_tablas(nombre, content)
    except AdjuntoIlegible as e:
        print(f"[IMBERA][LECTOR][ERROR] {e}")
        return None

    elegidas = []
    for tabla in tablas:
        mapeo = renombrar(tabla.columnas)
        if ENCABEZADO_DATOS <= set(mapeo.values()):
            elegidas.append((tabla, mapeo))
        else:
            print(f"[IMBERA][LECTOR][INFO] Hoja sin encabezado de datos ignorada: {tabla.hoja!r}")
    if not elegidas:
        return None
    elegidas.sort(key=lambda tm: (normalizar(tm[0].hoja) != HOJA_RUTA, tm[0].oculta))

    registros = []
    for tabla, mapeo in elegidas:
        for fila_hoja, fila in tabla.df.iterrows():
            registro = {c: "" for c in COLUMNAS}
            for columna, canonico in mapeo.items():
                registro[canonico] = celda_a_texto(fila[columna])
            if not any(registro.get(c) for c in CAMPOS_FILA_REAL):
                continue
            registro[COL_ARCHIVO] = archivo
            registro[COL_FILA_EXCEL] = str(fila_hoja)
            registros.append(registro)

    return pd.DataFrame(registros, columns=COLUMNAS + [COL_ARCHIVO, COL_FILA_EXCEL], dtype="object")
