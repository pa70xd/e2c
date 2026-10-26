"""Harness de Oxxo: el de tests/conftest.py más lo que Oxxo necesita y el
harness base no conoce (sin tocar tests/support/).

* Buzones inventados de Oxxo (el base solo trae los de otros clientes).
* ``DB_OXXO`` falso en el mismo ``FakeRepo`` (queda en ``repo_calls`` como
  ``oxxo.DB_OXXO``).
* Los parsers de Oxxo APAGADOS salvo que la prueba los encienda con
  ``oxxo.encender(...)``: igual que en producción.
"""

import json
from pathlib import Path

import pytest

import src.service as service
from repository.oxxo.consultas_postgre import DB_OXXO
from tests.support import emails as emails_mod
from tests.support.fakes import _wrap

MAILBOX_MANTENIMIENTO = "cliente.oxxo@repare.example.com"
MAILBOX_GARANTIAS = "cliente.oxogar@repare.example.com"
SISTEMA = ("Sistema Oxxo Ejemplo", "notificaciones@oxxo-sistema.example.com")
OPERADOR = ("Operador REPARE Ejemplo", None)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "oxxo"


class Oxxo:
    def __init__(self, harness, monkeypatch):
        self.h = harness
        self._mp = monkeypatch
        self.correos = json.loads((FIXTURES / "correos.json").read_text(encoding="utf-8"))

    def encender(self, valor="oxxo,oxxo_garantias"):
        self._mp.setenv("E2C_CLIENTES_HABILITADOS", valor)

    def apagar(self):
        self._mp.delenv("E2C_CLIENTES_HABILITADOS", raising=False)

    def xlsm(self, nombre):
        return nombre, (FIXTURES / nombre).read_bytes()

    def correo(self, buzon, clave, message_id, *, conversation_id=None, con_adjunto=False, asunto=None):
        c = self.correos[clave]
        return emails_mod.make_email(
            subject=asunto or c["subject"],
            body=c["body"],
            sender=SISTEMA,
            to=[buzon],
            conversation_id=conversation_id or f"conv-{message_id}",
            message_id=message_id,
            has_attachments=con_adjunto,
        )

    def comando(self, buzon, comando, message_id, conversation_id="conv-bot"):
        return emails_mod.make_email(
            subject="RE: Solicitud registrada",
            body=comando,
            sender=("Operador REPARE Ejemplo", buzon),
            to=[buzon],
            conversation_id=conversation_id,
            message_id=message_id,
            has_attachments=False,
        )


@pytest.fixture
def oxxo(harness, monkeypatch):
    mailboxes = {
        **emails_mod.MAILBOXES,
        MAILBOX_MANTENIMIENTO: "oxxo",
        MAILBOX_GARANTIAS: "oxxo_garantias",
    }
    monkeypatch.setattr(service.validator, "mailboxes", dict(mailboxes))
    monkeypatch.setattr(service, "CUSTOMER_INDEX", dict(mailboxes))

    repo = harness.repo
    repo._defaults.update({
        "insert_fila": True,
        "get_by_folio": None,
        "marcar_escalacion": True,
        "get_request": {"request_code": "REPARE_000042", "status": "IN_PROGRESS"},
    })
    for nombre, miembro in list(vars(DB_OXXO).items()):
        if nombre.startswith("_") or not isinstance(miembro, staticmethod):
            continue
        monkeypatch.setattr(
            DB_OXXO, nombre,
            _wrap(repo, "repository.oxxo.consultas_postgre", "DB_OXXO", nombre, miembro.__func__),
        )

    monkeypatch.delenv("E2C_CLIENTES_HABILITADOS", raising=False)
    return Oxxo(harness, monkeypatch)
