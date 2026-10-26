"""Adjuntos del correo (Imbera y Torrey): las hojas de cálculo del "Lay Out Repare"
(.xlsx, .xls, .xlsm y .ods, las que lee el lector común)
se registran como tablas de DuckDB; del resto (PDF, fotos) solo se
conserva el nombre, para las señales de garantía."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field

from parsers.imbera_parse.layout import leer_layout
from parsers.imbera_parse.lector import es_adjunto_soportado


@dataclass
class Adjuntos:
    # [{"name", "table", "content"}] por Excel con el layout.
    tablas: list[dict] = field(default_factory=list)
    # Nombres de todos los adjuntos que no son Excel (PDF, imágenes...).
    otros: list[str] = field(default_factory=list)
    # Excel que no traen el layout (se avisa en la respuesta).
    excel_sin_layout: list[str] = field(default_factory=list)


def _contenido(attachment) -> bytes:
    content = attachment.content_bytes or b""
    if content.startswith(b"UEs"):  # Graph a veces lo entrega en Base64
        content = base64.b64decode(content)
    return content


async def listar_adjuntos(client, user_id, mail_id):
    attachments = await (
        client.users
        .by_user_id(user_id)
        .messages
        .by_message_id(mail_id)
        .attachments
        .get()
    )
    return [a for a in (attachments.value or []) if getattr(a, "name", None)]


async def get_adjuntos(client, user_id, mail_id, duck_conn) -> Adjuntos:
    resultado = Adjuntos()

    for index, attachment in enumerate(await listar_adjuntos(client, user_id, mail_id), start=1):
        nombre = attachment.name
        if nombre.startswith("~$"):
            continue

        if not es_adjunto_soportado(nombre):
            resultado.otros.append(nombre)
            continue

        if not hasattr(attachment, "content_bytes"):
            continue

        content = _contenido(attachment)
        table_name = f"excel_{index}"
        df = leer_layout(content, table_name, nombre)
        if df is None:
            resultado.excel_sin_layout.append(nombre)
            continue

        duck_conn.register("tmp_df", df)
        duck_conn.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM tmp_df')
        duck_conn.unregister("tmp_df")

        resultado.tablas.append({"name": nombre, "table": table_name, "content": content})

    return resultado
