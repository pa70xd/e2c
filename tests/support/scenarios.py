"""Armado de correos de hilo (cliente -> REPARE, REPARE -> cliente, comandos
del bot) con los buzones y textos inventados de tests/fixtures/."""

from __future__ import annotations

from tests.support.emails import CLIENTES, REPARE, make_email

OPERADOR = "Operador REPARE Ejemplo"


def inbound(cliente: str, correo: dict, message_id: str, conversation_id: str, *, cc=()):
    """Cliente -> REPARE (correo nuevo con Excel o ampliación en el hilo)."""
    return make_email(
        subject=correo["subject"],
        body=correo["body"],
        sender=CLIENTES[cliente],
        to=[REPARE[cliente]],
        cc=cc,
        conversation_id=conversation_id,
        message_id=message_id,
    )


def outbound(cliente: str, correo: dict, message_id: str, conversation_id: str):
    """REPARE -> cliente (Excel con OS)."""
    return make_email(
        subject=correo["subject"],
        body=correo["body"],
        sender=(OPERADOR, REPARE[cliente]),
        to=[CLIENTES[cliente][1]],
        conversation_id=conversation_id,
        message_id=message_id,
        has_attachments=True,
    )


def bot_command(cliente: str, subject: str, comando: str, message_id: str, conversation_id: str):
    """REPARE -> REPARE: el operador responde al correo del bot con un comando."""
    return make_email(
        subject=subject,
        body=comando,
        sender=(OPERADOR, REPARE[cliente]),
        to=[REPARE[cliente]],
        conversation_id=conversation_id,
        message_id=message_id,
        has_attachments=False,
    )


# Filas de ejemplo para bot.global (RealDictRow en producción). Las fechas van
# sin zona horaria: openpyxl rechaza datetimes con tzinfo.
GLOBAL_ROWS = [
    {
        "request_code": "REPARE_000042",
        "status": "IN_PROGRESS",
        "total_coolers": 3,
        "created_at": "2026-03-02T09:30:00",
        "cliente": "DANONE",
    },
    {
        "request_code": "REPARE_000043",
        "status": "COMPLETED",
        "total_coolers": 1,
        "created_at": "2026-03-03T10:00:00",
        "cliente": "BONAFONT",
    },
]
