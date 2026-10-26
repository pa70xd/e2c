"""Adaptador de lectura de Excel para KOF.

TODO(kof): cambiar por el lector común ``parsers/core/lector.py`` cuando esté
en la base. Este es el único archivo que debe cambiar: el resto del parser
solo usa ``leer_adjuntos`` y ``leer_libro`` con este contrato:

    leer_libro(nombre, contenido) -> [
        {"name": str, "hoja": str, "visible": bool, "dataframe": DataFrame}
    ]

Una entrada por hoja, visibles y ocultas (KOF esconde hojas con filas válidas),
con la cuadrícula cruda (``header=None``, ``dtype=str``): el encabezado lo
busca ``reader.py``.
"""

import base64
from io import BytesIO
from pathlib import Path

import pandas as pd

EXCEL_EXTENSIONS = (".xlsx", ".xlsm", ".xls")


def leer_libro(nombre: str, contenido: bytes) -> list[dict]:
    excel = pd.ExcelFile(BytesIO(contenido))
    if excel.engine == "openpyxl":
        estados = {ws.title: ws.sheet_state == "visible" for ws in excel.book.worksheets}
    else:
        estados = {}

    hojas = []
    for hoja in excel.sheet_names:
        df = excel.parse(sheet_name=hoja, header=None, dtype=str)
        hojas.append({
            "name": nombre,
            "hoja": hoja,
            "visible": estados.get(hoja, True),
            "dataframe": df,
        })
    return hojas


async def leer_adjuntos(client, user_id, mail_id) -> list[dict]:
    attachments = await (
        client.users
        .by_user_id(user_id)
        .messages
        .by_message_id(mail_id)
        .attachments
        .get()
    )

    hojas = []
    for attachment in attachments.value or []:
        nombre = getattr(attachment, "name", "") or ""
        contenido = getattr(attachment, "content_bytes", None)
        if not contenido or nombre.startswith("~$"):
            continue
        if Path(nombre).suffix.lower() not in EXCEL_EXTENSIONS:
            continue
        # Algunos archivos llegan codificados en Base64.
        if contenido.startswith(b"UEs"):
            contenido = base64.b64decode(contenido)
        try:
            hojas.extend(leer_libro(nombre, contenido))
        except Exception as e:
            print(f"[KOF][ERROR] No se pudo leer {nombre!r}: {type(e).__name__}")
    return hojas
