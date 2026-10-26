"""Aviso a REPARE por clasificación dudosa (gate externo con confianza baja)."""

import asyncio
from types import SimpleNamespace

import pytest

import review
from classifier import registry
from classifier.contracts import (
    CANCELAR_FILAS,
    ETAPA_REPLY,
    MOTIVO_CLASIFICACION_DUDOSA,
    GateResult,
    RowExtraida,
    ThreadCtx,
)
from classifier.contracts import Decision
from tests.support.emails import CLIENTES, REPARE, make_email

DUDOSA = Decision(
    GateResult(True, "modificar_filas", 1.0), "regex", "regex",
    motivo_revision=MOTIVO_CLASIFICACION_DUDOSA,
)
NORMAL = Decision(GateResult(True, "modificar_filas", 1.0), "regex", "regex")


def _ctx(direccion="inbound"):
    return ThreadCtx(etapa=ETAPA_REPLY, customer="danone", direccion=direccion, request_code="RC-9")


SIN_EXCEL = SimpleNamespace(has_attachments=False)
CON_EXCEL = SimpleNamespace(has_attachments=True)


@pytest.mark.parametrize("decision, ctx, email, esperado", [
    (DUDOSA, _ctx(), SIN_EXCEL, True),
    (DUDOSA, _ctx(), CON_EXCEL, False),            # con Excel decide el Excel
    (DUDOSA, _ctx("outbound"), SIN_EXCEL, False),  # lo que escribe REPARE no se avisa
    (DUDOSA, _ctx("reply_to_bot"), SIN_EXCEL, False),
    (NORMAL, _ctx(), SIN_EXCEL, False),
    (None, _ctx(), SIN_EXCEL, False),
    (DUDOSA, None, SIN_EXCEL, False),
], ids=["inbound", "con_excel", "outbound", "bot", "sin_duda", "sin_decision", "sin_ctx"])
def test_debe_avisar_duda(decision, ctx, email, esperado):
    assert review.debe_avisar_duda(decision, ctx, email) is esperado


def test_debe_atender_nunca_con_duda(monkeypatch):
    monkeypatch.setenv("CLASSIFIER_EXTRACT", "fake")
    dudosa = Decision(
        GateResult(True, CANCELAR_FILAS, 0.9), "fake", "fake",
        rows=(RowExtraida("cancelar", row_number=1),),
        filas_aplicables=(RowExtraida("cancelar", row_number=1),),
        motivo_revision=MOTIVO_CLASIFICACION_DUDOSA,
    )
    assert not review.debe_atender(dudosa, _ctx(), SIN_EXCEL)


def test_avisar_duda_envia_requiere_revision():
    enviados = []

    async def enviar(m):
        enviados.append(m)

    assert asyncio.run(review.avisar_duda(DUDOSA, _ctx(), enviar)) is True
    assert len(enviados) == 1
    assert "requiere revisión" in enviados[0] and "Clasificación dudosa" in enviados[0]
    assert "RC-9" in enviados[0]


def test_avisar_duda_no_propaga_error_de_envio(capsys):
    async def enviar(m):
        raise RuntimeError("graph caído con texto")

    assert asyncio.run(review.avisar_duda(DUDOSA, _ctx(), enviar)) is False
    out = capsys.readouterr().out
    assert "RuntimeError" in out and "texto" not in out


# ------------------------------------------------------------ de punta a punta
CLIENTE = "danone"
FILAS = [{"row_number": 1, "serie_fabricante": "FAB-0001", "serie_dnn_bnf": None, "status": "PENDING"}]


@pytest.fixture
def dudoso(monkeypatch):
    llamadas = []
    modulo = SimpleNamespace(
        NAME="fake",
        gate=lambda s, b, ctx: GateResult(es_os=True, tipo_evento=CANCELAR_FILAS, confidence=0.3),
        extract=lambda b, ctx, gate=None: llamadas.append(gate) or [RowExtraida(accion="cancelar", row_number=1)],
    )
    real = registry.cargar
    monkeypatch.setattr(registry, "cargar", lambda n: modulo if n == "fake" else real(n))
    monkeypatch.setattr(registry, "get_redactor", lambda: (lambda t, conservar=(): t))
    return llamadas


def _correo(n, has_attachments=False):
    return make_email(
        subject="RE: Solicitud de servicio",
        body="Cancelen por favor la fila 1.",
        sender=CLIENTES[CLIENTE],
        to=[REPARE[CLIENTE]],
        conversation_id=f"conv-duda-{n}",
        message_id=f"msg-duda-{n}",
        has_attachments=has_attachments,
    )


def _preparar(harness):
    harness.repo.set("conversation_exists", True)
    harness.repo.set("get_cooler_rows", FILAS)


def test_inbound_dudoso_avisa_y_el_parser_corre_igual(harness, dudoso, monkeypatch):
    _preparar(harness)
    # Referencia: el mismo correo con el default regex.
    harness.deliver(_correo("ref"))
    referencia = [r["body"] for r in harness.replies]
    llamadas_ref = harness.repo.names()

    monkeypatch.setenv("CLASSIFIER_GATE", "fake")
    monkeypatch.setenv("CLASSIFIER_EXTRACT", "fake")
    n_replies, n_calls = len(harness.replies), len(harness.repo.calls)
    harness.deliver(_correo("dudoso"))

    nuevas = harness.replies[n_replies:]
    aviso, *resto = [r["body"] for r in nuevas]
    assert "Clasificación dudosa" in aviso and "requiere revisión" in aviso
    assert resto == referencia  # el parser respondió igual que con regex (aquí, nada)
    assert llamadas_ref  # y el parser sí corrió
    nombres = harness.repo.names()[n_calls:]
    assert "cancel_pending_cooler_row" not in nombres
    # Solo se agregan las consultas del contexto del hilo (proveedor externo).
    assert [n for n in nombres if n not in ("get_cooler_rows", "email_reply_validate")] == \
        [n for n in llamadas_ref if n not in ("get_cooler_rows", "email_reply_validate")]
    assert dudoso == []  # el extract no corrió
    assert nuevas[0]["in_reply_to"] == "msg-duda-dudoso"


def test_inbound_dudoso_con_excel_no_avisa(harness, dudoso, monkeypatch):
    _preparar(harness)
    monkeypatch.setenv("CLASSIFIER_GATE", "fake")
    harness.deliver(_correo("excel", has_attachments=True))
    assert all("Clasificación dudosa" not in r["body"] for r in harness.replies)
