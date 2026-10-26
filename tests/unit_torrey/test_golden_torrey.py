"""Golden tests de Torrey (garantías con "Lay Out Repare" variante B).

Regenerar: ``pytest tests/unit_torrey/test_golden_torrey.py --update-golden``.
"""

import pytest

from tests.support.scenarios import bot_command, inbound, outbound

CLIENTE = "torrey"
CONV = "conv-torrey-001"
LAYOUT = "lay_out_repare_torrey.xlsx"


@pytest.fixture
def fx(fixtures_for):
    return fixtures_for(CLIENTE)


def _coolers(harness):
    return [c["params"]["parametros"] for c in harness.repo.calls_to("send_email_coolers")]


@pytest.mark.golden
def test_correo_nuevo_garantia_con_hielo(harness_layout, fx, golden):
    msg = inbound(CLIENTE, fx.correos["init"], "msg-torrey-init", CONV)
    assert harness_layout.deliver(msg, [fx.xlsx(LAYOUT), fx.xlsx("factura.pdf")]) == "recibido"

    coolers = _coolers(harness_layout)
    # Fila basura descartada; la máquina de hielo va al cliente IMBERA.
    assert [(c["serie_fabricante"], c["cliente"]) for c in coolers] == [
        ("SER-TOR-0001", "TORREY"),
        ("SER-TOR-0002", "IMBERA"),
    ]
    assert all(c["gestion_observaciones"].startswith("Garantía: SI") for c in coolers)
    (request,) = harness_layout.repo.calls_to("send_email_request")
    assert request["params"]["parametros"]["customer"] == "torrey"
    # Se contesta en el hilo de Torrey.
    (reply,) = harness_layout.replies
    assert reply["in_reply_to"] == "msg-torrey-init"
    assert "se generan para el cliente IMBERA" in reply["body"]
    # PII: el nombre de quien recibe no viaja en la respuesta.
    assert "RECIBE EJEMPLO" not in reply["body"]
    golden.check("torrey_correo_nuevo_garantia_con_hielo", harness_layout.snapshot())


@pytest.mark.golden
def test_correo_nuevo_sin_factura_avisa(harness_layout, fx, golden):
    msg = inbound(CLIENTE, fx.correos["init"], "msg-torrey-sinpdf", CONV)
    harness_layout.deliver(msg, [fx.xlsx(LAYOUT)])
    (reply,) = harness_layout.replies
    assert "No se encontró la factura en PDF" in reply["body"]
    golden.check("torrey_correo_nuevo_sin_factura", harness_layout.snapshot())


@pytest.mark.golden
def test_hilo_outbound_os_en_texto(harness_layout, fx, golden):
    harness_layout.repo.set("get_cooler_rows", [
        {"row_number": 1, "serie_fabricante": "SER-TOR-0001", "serie_dnn_bnf": None, "status": "ACCEPTED"},
        {"row_number": 2, "serie_fabricante": "SER-TOR-0002", "serie_dnn_bnf": None, "status": "PENDING"},
    ])
    msg = outbound(CLIENTE, fx.correos["outbound_texto"], "msg-torrey-out", CONV)
    harness_layout.deliver(msg)
    (call,) = harness_layout.repo.calls_to("update_os_por_fila")
    assert call["params"]["row_number"] == 2
    golden.check("torrey_hilo_outbound_os_texto", harness_layout.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize("comando", ["ayuda", "cancelar"])
def test_hilo_comando_bot(harness_layout, fx, golden, comando):
    msg = bot_command(
        CLIENTE,
        fx.correos["outbound_texto"]["subject"],
        fx.correos["comandos"][comando],
        f"msg-torrey-bot-{comando}",
        CONV,
    )
    harness_layout.deliver(msg)
    assert len(harness_layout.replies) == 1
    golden.check(f"torrey_hilo_bot_{comando}", harness_layout.snapshot())
