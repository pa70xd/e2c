"""Lectura del formato "Lay Out Repare" (Imbera y Torrey): encuentra la(s)
hoja(s) de datos, su encabezado (variante A de una fila o variante B con
fila de grupos) y regresa las filas con nombres canónicos.

  * Hojas: se usan las que traen el encabezado de datos
    (ENCABEZADO_DATOS). Una hoja OCULTA solo entra si también lo trae; así
    las hojas de catálogo ("LinesByCategori", "ModelsByLines") nunca se
    leen como datos.
  * Fila basura (sin ningún CAMPOS_FILA_REAL): se descarta en silencio.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.customers.imbera.columns_names import (
    CAMPOS_FILA_REAL,
    COL_ARCHIVO,
    COL_FILA_EXCEL,
    COLUMNAS,
    ENCABEZADO_DATOS,
    HOJA_RUTA,
    MAX_FILAS_ENCABEZADO,
    NAMES_COLUMNS,
)
from parsers.imbera_parse import lector
from parsers.imbera_parse.lector import celda_a_texto, normalizar

_ALIAS = {normalizar(k): v for k, v in NAMES_COLUMNS.items()}


@dataclass
class Encabezado:
    fila: int  # índice 0 de la fila de columnas
    columnas: dict[int, str]  # índice de columna -> nombre canónico


def _grupos(hoja: lector.Hoja, fila_grupos: int, ancho: int) -> list[str]:
    """Nombre de grupo por columna para la fila `fila_grupos` (índice 0),
    extendido sobre las celdas combinadas."""
    if fila_grupos < 0:
        return [""] * ancho
    valores = list(hoja.filas[fila_grupos]) + [None] * ancho
    grupos = [normalizar(v) for v in valores[:ancho]]
    for fmin, cmin, fmax, cmax in hoja.combinadas:
        if fmin <= fila_grupos + 1 <= fmax:
            nombre = grupos[cmin - 1] if cmin - 1 < ancho else ""
            for c in range(cmin - 1, min(cmax, ancho)):
                grupos[c] = nombre
    return grupos


def _columnas(hoja: lector.Hoja, fila: int) -> dict[int, str]:
    encabezado = hoja.filas[fila]
    grupos = _grupos(hoja, fila - 1, len(encabezado))
    columnas: dict[int, str] = {}
    usadas: set[str] = set()
    for i, valor in enumerate(encabezado):
        nombre = normalizar(valor)
        if not nombre:
            continue
        canonico = _ALIAS.get(f"{grupos[i]} | {nombre}") if grupos[i] else None
        canonico = canonico or _ALIAS.get(nombre)
        if canonico and canonico not in usadas:
            columnas[i] = canonico
            usadas.add(canonico)
    return columnas


def encontrar_encabezado(hoja: lector.Hoja) -> Encabezado | None:
    for fila in range(min(MAX_FILAS_ENCABEZADO, len(hoja.filas))):
        columnas = _columnas(hoja, fila)
        if ENCABEZADO_DATOS <= set(columnas.values()):
            return Encabezado(fila, columnas)
    return None


def hojas_de_datos(hojas: list[lector.Hoja]) -> list[tuple[lector.Hoja, Encabezado]]:
    """Hojas con encabezado de datos: primero RUTA, luego las visibles y al
    final las ocultas (solo si coinciden con el encabezado)."""
    elegidas = []
    for hoja in hojas:
        encabezado = encontrar_encabezado(hoja)
        if encabezado is None:
            if not hoja.visible:
                print(f"[IMBERA][LECTOR][INFO] Hoja oculta ignorada (catálogo): {hoja.nombre!r}")
            continue
        elegidas.append((hoja, encabezado))
    elegidas.sort(key=lambda he: (normalizar(he[0].nombre) != HOJA_RUTA, not he[0].visible))
    return elegidas


def _es_fila_real(registro: dict) -> bool:
    return any(registro.get(c) for c in CAMPOS_FILA_REAL)


def leer_layout(content: bytes, archivo: str) -> pd.DataFrame | None:
    """DataFrame con COLUMNAS + _ARCHIVO/_FILA_EXCEL, o None si el archivo
    no trae ninguna hoja con el encabezado del layout."""
    try:
        hojas = lector.leer_hojas(content)
    except Exception as e:
        print(f"[IMBERA][LECTOR][ERROR] No se pudo leer {archivo!r}: {type(e).__name__}")
        return None

    elegidas = hojas_de_datos(hojas)
    if not elegidas:
        return None

    registros = []
    for hoja, encabezado in elegidas:
        for i in range(encabezado.fila + 1, len(hoja.filas)):
            fila = hoja.filas[i]
            registro = {c: "" for c in COLUMNAS}
            for col, canonico in encabezado.columnas.items():
                if col < len(fila):
                    registro[canonico] = celda_a_texto(fila[col])
            if not _es_fila_real(registro):
                continue
            registro[COL_ARCHIVO] = archivo
            registro[COL_FILA_EXCEL] = str(i + 1)
            registros.append(registro)

    return pd.DataFrame(registros, columns=COLUMNAS + [COL_ARCHIVO, COL_FILA_EXCEL], dtype="object")
