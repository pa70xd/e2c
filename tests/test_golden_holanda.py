"""Golden tests de Holanda (hilo único; las solicitudes se resuelven por CASO2
o por folio REPARE_xxxxxx, no por conversación).

Regenerar: ``pytest tests/test_golden_holanda.py --update-golden``.
"""

import pytest

from tests.support.scenarios import GLOBAL_ROWS, bot_command, inbound, outbound

CLIENTE = "holanda"
CONV = "conv-holanda-001"
EXCEL_INIT = "Casos REPARE 02032026.xlsx"
EXCEL_OS = "Casos REPARE OS.xlsx"


@pytest.fixture
def fx(fixtures_for):
    return fixtures_for(CLIENTE)


@pytest.mark.golden
def test_correo_nuevo_con_excel(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["init"], "msg-holanda-init", CONV)
    result = harness.deliver(msg, [fx.xlsx(EXCEL_INIT)])
    assert result == "recibido"
    golden.check("holanda_correo_nuevo_con_excel", harness.snapshot())


@pytest.mark.golden
def test_correo_nuevo_con_equipo_abierto_marca_duplicado(harness, fx, golden):
    """El histórico de Postgres ya tiene un caso sin OS para CONG00002."""
    harness.repo.set("get_equipos_con_caso_abierto", ["CONG00002"])
    msg = inbound(CLIENTE, fx.correos["init"], "msg-holanda-histdup", CONV)
    harness.deliver(msg, [fx.xlsx(EXCEL_INIT)])
    golden.check("holanda_correo_nuevo_duplicado_historico", harness.snapshot())


@pytest.mark.golden
def test_asunto_ajeno_no_responde(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["fuera_de_asunto"], "msg-holanda-ajeno", CONV)
    harness.deliver(msg, [fx.xlsx(EXCEL_INIT)])
    assert harness.replies == []
    golden.check("holanda_asunto_ajeno", harness.snapshot())


@pytest.mark.golden
def test_hilo_outbound_con_os(harness, fx, golden):
    msg = outbound(CLIENTE, fx.correos["outbound"], "msg-holanda-out", CONV)
    harness.deliver(msg, [fx.xlsx(EXCEL_OS)])
    golden.check("holanda_hilo_outbound_os", harness.snapshot())


@pytest.mark.golden
def test_hilo_outbound_cancelado_no_se_recalcula(harness, fx, golden):
    harness.repo.set("get_email_request_status", "CANCELLED")
    msg = outbound(CLIENTE, fx.correos["outbound"], "msg-holanda-out-canc", CONV)
    harness.deliver(msg, [fx.xlsx(EXCEL_OS)])
    assert "update_email_request" not in harness.repo.names()
    golden.check("holanda_hilo_outbound_cancelado", harness.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize("comando", ["ayuda", "estatus", "cancelar", "finalizar", "sin_folio", "global"])
def test_hilo_comando_bot(harness, fx, golden, comando):
    if comando == "global":
        harness.repo.set("global_status", GLOBAL_ROWS)
    msg = bot_command(
        CLIENTE,
        fx.correos["outbound"]["subject"],
        fx.correos["comandos"][comando],
        f"msg-holanda-bot-{comando}",
        CONV,
    )
    harness.deliver(msg)
    assert len(harness.replies) == 1
    golden.check(f"holanda_hilo_bot_{comando}", harness.snapshot())
