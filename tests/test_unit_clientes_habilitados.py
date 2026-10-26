"""Flag ``E2C_CLIENTES_HABILITADOS``: los clientes nuevos de la Fase 4 viven en
el índice pero se ignoran (con log, sin respuesta) mientras no se habiliten."""

import json

import pytest

from src import service
from src.email_type import EMAIL_TYPE, clientes_habilitados, cliente_habilitado
from tests.support.emails import CLIENTES, MAILBOXES, make_email

FLAG = "E2C_CLIENTES_HABILITADOS"
BASE = {"danone", "holanda", "penafiel", "heineken"}
NUEVOS = {
    "cliente.imbera@repare.com.mx": "imbera",
    "cliente.kof@repare.com.mx": "kof",
    "cliente.torrey@repare.com.mx": "torrey",
    "cliente.oxxo@repare.com.mx": "oxxo",
    "cliente.oxogar@repare.com.mx": "oxxo_garantias",
}
CAJA_IMBERA = "cliente.imbera@repare.example.com"
EXTRA = ("Contacto Imbera Ejemplo", "contacto@imbera-cliente.example.com")


@pytest.fixture(autouse=True)
def sin_flag(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)


@pytest.fixture
def validator(tmp_path):
    config = tmp_path / "m.json"
    config.write_text(json.dumps({**MAILBOXES, CAJA_IMBERA: "imbera"}), encoding="utf-8")
    return EMAIL_TYPE(config_path=str(config))


def _a_imbera(**kw):
    return make_email(subject="Solicitud", body="x", sender=EXTRA, to=[CAJA_IMBERA], message_id="m1", **kw)


def test_el_indice_trae_los_buzones_nuevos():
    datos = json.load(open("config/email_index.json", encoding="utf-8"))
    assert NUEVOS.items() <= datos.items()
    assert set(datos.values()) - set(NUEVOS.values()) == BASE


def test_por_defecto_solo_los_clientes_de_hoy():
    assert clientes_habilitados() == BASE


@pytest.mark.parametrize("valor", ["", "  ", ",,"])
def test_valor_vacio_equivale_a_no_definida(monkeypatch, valor):
    monkeypatch.setenv(FLAG, valor)
    assert clientes_habilitados() == BASE


def test_flag_suma_clientes_y_acepta_alias_y_mayusculas(monkeypatch):
    monkeypatch.setenv(FLAG, " Imbera , KOF,hnk ")
    assert clientes_habilitados() == BASE | {"imbera", "kof"}


def test_cliente_test_no_depende_del_flag():
    assert cliente_habilitado("test") and not cliente_habilitado("imbera")


def test_detect_customer_ignora_cliente_nuevo_con_log(validator, capsys):
    assert validator.detect_customer(_a_imbera()) is None
    assert "no habilitado" in capsys.readouterr().out


def test_detect_customer_con_flag(validator, monkeypatch):
    monkeypatch.setenv(FLAG, "imbera")
    assert validator.detect_customer(_a_imbera()) == "imbera"


def test_detect_customer_clientes_de_hoy_intactos(validator):
    correo = make_email(subject="s", body="x", sender=CLIENTES["danone"], to=["cliente.danone@repare.example.com"], message_id="m2")
    assert validator.detect_customer(correo) == "danone"


def test_detect_direccion_ignora_cliente_nuevo_y_con_flag_lo_ve(validator, monkeypatch, capsys):
    assert validator.detect_direccion(_a_imbera()) is None
    assert "no habilitado" in capsys.readouterr().out
    monkeypatch.setenv(FLAG, "imbera")
    assert validator.detect_direccion(_a_imbera()) == ("imbera", "inbound")


# ---- de punta a punta -----------------------------------------------------

@pytest.fixture
def con_imbera(harness, monkeypatch):
    monkeypatch.setitem(service.validator.mailboxes, CAJA_IMBERA, "imbera")
    monkeypatch.setitem(service.CUSTOMER_INDEX, CAJA_IMBERA, "imbera")
    return harness


def test_flag_vacio_cliente_nuevo_se_ignora_sin_responder(con_imbera, capsys):
    assert con_imbera.deliver(_a_imbera()) is None
    assert con_imbera.replies == []
    assert con_imbera.repo.snapshot() == []
    assert "no habilitado" in capsys.readouterr().out


def test_flag_sin_parser_registrado_se_ignora_con_log(con_imbera, monkeypatch, capsys):
    monkeypatch.setenv(FLAG, "imbera")
    assert "imbera" not in service.PARSERS_INIT
    assert con_imbera.deliver(_a_imbera()) is None
    assert con_imbera.replies == []
    assert con_imbera.repo.snapshot() == []
    assert "sin parser INIT registrado" in capsys.readouterr().out


def test_flag_sin_parser_reply_registrado_se_ignora_con_log(con_imbera, monkeypatch, capsys):
    monkeypatch.setenv(FLAG, "imbera")
    monkeypatch.setitem(service.PARSERS_INIT, "imbera", object)  # solo INIT registrado
    correo = make_email(
        subject="Re: Solicitud", body="x", sender=EXTRA, to=[CAJA_IMBERA],
        message_id="m3", conversation_id="c1",
    )
    assert con_imbera.deliver(correo) is None
    assert con_imbera.replies == []
    assert "sin parser REPLY registrado" in capsys.readouterr().out
