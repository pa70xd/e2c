"""Golden tests de Danone: congelan el comportamiento ACTUAL (incluidos los
bugs conocidos de okf/riesgos/bugs.md) antes de refactorizar.

Regenerar: ``pytest tests/test_golden_danone.py --update-golden``.
"""

import pytest

from tests.support.scenarios import GLOBAL_ROWS, bot_command, inbound, outbound

CLIENTE = "danone"
CONV = "conv-danone-001"


@pytest.fixture
def fx(fixtures_for):
    return fixtures_for(CLIENTE)


@pytest.mark.golden
def test_correo_nuevo_con_excel(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["init"], "msg-danone-init", CONV)
    result = harness.deliver(msg, [fx.xlsx("solicitud_servicios.xlsx")])
    assert result == "recibido"
    golden.check("danone_correo_nuevo_con_excel", harness.snapshot())


@pytest.mark.golden
def test_correo_nuevo_sin_proposito_no_responde(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["sin_proposito"], "msg-danone-sinprop", "conv-danone-002")
    harness.deliver(msg, [fx.xlsx("solicitud_servicios.xlsx")])
    assert harness.replies == []
    golden.check("danone_correo_nuevo_sin_proposito", harness.snapshot())


@pytest.mark.golden
def test_correo_nuevo_ya_procesado_se_omite(harness, fx, golden):
    harness.repo.set("email_init_exist", True)
    msg = inbound(CLIENTE, fx.correos["init"], "msg-danone-dup", "conv-danone-003")
    harness.deliver(msg, [fx.xlsx("solicitud_servicios.xlsx")])
    assert harness.replies == []
    assert "save_email_log_init" not in harness.repo.names()
    golden.check("danone_correo_nuevo_ya_procesado", harness.snapshot())


@pytest.mark.golden
def test_hilo_inbound_con_excel(harness, fx, golden):
    msg = inbound(CLIENTE, fx.correos["inbound"], "msg-danone-in", CONV)
    harness.deliver(msg, [fx.xlsx("ampliacion_servicios.xlsx")])
    golden.check("danone_hilo_inbound_con_excel", harness.snapshot())


@pytest.mark.golden
def test_correo_sin_prefijo_en_conversacion_existente_se_trata_como_respuesta(harness, fx, golden):
    """service.py: solo el primer mensaje del hilo abre solicitud; un correo
    posterior sin 'RE:' pasa al flujo de respuesta."""
    harness.repo.set("conversation_exists", True)
    msg = inbound(CLIENTE, fx.correos["init"], "msg-danone-sinre", CONV)
    harness.deliver(msg, [fx.xlsx("ampliacion_servicios.xlsx")])
    assert "save_email_log_init" not in harness.repo.names()
    assert "insert_update_cooler" in harness.repo.names()
    golden.check("danone_conversacion_existente_sin_prefijo", harness.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize(
    "estado, nombre",
    [("IN_PROGRESS", "en_proceso"), ("COMPLETED", "completa")],
)
def test_hilo_outbound_con_os(harness, fx, golden, estado, nombre):
    harness.repo.set("get_email_request_status", estado)
    msg = outbound(CLIENTE, fx.correos["outbound"], f"msg-danone-out-{nombre}", CONV)
    harness.deliver(msg, [fx.xlsx("respuesta_os.xlsx")])
    golden.check(f"danone_hilo_outbound_os_{nombre}", harness.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize("comando", ["ayuda", "estatus", "cancelar", "finalizar", "global", "desconocido"])
def test_hilo_comando_bot(harness, fx, golden, comando):
    if comando == "global":
        harness.repo.set("get_email_request_global", GLOBAL_ROWS)
    msg = bot_command(
        CLIENTE,
        fx.correos["bot"]["subject"],
        fx.correos["comandos"][comando],
        f"msg-danone-bot-{comando}",
        CONV,
    )
    harness.deliver(msg)
    # Un comando que no está en palabras_reservadas ni siquiera se detecta como
    # comando: el flujo termina sin responder (el `case _` de parse es inalcanzable).
    assert len(harness.replies) == (0 if comando == "desconocido" else 1)
    golden.check(f"danone_hilo_bot_{comando}", harness.snapshot())


@pytest.mark.golden
def test_hilo_mensaje_del_bot_no_responde(harness, fx, golden):
    """REPARE -> REPARE con la frase de plantilla ('bot'): se ignora."""
    msg = bot_command(CLIENTE, fx.correos["bot"]["subject"], fx.correos["bot"]["body"], "msg-danone-bot-bot", CONV)
    harness.deliver(msg)
    assert harness.replies == []
    golden.check("danone_hilo_mensaje_del_bot", harness.snapshot())


@pytest.mark.golden
def test_hilo_sin_solicitud_asociada_no_responde(harness, fx, golden):
    harness.repo.set("email_reply_validate", None)
    msg = outbound(CLIENTE, fx.correos["outbound"], "msg-danone-out-huerfano", "conv-danone-999")
    harness.deliver(msg, [fx.xlsx("respuesta_os.xlsx")])
    assert harness.replies == []
    golden.check("danone_hilo_sin_solicitud", harness.snapshot())
