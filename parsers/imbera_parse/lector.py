"""Adaptador de Imbera/Torrey al lector común (parsers/core/lector.py).

Una sola función, ``leer_tablas``, llama a ``leer_adjunto`` con el
vocabulario del "Lay Out Repare" y ``hojas_ocultas="si_coinciden"``: las
hojas de catálogo ocultas ("LinesByCategori", "ModelsByLines") no se leen y
una hoja oculta con el mismo encabezado que la de datos sí.
"""

from __future__ import annotations

import re
import unicodedata

from config.customers.imbera.columns_names import CAMPOS_FILA_REAL, NAMES_COLUMNS
from parsers.core.lector import AdjuntoIlegible, Tabla, es_adjunto_soportado, leer_adjunto  # noqa: F401

# Columnas del layout que identifican una fila real (el lector descarta las
# filas sin ninguna).
CLAVES = tuple(alias for alias, canonico in NAMES_COLUMNS.items() if canonico in CAMPOS_FILA_REAL)


def leer_tablas(nombre: str, contenido: bytes) -> list[Tabla]:
    return leer_adjunto(
        nombre,
        contenido,
        NAMES_COLUMNS.keys(),
        hojas_ocultas="si_coinciden",
        claves=CLAVES,
    )


# ---------------------------------------------------------------------------
# Normalización de texto (asunto, cuerpo y celdas)
# ---------------------------------------------------------------------------

def normalizar(texto) -> str:
    """Mayúsculas, sin acentos y con espacios simples ("Ñ" se conserva para
    no confundir "AÑO" con "ANO")."""
    if texto is None:
        return ""
    texto = str(texto).replace("ñ", "\0").replace("Ñ", "\0")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("\0", "Ñ").upper()
    return " ".join(texto.split())


_FECHA_SIN_HORA = re.compile(r"^(\d{4}-\d{2}-\d{2}) 00:00:00$")


def celda_a_texto(valor) -> str:
    """Celda del lector (str o None) como texto estable: "" si está vacía y
    las fechas sin hora como AAAA-MM-DD."""
    # El lector común deja None, pero según la versión de pandas una celda
    # vacía puede llegar como NaN.
    if valor is None or (isinstance(valor, float) and valor != valor):
        return ""
    texto = str(valor).strip()
    m = _FECHA_SIN_HORA.match(texto)
    return m.group(1) if m else texto
