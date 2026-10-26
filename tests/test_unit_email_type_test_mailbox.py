"""Buzón de pruebas por variable de entorno ``E2C_TEST_MAILBOX``."""

import json

from src.email_type import EMAIL_TYPE, with_test_mailbox
from tests.support.emails import CLIENTES, make_email

REPARE_BOXES = {"cliente.x@repare.example.com": "danone"}

BUZON = "buzon.pruebas@example.com"


def _validator(tmp_path):
    config = tmp_path / "mailboxes.json"
    config.write_text(json.dumps(REPARE_BOXES), encoding="utf-8")
    return EMAIL_TYPE(config_path=str(config))


def test_sin_variable_no_hay_buzon_de_pruebas(tmp_path, monkeypatch):
    monkeypatch.delenv("E2C_TEST_MAILBOX", raising=False)
    v = _validator(tmp_path)
    assert "test" not in v.mailboxes.values()
    correo = make_email(subject="[danone] prueba", body="x", message_id="m1", sender=CLIENTES["danone"], to=[BUZON])
    assert v.detect_customer(correo) is None


def test_variable_vacia_equivale_a_no_definida(tmp_path, monkeypatch):
    monkeypatch.setenv("E2C_TEST_MAILBOX", "   ")
    assert "test" not in _validator(tmp_path).mailboxes.values()


def test_con_variable_el_buzon_resuelve_a_test(tmp_path, monkeypatch):
    monkeypatch.setenv("E2C_TEST_MAILBOX", f"  {BUZON.upper()} ")
    v = _validator(tmp_path)
    assert v.mailboxes[BUZON] == "test"
    correo = make_email(subject="[danone] prueba", body="x", message_id="m1", sender=CLIENTES["danone"], to=[BUZON])
    assert v.detect_customer(correo) == "test"


def test_with_test_mailbox_no_muta_el_original(monkeypatch):
    monkeypatch.setenv("E2C_TEST_MAILBOX", BUZON)
    original = {"a@example.com": "danone"}
    assert with_test_mailbox(original) == {"a@example.com": "danone", BUZON: "test"}
    assert original == {"a@example.com": "danone"}


def test_el_indice_versionado_no_trae_direccion_personal():
    datos = json.load(open("config/email_index.json", encoding="utf-8"))
    assert "test" not in datos.values()
    assert all(k.endswith("@repare.com.mx") for k in datos)
