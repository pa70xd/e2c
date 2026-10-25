"""Constructores de correos sintéticos (objetos ``Message`` reales del SDK de
Graph) y buzones inventados. Todo dominio es ``example.com``."""

from __future__ import annotations

import datetime as dt
from typing import Iterable

from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient

# Buzones de REPARE inventados. Sustituyen a ``config/email_index.json``
# (que tiene buzones reales) en ``src.service`` y ``EMAIL_TYPE``.
MAILBOXES = {
    "cliente.danone@repare.example.com": "danone",
    "cliente.penafiel@repare.example.com": "penafiel",
    "cliente.holanda@repare.example.com": "holanda",
    "cliente.heineken@repare.example.com": "heineken",
    "pruebas@example.com": "test",
}
REPARE = {name: addr for addr, name in MAILBOXES.items()}

# Remitentes "cliente" inventados.
CLIENTES = {
    "danone": ("Contacto Danone Ejemplo", "contacto@danone-cliente.example.com"),
    "penafiel": ("Contacto Penafiel Ejemplo", "contacto@penafiel-cliente.example.com"),
    "holanda": ("Contacto Holanda Ejemplo", "contacto@holanda-cliente.example.com"),
    "heineken": ("Contacto Heineken Ejemplo", "contacto@heineken-cliente.example.com"),
}

RECEIVED = dt.datetime(2026, 3, 2, 15, 30, 0, tzinfo=dt.timezone.utc)


def _recipient(addr: str, name: str | None = None) -> Recipient:
    return Recipient(email_address=EmailAddress(address=addr, name=name))


def make_email(
    *,
    subject: str,
    body: str,
    sender: tuple[str, str],
    to: Iterable[str],
    cc: Iterable[str] = (),
    conversation_id: str = "conv-0001",
    message_id: str,
    has_attachments: bool = True,
) -> Message:
    """Correo tal como lo devuelve Graph con ``uniqueBody`` en texto."""
    name, addr = sender
    return Message(
        id=message_id,
        subject=subject,
        conversation_id=conversation_id,
        conversation_index=f"idx-{message_id}",
        internet_message_id=f"<{message_id}@mail.example.com>",
        change_key=f"ck-{message_id}",
        web_link=f"https://mail.example.com/owa/?ItemID={message_id}",
        is_draft=False,
        has_attachments=has_attachments,
        received_date_time=RECEIVED,
        sent_date_time=RECEIVED,
        sender=_recipient(addr, name),
        from_=_recipient(addr, name),
        to_recipients=[_recipient(a) for a in to],
        cc_recipients=[_recipient(a) for a in cc],
        bcc_recipients=[],
        unique_body=ItemBody(content_type=BodyType.Text, content=body),
        body=ItemBody(content_type=BodyType.Text, content=body),
    )


def notification(message: Message, user: str = "user-0001") -> dict:
    """Payload ``value[i]`` de Graph que recibe ``/receive_mail``."""
    return {
        "resourceData": {
            "@odata.id": f"Users/{user}/Messages/{message.id}",
            "id": message.id,
        }
    }
