"""Golden tests de Heineken: dos flujos por asunto, D2D (un hilo por día =
una solicitud) y RUTA (Mantenimiento Ferguez, hilo eterno, resuelve por folio).

Regenerar: ``pytest tests/test_golden_heineken.py --update-golden``.
"""

import pytest

from tests.support.scenarios import GLOBAL_ROWS, bot_command, inbound, outbound

CLIENTE = "heineken"
CONV_D2D = "conv-heineken-d2d-001"
CONV_RUTA = "conv-heineken-ruta-001"


@pytest.fixture
def fx(fixtures_for):
    return fixtures_for(CLIENTE)


@pytest.mark.golden
def test_d2d_correo_nuevo_con_excel(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["d2d_init"], "msg-hnk-d2d-init", CONV_D2D)
    result = harness.deliver(msg, [fx.xlsx("precarga_d2d.xlsx")])
    assert result == "recibido"
    golden.check("heineken_d2d_correo_nuevo_con_excel", harness.snapshot())


@pytest.mark.golden
def test_d2d_reenvio_actualiza_la_solicitud_del_hilo(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["d2d_reenvio"], "msg-hnk-d2d-in", CONV_D2D)
    harness.deliver(msg, [fx.xlsx("precarga_d2d.xlsx")])
    golden.check("heineken_d2d_hilo_inbound_reenvio", harness.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize(
    "estado, nombre",
    [("IN_PROGRESS", "en_proceso"), ("COMPLETED", "completa")],
)
def test_d2d_hilo_outbound_con_os(harness, fx, golden, estado, nombre):
    harness.repo.set("get_email_request_status", estado)
    msg = outbound(CLIENTE, fx.correos["d2d_outbound"], f"msg-hnk-d2d-out-{nombre}", CONV_D2D)
    harness.deliver(msg, [fx.xlsx("respuesta_d2d.xlsx")])
    golden.check(f"heineken_d2d_hilo_outbound_os_{nombre}", harness.snapshot())


@pytest.mark.golden
def test_d2d_reenvio_reutiliza_la_serie_generica_pendiente(harness, fx, golden):
    harness.repo.queue("serie_generica_pendiente", ["HEI2026010199001"])
    msg = inbound(CLIENTE, fx.correos["d2d_reenvio"], "msg-hnk-d2d-pend", CONV_D2D)
    harness.deliver(msg, [fx.xlsx("precarga_d2d.xlsx")])
    golden.check("heineken_d2d_reenvio_serie_pendiente", harness.snapshot())


@pytest.mark.golden
def test_ruta_correo_nuevo_con_excel(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["ruta_init"], "msg-hnk-ruta-init", CONV_RUTA)
    result = harness.deliver(msg, [fx.xlsx("mantenimiento_ferguez.xlsx")])
    assert result == "recibido"
    golden.check("heineken_ruta_correo_nuevo_con_excel", harness.snapshot())


@pytest.mark.golden
def test_ruta_hilo_outbound_con_os(harness, fx, golden):
    msg = outbound(CLIENTE, fx.correos["ruta_outbound"], "msg-hnk-ruta-out", CONV_RUTA)
    harness.deliver(msg, [fx.xlsx("respuesta_ruta.xlsx")])
    golden.check("heineken_ruta_hilo_outbound_os", harness.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize(
    "comando, asunto, conversacion",
    [
        ("estatus_d2d", "d2d_outbound", CONV_D2D),
        ("cancelar_d2d", "d2d_outbound", CONV_D2D),
        ("estatus_ruta", "ruta_outbound", CONV_RUTA),
        ("ayuda", "d2d_outbound", CONV_D2D),
        ("global", "d2d_outbound", CONV_D2D),
    ],
)
def test_hilo_comando_bot(harness, fx, golden, comando, asunto, conversacion):
    if comando == "global":
        harness.repo.set("global_status", GLOBAL_ROWS)
    msg = bot_command(
        CLIENTE,
        fx.correos[asunto]["subject"],
        fx.correos["comandos"][comando],
        f"msg-hnk-bot-{comando}",
        conversacion,
    )
    harness.deliver(msg)
    assert len(harness.replies) == 1
    golden.check(f"heineken_hilo_bot_{comando}", harness.snapshot())
