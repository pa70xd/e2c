"""Selección de proveedores, redacción y caída a regex."""

import pytest

import classifier
from classifier import registry
from classifier.contracts import (
    ACCEPTED,
    ETAPA_INIT,
    ETAPA_REPLY,
    PENDING,
    FilaGuardada,
    GateResult,
    ProveedorNoDisponible,
    RowExtraida,
    ThreadCtx,
)

REPLY = ThreadCtx(etapa=ETAPA_REPLY, customer="danone", direccion="inbound")
FILAS = ThreadCtx(
    etapa=ETAPA_REPLY,
    customer="danone",
    direccion="inbound",
    filas=(FilaGuardada(1, PENDING), FilaGuardada(2, ACCEPTED)),
)
CUERPO = "Cambien la serie SF-PRIVADA de Calle Inventada 42, contacto 555-0100"


def test_defaults(monkeypatch):
    assert registry.nombre_gate() == registry.nombre_extract() == "regex"
    assert registry.min_confidence() == 0.7
    monkeypatch.setenv("CLASSIFIER_GATE", " Haiku ")
    monkeypatch.setenv("CLASSIFIER_MIN_CONFIDENCE", "0.85")
    assert registry.nombre_gate() == "haiku"
    assert registry.min_confidence() == 0.85
    monkeypatch.setenv("CLASSIFIER_MIN_CONFIDENCE", "x")
    assert registry.min_confidence() == 0.7


def test_haiku_y_jev_registrados():
    assert {"regex", "haiku", "jev"} <= set(registry.PROVEEDORES)


def test_cargar_desconocido_o_no_implementado():
    with pytest.raises(ProveedorNoDisponible, match="proveedor_desconocido:nada"):
        registry.cargar("nada")
    with pytest.raises(ProveedorNoDisponible, match="proveedor_no_implementado:jev"):
        registry.cargar("jev")


def test_get_redactor_es_la_redact_real():
    from classifier.redact import redact
    assert registry.get_redactor() is redact


@pytest.mark.parametrize(
    "error, codigo",
    [(NotImplementedError, "redaccion_no_disponible"), (ImportError, "redaccion_no_disponible"),
     (ValueError, "redaccion_error")],
)
def test_externo_sin_redaccion_cae_a_regex_y_no_llama_al_proveedor(proveedores, capsys, error, codigo):
    llamadas = []
    proveedores.registrar("fake", gate=lambda *a: llamadas.append(a))
    proveedores.sin_redaccion(error)
    proveedores.usar(gate="fake")
    d = classifier.decidir("RE: x", CUERPO, REPLY)
    assert llamadas == []
    assert d.proveedor_gate == "regex"
    assert d.fallbacks == (f"gate:fake:{codigo}",)
    out = capsys.readouterr().out
    assert "[CLASSIFIER]" in out and "PRIVADA" not in out and "Inventada" not in out


def test_externo_recibe_texto_redactado(proveedores):
    recibido = []

    def gate(subject, body, ctx):
        recibido.append((subject, body))
        return GateResult(True, "estatus", 0.95)

    proveedores.registrar("fake", gate=gate)
    proveedores.redactor()
    proveedores.usar(gate="fake")
    d = classifier.decidir("RE: Calle Inventada", CUERPO, REPLY)
    assert recibido == [("<R>", "<R>")]
    assert proveedores.redactados == [("RE: Calle Inventada", ()), (CUERPO, ())]
    assert (d.proveedor_gate, d.tipo_evento, d.fallbacks) == ("fake", "estatus", ())


def test_redact_conserva_las_series_del_hilo(proveedores):
    ctx = ThreadCtx(
        etapa=ETAPA_REPLY,
        filas=(FilaGuardada(1, PENDING, "5512345678", ""), FilaGuardada(2, ACCEPTED, None, "DB-9"),
               FilaGuardada(3, PENDING, "5512345678", None)),
    )
    proveedores.registrar("fake", gate=lambda s, b, c: GateResult(True, "estatus", 0.95))
    proveedores.redactor()
    proveedores.usar(gate="fake")
    classifier.decidir(None, "la 5512345678 falla", ctx)
    assert proveedores.redactados == [("la 5512345678 falla", ("5512345678", "DB-9"))]


def test_redact_real_con_series_del_hilo(proveedores):
    recibido = []
    proveedores.registrar("fake", gate=lambda s, b, c: recibido.append(b) or GateResult(True, "estatus", 0.95))
    proveedores.usar(gate="fake")
    ctx = ThreadCtx(etapa=ETAPA_REPLY, filas=(FilaGuardada(1, PENDING, "5512345678"),))
    d = classifier.decidir(None, "cambien 5512345678 hoy", ctx)
    assert "5512345678" in recibido[0]
    assert d.proveedor_gate == "fake"
    # Sin la serie en el hilo, la misma cifra se trata como teléfono.
    classifier.decidir(None, "cambien 5512345678 hoy", REPLY)
    assert "5512345678" not in recibido[1]


@pytest.mark.parametrize(
    "gate, codigo",
    [
        (lambda s, b, c: GateResult(True, "estatus", 0.3), "gate:fake:gate:confianza_baja"),
        (lambda s, b, c: {"es_os": True}, "gate:fake:gate:tipo_invalido"),
        (lambda s, b, c: GateResult(True, "nueva_solicitud", 0.9), "gate:fake:ctx:nueva_solicitud_en_hilo"),
    ],
)
def test_gate_invalido_cae_a_regex(proveedores, gate, codigo):
    proveedores.registrar("fake", gate=gate)
    proveedores.redactor()
    proveedores.usar(gate="fake")
    d = classifier.decidir("RE: x", "bot.cancelar", REPLY)
    assert d.proveedor_gate == "regex"
    assert d.tipo_evento == "cancelar_solicitud"
    assert d.fallbacks == (codigo,)


def test_excepcion_del_proveedor_se_loguea_sin_mensaje(proveedores, capsys):
    def gate(*a):
        raise RuntimeError(CUERPO)

    proveedores.registrar("fake", gate=gate)
    proveedores.redactor()
    proveedores.usar(gate="fake")
    d = classifier.decidir("RE: x", CUERPO, REPLY)
    assert d.fallbacks == ("gate:fake:RuntimeError",)
    assert "PRIVADA" not in capsys.readouterr().out


def test_proveedor_no_implementado_cae_a_regex(proveedores):
    proveedores.redactor()
    proveedores.usar(gate="jev", extract="jev")
    d = classifier.decidir("RE: x", "bot.estatus", REPLY)
    assert d.proveedor_gate == d.proveedor_extract == "regex"
    assert d.fallbacks == (
        "gate:jev:proveedor_no_implementado:jev",
        "extract:jev:proveedor_no_implementado:jev",
    )


def test_no_os_externo_en_init(proveedores):
    proveedores.registrar("fake", gate=lambda s, b, c: GateResult(False, "no_os", 0.9))
    proveedores.redactor()
    proveedores.usar(gate="fake")
    # Regex diría que sí (pide instalaciones); el externo valida y manda.
    assert classifier.gate_proposito("danone", "Solicitud", "favor de realizar instalaciones") is False


def test_extract_externo_y_revision_de_accepted(proveedores):
    recibido_gate = []
    rows = [RowExtraida("modificar", modelo="M2", row_number=1),
            RowExtraida("modificar", modelo="M3", row_number=2)]
    proveedores.registrar(
        "fake",
        gate=lambda s, b, c: GateResult(True, "modificar_filas", 0.9),
        extract=lambda b, c, gate=None: recibido_gate.append(gate) or rows,
    )
    proveedores.redactor()
    proveedores.usar(gate="fake", extract="fake")
    d = classifier.decidir("RE: x", CUERPO, FILAS)
    assert (d.proveedor_gate, d.proveedor_extract) == ("fake", "fake")
    assert recibido_gate == [d.gate] and d.gate.tipo_evento == "modificar_filas"
    assert d.rows == tuple(rows)
    assert [r.row_number for r in d.filas_aplicables] == [1]
    assert [(r.row_number, r.comentario) for r in d.filas_revision] == [(2, "requiere revisión")]
    assert d.requiere_revision


def test_extract_invalido_cae_a_regex(proveedores):
    proveedores.registrar("fake", extract=lambda b, c, gate=None: [RowExtraida("modificar", row_number=1)])
    proveedores.redactor()
    proveedores.usar(extract="fake")
    # Sin filas cargadas no se puede verificar la referencia.
    d = classifier.decidir("RE: x", "adjunto cambios", REPLY)
    assert d.proveedor_extract == "regex"
    assert d.rows == ()
    assert d.fallbacks == ("extract:fake:rows[0]:filas_no_cargadas",)


def test_extract_no_corre_si_no_es_os(proveedores):
    llamadas = []
    proveedores.registrar(
        "fake",
        gate=lambda s, b, c: GateResult(False, "no_os", 0.9),
        extract=lambda b, c, gate=None: llamadas.append(b) or [],
    )
    proveedores.redactor()
    proveedores.usar(gate="fake", extract="fake")
    d = classifier.decidir("RE: x", "gracias", REPLY)
    assert llamadas == [] and d.rows == ()


def test_cargador_de_contexto_solo_con_externo(monkeypatch, proveedores):
    from types import SimpleNamespace
    llamadas = []

    def cargador(email, ctx):
        llamadas.append(ctx)
        return FILAS

    classifier.registrar_cargador_contexto(cargador)
    email = SimpleNamespace(subject="RE: x", unique_body=SimpleNamespace(content="hola"))
    classifier.decidir_correo(email, "danone", ETAPA_REPLY, "inbound")
    assert llamadas == []

    proveedores.registrar("fake", gate=lambda s, b, c: GateResult(True, "estatus", 0.9))
    proveedores.redactor()
    proveedores.usar(gate="fake")
    d, ctx = classifier.decidir_correo(email, "danone", ETAPA_REPLY, "inbound")
    assert ctx is FILAS and len(llamadas) == 1
    assert d.proveedor_gate == "fake"


def test_debe_continuar():
    no_os = classifier.Decision(GateResult(False, "no_os", 0.9), "fake", "regex")
    assert not classifier.debe_continuar(no_os, REPLY)
    assert classifier.debe_continuar(no_os, ThreadCtx(etapa=ETAPA_REPLY, direccion="reply_to_bot"))
    assert classifier.debe_continuar(no_os, ThreadCtx(etapa=ETAPA_REPLY, direccion="bot"))
    si = classifier.Decision(GateResult(True, "estatus", 0.9), "fake", "regex")
    assert classifier.debe_continuar(si, ThreadCtx(etapa=ETAPA_INIT))
