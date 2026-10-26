"""Golden tests de Imbera (buzón multi-cliente, "Lay Out Repare").

Regenerar: ``pytest tests/unit_imbera/test_golden_imbera.py --update-golden``.
"""

import pytest

from tests.support.scenarios import bot_command, inbound, outbound

CLIENTE = "imbera"
CONV = "conv-imbera-001"


@pytest.fixture
def fx(fixtures_for):
    return fixtures_for(CLIENTE)



@pytest.mark.golden
def test_correo_nuevo_ruta(harness_layout, fx, golden):
    msg = inbound(CLIENTE, fx.correos["init_ruta"], "msg-imbera-init", CONV)
    assert harness_layout.deliver(msg, [fx.xlsx("lay_out_repare_ruta.xlsx")]) == "recibido"

    coolers = [c["params"]["parametros"] for c in harness_layout.repo.calls_to("send_email_coolers")]
    assert [c["status"] for c in coolers] == ["PENDING", "PENDING", "REJECTED", "REJECTED"]
    assert {c["cbu"] for c in coolers} == {"JUMEX"}
    assert {c["folio"] for c in coolers} == {"REP-261026_1"}
    assert all(c["gestion_observaciones"] is None or "Garantía" not in c["gestion_observaciones"] for c in coolers)
    golden.check("imbera_correo_nuevo_ruta", harness_layout.snapshot())


@pytest.mark.golden
def test_correo_nuevo_garantia(harness_layout, fx, golden):
    msg = inbound(CLIENTE, fx.correos["init_garantia"], "msg-imbera-garantia", CONV)
    harness_layout.deliver(msg, [fx.xlsx("lay_out_repare_garantia.xlsx"), fx.xlsx("factura.pdf")])

    (cooler,) = [c["params"]["parametros"] for c in harness_layout.repo.calls_to("send_email_coolers")]
    assert cooler["ticket_solicitud"] == "123456"
    assert cooler["gestion_observaciones"].startswith(
        "Garantía: SI (asunto,factura_pdf,equipo_nuevo_danado)"
    )
    golden.check("imbera_correo_nuevo_garantia", harness_layout.snapshot())


@pytest.mark.golden
def test_seguimiento_sin_excel_no_crea(harness_layout, fx, golden):
    msg = inbound(CLIENTE, fx.correos["seguimiento"], "msg-imbera-seg", CONV)
    harness_layout.deliver(msg)
    assert harness_layout.replies == []
    assert "save_email_log_init" not in harness_layout.repo.names()
    golden.check("imbera_seguimiento_sin_excel", harness_layout.snapshot())


@pytest.mark.golden
def test_hilo_inbound_reenvio(harness_layout, fx, golden):
    msg = inbound(CLIENTE, fx.correos["inbound_reenvio"], "msg-imbera-reenvio", CONV)
    harness_layout.deliver(msg, [fx.xlsx("lay_out_repare_reenvio.xlsx")])
    (call,) = harness_layout.repo.calls_to("insert_update_cooler")
    # Serie nueva: va después de las filas existentes, sin pisar la fila 1.
    assert call["params"]["parametros"]["row_number"] == 4
    golden.check("imbera_hilo_inbound_reenvio", harness_layout.snapshot())


@pytest.mark.golden
def test_hilo_outbound_os_excel(harness_layout, fx, golden):
    msg = outbound(CLIENTE, fx.correos["outbound_excel"], "msg-imbera-out-xlsx", CONV)
    harness_layout.deliver(msg, [fx.xlsx("respuesta_os.xlsx")])
    calls = harness_layout.repo.calls_to("update_os_por_serie")
    assert [(c["params"]["serie"], c["params"]["os_value"]) for c in calls] == [("SER-IMB-0001", "4031000001")]
    golden.check("imbera_hilo_outbound_os_excel", harness_layout.snapshot())


@pytest.mark.golden
def test_hilo_outbound_os_en_texto(harness_layout, fx, golden):
    msg = outbound(CLIENTE, fx.correos["outbound_texto"], "msg-imbera-out-txt", CONV)
    harness_layout.deliver(msg)
    (call,) = harness_layout.repo.calls_to("update_os_por_fila")
    assert call["params"] == {"request_code": "REPARE_000042", "row_number": 1, "os_value": "4031000002"}
    golden.check("imbera_hilo_outbound_os_texto", harness_layout.snapshot())


@pytest.mark.golden
def test_hilo_outbound_texto_con_series(harness_layout, fx, golden):
    harness_layout.repo.set("get_cooler_rows", [
        {"row_number": 1, "serie_fabricante": "SER-IMB-0001", "serie_dnn_bnf": None, "status": "PENDING"},
        {"row_number": 4, "serie_fabricante": "SER-IMB-0004", "serie_dnn_bnf": None, "status": "PENDING"},
    ])
    msg = outbound(CLIENTE, fx.correos["outbound_texto_series"], "msg-imbera-out-series", CONV)
    harness_layout.deliver(msg)
    pares = [(c["params"]["row_number"], c["params"]["os_value"]) for c in harness_layout.repo.calls_to("update_os_por_fila")]
    assert pares == [(4, "4031000005"), (1, "4031000006")]
    golden.check("imbera_hilo_outbound_texto_series", harness_layout.snapshot())


@pytest.mark.golden
def test_hilo_outbound_texto_ambiguo_no_concilia(harness_layout, fx, golden):
    harness_layout.repo.set("get_cooler_rows", [
        {"row_number": 1, "serie_fabricante": "SER-IMB-0001", "serie_dnn_bnf": None, "status": "PENDING"},
        {"row_number": 2, "serie_fabricante": "SER-IMB-0002", "serie_dnn_bnf": None, "status": "PENDING"},
    ])
    msg = outbound(CLIENTE, fx.correos["outbound_texto"], "msg-imbera-out-amb", CONV)
    harness_layout.deliver(msg)
    assert "update_os_por_fila" not in harness_layout.repo.names()
    assert harness_layout.replies == []
    golden.check("imbera_hilo_outbound_texto_ambiguo", harness_layout.snapshot())


@pytest.mark.golden
def test_hilo_outbound_espera_de_pieza_es_no_os(harness_layout, fx, golden):
    msg = outbound(CLIENTE, fx.correos["outbound_espera_pieza"], "msg-imbera-out-pieza", CONV)
    harness_layout.deliver(msg)
    assert not {"update_os_por_fila", "update_os_por_serie", "get_cooler_rows"} & set(harness_layout.repo.names())
    assert harness_layout.replies == []
    golden.check("imbera_hilo_outbound_espera_pieza", harness_layout.snapshot())


@pytest.mark.golden
def test_hilo_outbound_cancelado_no_se_recalcula(harness_layout, fx, golden):
    harness_layout.repo.set("get_email_request_status", "CANCELLED")
    msg = outbound(CLIENTE, fx.correos["outbound_texto"], "msg-imbera-out-canc", CONV)
    harness_layout.deliver(msg)
    assert "update_email_request" not in harness_layout.repo.names()
    golden.check("imbera_hilo_outbound_cancelado", harness_layout.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize("comando", ["ayuda", "estatus"])
def test_hilo_comando_bot(harness_layout, fx, golden, comando):
    msg = bot_command(
        CLIENTE,
        fx.correos["outbound_texto"]["subject"],
        fx.correos["comandos"][comando],
        f"msg-imbera-bot-{comando}",
        CONV,
    )
    harness_layout.deliver(msg)
    assert len(harness_layout.replies) == 1
    golden.check(f"imbera_hilo_bot_{comando}", harness_layout.snapshot())
