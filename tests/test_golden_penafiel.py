"""Golden tests de Penafiel (misma base que Danone, con su propio lector,
reglas y repositorio ``repository.penafiel``).

Regenerar: ``pytest tests/test_golden_penafiel.py --update-golden``.
"""

import pytest

from tests.support.scenarios import GLOBAL_ROWS, bot_command, inbound, outbound

CLIENTE = "penafiel"
CONV = "conv-penafiel-001"


@pytest.fixture
def fx(fixtures_for):
    return fixtures_for(CLIENTE)


@pytest.mark.golden
def test_correo_nuevo_con_excel(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["init"], "msg-penafiel-init", CONV)
    result = harness.deliver(msg, [fx.xlsx("solicitud_servicios.xlsx")])
    assert result == "recibido"
    golden.check("penafiel_correo_nuevo_con_excel", harness.snapshot())


@pytest.mark.golden
def test_hilo_inbound_con_excel(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["inbound"], "msg-penafiel-in", CONV)
    harness.deliver(msg, [fx.xlsx("ampliacion_servicios.xlsx")])
    golden.check("penafiel_hilo_inbound_con_excel", harness.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize(
    "estado, nombre",
    [("IN_PROGRESS", "en_proceso"), ("COMPLETED", "completa")],
)
def test_hilo_outbound_con_os(harness, fx, golden, estado, nombre):
    harness.repo.set("get_email_request_status", estado)
    msg = outbound(CLIENTE, fx.correos["outbound"], f"msg-penafiel-out-{nombre}", CONV)
    harness.deliver(msg, [fx.xlsx("respuesta_os.xlsx")])
    golden.check(f"penafiel_hilo_outbound_os_{nombre}", harness.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize("comando", ["ayuda", "estatus", "cancelar", "finalizar", "global"])
def test_hilo_comando_bot(harness, fx, golden, comando):
    if comando == "global":
        harness.repo.set("get_email_request_global", GLOBAL_ROWS)
    msg = bot_command(
        CLIENTE,
        fx.correos["outbound"]["subject"],
        fx.correos["comandos"][comando],
        f"msg-penafiel-bot-{comando}",
        CONV,
    )
    harness.deliver(msg)
    assert len(harness.replies) == 1
    golden.check(f"penafiel_hilo_bot_{comando}", harness.snapshot())
