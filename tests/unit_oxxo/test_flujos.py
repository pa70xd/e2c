"""Flujos de Oxxo de punta a punta (processMail con dobles) y sus goldens.

Regenerar: ``pytest tests/unit_oxxo --update-golden``.
"""

import pytest

from tests.fixtures.oxxo import build_oxxo
from tests.unit_oxxo.conftest import MAILBOX_GARANTIAS, MAILBOX_MANTENIMIENTO


def _nombres(h):
    """Llamadas al repo de los parsers (sin la consulta de hilo de service)."""
    return [n for n in h.repo.names() if n != "conversation_exists"]


# ------------------------------------------------------------ apagado

@pytest.mark.golden
@pytest.mark.parametrize("valor", [None, "", "danone,holanda", "oxxo_garantias"])
def test_mantenimiento_apagado_no_hace_nada(oxxo, golden, valor):
    if valor is not None:
        oxxo.encender(valor)
    msg = oxxo.correo(MAILBOX_MANTENIMIENTO, "mantenimiento", "msg-ox-apagado")
    oxxo.h.deliver(msg)
    assert oxxo.h.replies == []
    assert _nombres(oxxo.h) == []
    if valor is None:
        golden.check("oxxo_apagado", oxxo.h.snapshot())


@pytest.mark.golden
def test_garantias_apagado_no_hace_nada(oxxo):
    oxxo.encender("oxxo")
    msg = oxxo.correo(MAILBOX_GARANTIAS, "seguimiento", "msg-og-apagado")
    oxxo.h.deliver(msg)
    assert oxxo.h.replies == []
    assert _nombres(oxxo.h) == []


# ------------------------------------------------------------ mantenimiento

@pytest.mark.golden
def test_mantenimiento_os_nueva(oxxo, golden):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_MANTENIMIENTO, "mantenimiento", "msg-ox-nueva")
    assert oxxo.h.deliver(msg) == "recibido"
    assert _nombres(oxxo.h) == [
        "email_init_exist", "get_by_folio", "save_email_log_init", "send_email_request", "insert_fila",
    ]
    [fila] = oxxo.h.repo.calls_to("insert_fila")
    assert fila["params"]["fila"]["folio"] == "10000001"
    assert fila["params"]["fila"]["serie_fabricante"] is None
    assert len(oxxo.h.replies) == 1
    golden.check("oxxo_mantenimiento_os_nueva", oxxo.h.snapshot())


@pytest.mark.golden
def test_mantenimiento_ticket_repetido_no_crea_otra_solicitud(oxxo, golden):
    oxxo.encender()
    oxxo.h.repo.set("get_by_folio", {
        "request_code": "REPARE_000042", "row_number": 1, "status": "PENDING", "cliente": "OXXO",
    })
    msg = oxxo.correo(MAILBOX_MANTENIMIENTO, "mantenimiento", "msg-ox-repetido")
    oxxo.h.deliver(msg)
    assert "save_email_log_init" not in _nombres(oxxo.h)
    assert "insert_fila" not in _nombres(oxxo.h)
    assert oxxo.h.replies == []
    golden.check("oxxo_mantenimiento_ticket_repetido", oxxo.h.snapshot())


def test_mantenimiento_ticket_ganado_por_otro_proceso(oxxo):
    """El SELECT no lo vio pero el INSERT sí chocó con el folio: no hay
    solicitud nueva ni respuesta."""
    oxxo.encender()
    oxxo.h.repo.set("insert_fila", False)
    oxxo.h.deliver(oxxo.correo(MAILBOX_MANTENIMIENTO, "mantenimiento", "msg-ox-carrera"))
    assert oxxo.h.replies == []


def test_mismo_correo_notificado_dos_veces_se_omite(oxxo):
    oxxo.encender()
    oxxo.h.repo.set("email_init_exist", True)
    oxxo.h.deliver(oxxo.correo(MAILBOX_MANTENIMIENTO, "mantenimiento", "msg-ox-dup"))
    assert _nombres(oxxo.h) == ["email_init_exist"]
    assert oxxo.h.replies == []


@pytest.mark.golden
def test_mantenimiento_sin_ticket_va_a_revision(oxxo, golden):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_MANTENIMIENTO, "mantenimiento_sin_ticket", "msg-ox-sin-ticket")
    oxxo.h.deliver(msg)
    # No se inventa nada: ni solicitud ni filas.
    assert _nombres(oxxo.h) == ["email_init_exist"]
    [respuesta] = oxxo.h.snapshot()["replies"]
    assert "requiere revisión" in respuesta["body"]
    assert "falta_ticket" in respuesta["body"]
    golden.check("oxxo_mantenimiento_sin_ticket", oxxo.h.snapshot())


def test_correo_fuera_de_plantilla_se_ignora(oxxo):
    oxxo.encender()
    oxxo.h.deliver(oxxo.correo(MAILBOX_MANTENIMIENTO, "fuera_de_plantilla", "msg-ox-ajeno"))
    assert "save_email_log_init" not in _nombres(oxxo.h)
    assert oxxo.h.replies == []


def test_mantenimiento_en_hilo_existente_se_procesa_igual(oxxo):
    """Un correo posterior de la misma conversación entra por REPLY (inbound)."""
    oxxo.encender()
    oxxo.h.repo.set("conversation_exists", True)
    oxxo.h.deliver(oxxo.correo(MAILBOX_MANTENIMIENTO, "mantenimiento", "msg-ox-hilo"))
    assert "insert_fila" in _nombres(oxxo.h)
    assert len(oxxo.h.replies) == 1


# ------------------------------------------------------------ garantías: seguimiento

@pytest.mark.golden
def test_seguimiento_de_folio_existente_es_escalacion(oxxo, golden):
    oxxo.encender()
    oxxo.h.repo.set("get_by_folio", {
        "request_code": "REPARE_000042", "row_number": 2, "status": "PENDING", "cliente": "OXXO_GARANTIAS",
    })
    msg = oxxo.correo(MAILBOX_GARANTIAS, "seguimiento", "msg-og-escalacion")
    oxxo.h.deliver(msg)
    assert "save_email_log_init" not in _nombres(oxxo.h)
    assert "insert_fila" not in _nombres(oxxo.h)
    [marca] = oxxo.h.repo.calls_to("marcar_escalacion")
    assert marca["params"]["request_code"] == "REPARE_000042"
    assert marca["params"]["row_number"] == 2
    assert marca["params"]["nota"].startswith("ESCALACION 2026-03-02: se cumplió el tiempo")
    [respuesta] = oxxo.h.snapshot()["replies"]
    assert "requiere revisión" in respuesta["body"]
    assert "escalacion_garantia" in respuesta["body"]
    golden.check("oxxo_garantias_seguimiento_escalacion", oxxo.h.snapshot())


@pytest.mark.golden
def test_seguimiento_de_folio_inexistente_es_os_nueva_con_aviso(oxxo, golden):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_GARANTIAS, "seguimiento", "msg-og-nueva")
    oxxo.h.deliver(msg)
    [fila] = oxxo.h.repo.calls_to("insert_fila")
    assert fila["params"]["fila"]["folio"] == "GAR-0001"
    assert fila["params"]["fila"]["ticket_solicitud"] == "10000001"
    assert fila["params"]["fila"]["tipo_servicio"] == "GARANTIA"
    [respuesta] = oxxo.h.snapshot()["replies"]
    assert "no tenía solicitud en la base" in respuesta["body"]
    golden.check("oxxo_garantias_seguimiento_folio_nuevo", oxxo.h.snapshot())


@pytest.mark.golden
def test_seguimiento_sin_folio_va_a_revision(oxxo, golden):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_GARANTIAS, "seguimiento_sin_folio", "msg-og-sin-folio")
    oxxo.h.deliver(msg)
    assert _nombres(oxxo.h) == ["email_init_exist"]
    [respuesta] = oxxo.h.snapshot()["replies"]
    assert "falta_folio" in respuesta["body"]
    golden.check("oxxo_garantias_seguimiento_sin_folio", oxxo.h.snapshot())


# ------------------------------------------------------------ garantías: Excel

@pytest.mark.golden
def test_excel_inicial_registra_las_filas(oxxo, golden):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_GARANTIAS, "excel_init", "msg-og-excel", con_adjunto=True)
    oxxo.h.deliver(msg, [oxxo.xlsm(build_oxxo.EXCEL_INIT)])
    filas = oxxo.h.repo.calls_to("insert_fila")
    assert [f["params"]["row_number"] for f in filas] == [1, 2, 3]
    assert [f["params"]["fila"]["folio"] for f in filas] == ["OX-0001", "OX-0002", None]
    golden.check("oxxo_garantias_excel_inicial", oxxo.h.snapshot())


@pytest.mark.golden
def test_excel_con_4_os_cuadra(oxxo, golden):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_GARANTIAS, "excel_reply", "msg-og-4os", con_adjunto=True)
    oxxo.h.deliver(msg, [oxxo.xlsm(build_oxxo.EXCEL_REPLY)])
    assert len(oxxo.h.repo.calls_to("insert_fila")) == 4
    golden.check("oxxo_garantias_excel_4_os", oxxo.h.snapshot())


@pytest.mark.golden
def test_excel_con_conteo_distinto_va_a_revision(oxxo, golden):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_GARANTIAS, "excel_reply_conteo", "msg-og-5os", con_adjunto=True)
    oxxo.h.deliver(msg, [oxxo.xlsm(build_oxxo.EXCEL_REPLY)])
    assert "insert_fila" not in _nombres(oxxo.h)
    assert "save_email_log_init" not in _nombres(oxxo.h)
    [respuesta] = oxxo.h.snapshot()["replies"]
    assert "conteo_os_distinto (correo 5, Excel 4)" in respuesta["body"]
    golden.check("oxxo_garantias_excel_conteo_distinto", oxxo.h.snapshot())


def test_excel_inicial_sin_adjunto_va_a_revision(oxxo):
    oxxo.encender()
    oxxo.h.deliver(oxxo.correo(MAILBOX_GARANTIAS, "excel_init", "msg-og-sin-adjunto"))
    [respuesta] = oxxo.h.snapshot()["replies"]
    assert "falta_excel" in respuesta["body"]
    assert "insert_fila" not in _nombres(oxxo.h)


def test_respuesta_sin_adjunto_es_conversacion(oxxo):
    oxxo.encender()
    oxxo.h.deliver(oxxo.correo(MAILBOX_GARANTIAS, "excel_reply", "msg-og-re-sin-adjunto"))
    assert oxxo.h.replies == []
    assert "insert_fila" not in _nombres(oxxo.h)


def test_excel_ilegible_va_a_revision(oxxo):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_GARANTIAS, "excel_init", "msg-og-roto", con_adjunto=True)
    oxxo.h.deliver(msg, [("roto.xlsm", b"no es un excel")])
    [respuesta] = oxxo.h.snapshot()["replies"]
    assert "excel_ilegible" in respuesta["body"]
    assert "insert_fila" not in _nombres(oxxo.h)


def test_excel_sin_cantidad_en_el_cuerpo_no_valida_conteo(oxxo):
    oxxo.encender()
    msg = oxxo.correo(MAILBOX_GARANTIAS, "excel_init", "msg-og-sin-n", con_adjunto=True)
    oxxo.h.deliver(msg, [oxxo.xlsm(build_oxxo.EXCEL_REPLY)])
    assert len(oxxo.h.repo.calls_to("insert_fila")) == 4


def test_excel_con_folios_repetidos_recalcula_la_solicitud(oxxo):
    oxxo.encender()
    oxxo.h.repo.queue("insert_fila", [True, False, True])
    msg = oxxo.correo(MAILBOX_GARANTIAS, "excel_init", "msg-og-folio-dup", con_adjunto=True)
    oxxo.h.deliver(msg, [oxxo.xlsm(build_oxxo.EXCEL_INIT)])
    assert "update_email_request" in _nombres(oxxo.h)
    [respuesta] = oxxo.h.snapshot()["replies"]
    assert "<b>2</b>" in respuesta["body"]


# ------------------------------------------------------------ bot

@pytest.mark.golden
@pytest.mark.parametrize("comando", ["ayuda", "estatus", "sin_folio"])
def test_comando_bot(oxxo, golden, comando):
    oxxo.encender()
    msg = oxxo.comando(MAILBOX_GARANTIAS, oxxo.correos["comandos"][comando], f"msg-og-bot-{comando}")
    oxxo.h.deliver(msg)
    assert len(oxxo.h.replies) == 1
    golden.check(f"oxxo_hilo_bot_{comando}", oxxo.h.snapshot())


def test_comando_bot_apagado(oxxo):
    msg = oxxo.comando(MAILBOX_GARANTIAS, "bot.ayuda", "msg-og-bot-apagado")
    oxxo.h.deliver(msg)
    assert oxxo.h.replies == []
    assert _nombres(oxxo.h) == []


def test_bot_estatus_se_acota_al_cliente_del_buzon(oxxo):
    oxxo.encender()
    msg = oxxo.comando(MAILBOX_MANTENIMIENTO, "bot.estatus REPARE_000042", "msg-ox-bot")
    oxxo.h.deliver(msg)
    [pedido] = oxxo.h.repo.calls_to("get_request")
    assert pedido["params"] == {"request_code": "REPARE_000042", "customer": "oxxo"}
    [estatus] = oxxo.h.repo.calls_to("bot_status")
    assert estatus["params"]["customer"] == "oxxo"
