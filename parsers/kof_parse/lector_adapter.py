"""Adaptador de KOF sobre el lector común ``parsers/core/lector.py``.

La descarga por Graph es del parser; el lector lee cada adjunto ya descargado.
Hojas ocultas en modo "si_coinciden": KOF esconde hojas con el MISMO
encabezado que la visible y filas válidas.

Contrato para ``reader.py``:

    leer_libro(nombre, contenido) -> [
        {"name": str, "hoja": str, "visible": bool, "fila_encabezado": int,
         "columnas": [str], "dataframe": DataFrame (índice = fila de la hoja)}
    ]
"""

import base64

from config.customers.kof.columns_names import LLAVES_ENCABEZADO, MIN_COLUMNAS_ENCABEZADO, NAMES_COLUMNS
from parsers.core.lector import AdjuntoIlegible, es_adjunto_soportado, leer_adjunto

VOCABULARIO = tuple(NAMES_COLUMNS)
CLAVES = tuple(alias for alias, canonica in NAMES_COLUMNS.items() if canonica in LLAVES_ENCABEZADO)


def leer_libro(nombre: str, contenido: bytes) -> list[dict]:
    tablas = leer_adjunto(
        nombre,
        contenido,
        VOCABULARIO,
        hojas_ocultas="si_coinciden",
        claves=CLAVES,
        min_coincidencias=MIN_COLUMNAS_ENCABEZADO,
    )
    return [
        {
            "name": t.archivo,
            "hoja": t.hoja,
            "visible": not t.oculta,
            "fila_encabezado": t.fila_encabezado,
            "columnas": t.columnas,
            "dataframe": t.df,
        }
        for t in tablas
    ]


async def leer_adjuntos(client, user_id, mail_id) -> tuple[list[dict], bool]:
    """(hojas, hubo_excel): hubo_excel es True si llegó al menos una hoja de
    cálculo, aunque ninguna tenga un encabezado de KOF."""
    attachments = await (
        client.users
        .by_user_id(user_id)
        .messages
        .by_message_id(mail_id)
        .attachments
        .get()
    )

    hojas, hubo_excel = [], False
    for attachment in attachments.value or []:
        nombre = getattr(attachment, "name", "") or ""
        contenido = getattr(attachment, "content_bytes", None)
        if not contenido or not es_adjunto_soportado(nombre):
            continue
        # Algunos archivos llegan codificados en Base64.
        if contenido.startswith(b"UEs"):
            contenido = base64.b64decode(contenido)
        hubo_excel = True
        try:
            hojas.extend(leer_libro(nombre, contenido))
        except AdjuntoIlegible as e:
            print(f"[KOF][ERROR] {e}")
    return hojas, hubo_excel
