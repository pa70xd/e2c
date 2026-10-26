"""Piezas de KOF para el harness: tests/support no conoce a KOF, así que el
buzón se agrega aquí con monkeypatch (sin tocar el harness compartido)."""

import pytest

import src.service as service
from tests.support.emails import make_email

CLIENTE = "kof"
BUZON_KOF = "cliente.kof@repare.example.com"
CONTACTO_KOF = ("Contacto KOF Ejemplo", "contacto@kof-cliente.example.com")
OPERADOR = ("Operador REPARE Ejemplo", BUZON_KOF)


@pytest.fixture
def kof(harness, monkeypatch):
    """``harness`` con el buzón inventado de KOF, habilitado."""
    monkeypatch.setenv("E2C_CLIENTES_HABILITADOS", CLIENTE)
    monkeypatch.setitem(service.validator.mailboxes, BUZON_KOF, CLIENTE)
    monkeypatch.setitem(service.CUSTOMER_INDEX, BUZON_KOF, CLIENTE)
    return harness


def inbound(correo, message_id, conversation_id):
    return make_email(
        subject=correo["subject"], body=correo["body"], sender=CONTACTO_KOF,
        to=[BUZON_KOF], conversation_id=conversation_id, message_id=message_id,
    )


def outbound(correo, message_id, conversation_id):
    return make_email(
        subject=correo["subject"], body=correo["body"], sender=OPERADOR,
        to=[CONTACTO_KOF[1]], conversation_id=conversation_id, message_id=message_id,
    )


def bot_command(subject, comando, message_id, conversation_id):
    return make_email(
        subject=subject, body=comando, sender=OPERADOR, to=[BUZON_KOF],
        conversation_id=conversation_id, message_id=message_id, has_attachments=False,
    )
