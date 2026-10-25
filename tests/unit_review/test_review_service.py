"""review/ de punta a punta por ``src.service.processMail`` (harness offline):
un inbound sin Excel con proveedor externo se atiende en review y no en el
parser; con el default regex el camino es el de siempre."""

import pytest

from classifier import registry
from classifier.contracts import CANCELAR, CANCELAR_FILAS, GateResult, RowExtraida
from tests.support.emails import CLIENTES, REPARE, make_email

CLIENTE = "danone"
CORREO = {"subject": "RE: Solicitud de servicio", "body": "Cancelen por favor las filas 1 y 3."}
FILAS = [
    {"row_number": 1, "serie_fabricante": "FAB-0001", "serie_dnn_bnf": None, "status": "PENDING"},
    {"row_number": 3, "serie_fabricante": "FAB-0003", "serie_dnn_bnf": None, "status": "ACCEPTED"},
]


@pytest.fixture
def externo(monkeypatch):
    from types import SimpleNamespace

    modulo = SimpleNamespace(
        NAME="fake",
        gate=lambda s, b, ctx: GateResult(es_os=True, tipo_evento=CANCELAR_FILAS, confidence=0.9),
        extract=lambda b, ctx, gate=None: [RowExtraida(accion=CANCELAR, row_number=1), RowExtraida(accion=CANCELAR, row_number=3)],
    )
    real = registry.cargar
    monkeypatch.setattr(registry, "cargar", lambda n: modulo if n == "fake" else real(n))
    monkeypatch.setattr(registry, "get_redactor", lambda: (lambda t, conservar=(): t))
    monkeypatch.setenv("CLASSIFIER_GATE", "fake")
    monkeypatch.setenv("CLASSIFIER_EXTRACT", "fake")


def inbound(cliente, correo, message_id, conversation_id):
    """Cliente -> REPARE en el hilo, SIN Excel (``scenarios.inbound`` marca
    adjuntos)."""
    return make_email(
        subject=correo["subject"],
        body=correo["body"],
        sender=CLIENTES[cliente],
        to=[REPARE[cliente]],
        conversation_id=conversation_id,
        message_id=message_id,
        has_attachments=False,
    )


def _preparar(harness):
    harness.repo.set("conversation_exists", True)
    harness.repo.set("get_cooler_rows", FILAS)
    harness.repo.set(
        "cancel_pending_cooler_row",
        lambda request_code, row_number: [{"request_code": request_code, "row_number": row_number}],
    )


def test_inbound_sin_excel_con_extract_externo_aplica_y_avisa(harness, externo):
    _preparar(harness)
    msg = inbound(CLIENTE, CORREO, "msg-review-1", "conv-review-1")
    assert harness.deliver(msg) == "recibido"

    nombres = harness.repo.names()
    assert "get_cooler_rows" in nombres
    assert [c["params"]["row_number"] for c in harness.repo.calls_to("cancel_pending_cooler_row")] == [1]
    assert "update_email_request" in nombres
    assert "insert_update_cooler" not in nombres  # el parser no corrió

    # 1) aviso a REPARE con las filas en revisión, 2) respuesta del hilo.
    assert len(harness.replies) == 2
    aviso, respuesta = (r["body"] for r in harness.replies)
    assert "requiere revisión" in aviso and "FAB-0003" in aviso and "fila_accepted" in aviso
    assert "FAB-0001" not in aviso
    assert "Aplicado" in respuesta and "FAB-0001" in respuesta and "En revisión" in respuesta
    for r in harness.replies:
        assert r["in_reply_to"] == "msg-review-1"


def test_mismo_correo_con_default_regex_va_al_parser(harness, monkeypatch):
    monkeypatch.delenv("CLASSIFIER_GATE", raising=False)
    monkeypatch.delenv("CLASSIFIER_EXTRACT", raising=False)
    _preparar(harness)
    msg = inbound(CLIENTE, CORREO, "msg-review-2", "conv-review-2")
    harness.deliver(msg)

    nombres = harness.repo.names()
    assert "get_cooler_rows" not in nombres
    assert "cancel_pending_cooler_row" not in nombres
    assert all("requiere revisión" not in r["body"] for r in harness.replies)


@pytest.mark.parametrize("gate, extract, consulta", [
    (None, None, False),          # default: ninguna consulta nueva por correo
    ("regex", "regex", False),
    ("fake", "regex", True),      # basta un proveedor externo
    ("regex", "fake", True),
], ids=["default", "regex_explicito", "gate_externo", "extract_externo"])
def test_cargador_solo_con_proveedor_externo(harness, externo, monkeypatch, gate, extract, consulta):
    for var, valor in (("CLASSIFIER_GATE", gate), ("CLASSIFIER_EXTRACT", extract)):
        if valor is None:
            monkeypatch.delenv(var, raising=False)
        else:
            monkeypatch.setenv(var, valor)
    _preparar(harness)
    harness.deliver(inbound(CLIENTE, CORREO, f"msg-cargador-{gate}-{extract}", "conv-cargador"))

    assert ("get_cooler_rows" in harness.repo.names()) is consulta
