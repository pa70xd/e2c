"""Duda del gate externo (confianza baja) en un hilo: revisión humana, no regex."""

import pytest

import classifier
from classifier import validate
from classifier.contracts import (
    ACCEPTED,
    ETAPA_INIT,
    ETAPA_REPLY,
    MOTIVO_CLASIFICACION_DUDOSA,
    PENDING,
    FilaGuardada,
    GateResult,
    ProveedorNoDisponible,
    RowExtraida,
    ThreadCtx,
)

HILO = ThreadCtx(
    etapa=ETAPA_REPLY,
    customer="danone",
    direccion="inbound",
    request_code="RC-1",
    filas=(FilaGuardada(1, PENDING), FilaGuardada(2, ACCEPTED)),
)
DUDOSO = lambda s, b, c: GateResult(True, "cancelar_filas", 0.4)  # noqa: E731


def _extract_espia(llamadas):
    def extract(b, ctx, gate=None):
        llamadas.append(gate)
        return [RowExtraida(accion="cancelar", row_number=1)]
    return extract


def test_reply_con_duda_va_a_revision_sin_filas(proveedores):
    llamadas = []
    proveedores.registrar("fake", gate=DUDOSO, extract=_extract_espia(llamadas))
    proveedores.redactor()
    proveedores.usar(gate="fake", extract="fake")

    d = classifier.decidir("RE: x", "cancelen la fila 1", HILO)

    assert d.motivo_revision == MOTIVO_CLASIFICACION_DUDOSA
    assert d.requiere_revision
    # El gate es el de regex: el parser corre igual que hoy.
    assert d.proveedor_gate == "regex" and d.tipo_evento == "modificar_filas"
    assert classifier.debe_continuar(d, HILO)
    # Nada por texto: el extract externo no corre con el gate de regex.
    assert llamadas == []
    assert d.rows == d.filas_aplicables == d.filas_revision == ()
    assert d.fallbacks == ("gate:fake:gate:confianza_baja",)


def test_reply_con_duda_y_cancelar_solicitud_no_marca_filas(proveedores):
    proveedores.registrar("fake", gate=DUDOSO)
    proveedores.redactor()
    proveedores.usar(gate="fake")
    d = classifier.decidir("RE: x", "bot.cancelar", HILO)
    assert d.tipo_evento == "cancelar_solicitud"
    assert d.motivo_revision == MOTIVO_CLASIFICACION_DUDOSA
    assert d.filas_revision == ()


def test_init_con_duda_cae_a_regex_como_siempre(proveedores):
    proveedores.registrar("fake", gate=lambda s, b, c: GateResult(True, "nueva_solicitud", 0.4))
    proveedores.redactor()
    proveedores.usar(gate="fake")
    d = classifier.decidir("Solicitud", "hola", ThreadCtx(etapa=ETAPA_INIT, customer="holanda"))
    assert d.motivo_revision is None
    assert not d.requiere_revision
    assert d.proveedor_gate == "regex"
    assert d.fallbacks == ("gate:fake:gate:confianza_baja",)


def _lanza(error):
    def gate(*a):
        raise error
    return gate


@pytest.mark.parametrize("gate", [
    _lanza(TimeoutError("texto del correo")),
    _lanza(RuntimeError("api")),
    _lanza(ProveedorNoDisponible("haiku_sin_api_key")),
    _lanza(ProveedorNoDisponible("haiku_pii_sin_redactar")),
    lambda s, b, c: {"es_os": True},                                # salida inválida
    lambda s, b, c: GateResult("si", "cancelar_filas", 0.4),        # confianza baja + otro error
    lambda s, b, c: GateResult(True, "nueva_solicitud", 0.9),       # incoherente con la etapa
], ids=["timeout", "error_api", "sin_key", "pii", "invalida", "mixto", "ctx"])
def test_otras_caidas_siguen_a_regex_sin_revision(proveedores, gate):
    proveedores.registrar("fake", gate=gate)
    proveedores.redactor()
    proveedores.usar(gate="fake")
    d = classifier.decidir("RE: x", "cuerpo", HILO)
    assert d.proveedor_gate == "regex"
    assert d.fallbacks
    assert d.motivo_revision is None


def test_redaccion_caida_no_es_duda(proveedores):
    proveedores.registrar("fake", gate=DUDOSO)
    proveedores.sin_redaccion()
    proveedores.usar(gate="fake")
    d = classifier.decidir("RE: x", "cuerpo", HILO)
    assert d.motivo_revision is None


def test_extract_con_confianza_baja_tambien_va_a_revision(proveedores, monkeypatch):
    proveedores.registrar(
        "fake",
        gate=lambda s, b, c: GateResult(True, "cancelar_filas", 0.95),
        extract=lambda b, c, gate=None: [RowExtraida(accion="cancelar", row_number=1)],
    )
    proveedores.redactor()
    proveedores.usar(gate="fake", extract="fake")
    monkeypatch.setattr(validate, "separar_invalidas", lambda *a: (["rows:confianza_baja"], (), ()))
    d = classifier.decidir("RE: x", "cuerpo", HILO)
    assert d.motivo_revision == MOTIVO_CLASIFICACION_DUDOSA
    assert d.proveedor_gate == "fake"
    assert d.rows == d.filas_aplicables == ()


def test_extract_invalido_no_es_duda(proveedores):
    proveedores.registrar(
        "fake",
        gate=lambda s, b, c: GateResult(True, "cancelar_filas", 0.95),
        extract=lambda b, c, gate=None: "no es lista",
    )
    proveedores.redactor()
    proveedores.usar(gate="fake", extract="fake")
    d = classifier.decidir("RE: x", "cuerpo", HILO)
    assert d.fallbacks and d.motivo_revision is None


def test_default_regex_sin_cambio(capsys):
    d = classifier.decidir("RE: x", "cuerpo", HILO)
    assert d.motivo_revision is None and not d.requiere_revision
    assert capsys.readouterr().out == ""


def test_log_incluye_motivo(proveedores, capsys):
    proveedores.registrar("fake", gate=DUDOSO)
    proveedores.redactor()
    proveedores.usar(gate="fake")
    classifier.decidir("RE: x", "cuerpo", HILO)
    assert f"motivo_revision={MOTIVO_CLASIFICACION_DUDOSA}" in capsys.readouterr().out
