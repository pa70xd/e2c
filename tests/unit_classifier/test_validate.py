"""Validación determinista y reglas de revisión de filas."""

import pytest

from classifier import validate
from classifier.contracts import (
    ACCEPTED,
    CANCELLED,
    COMENTARIO_REVISION,
    ETAPA_INIT,
    ETAPA_REPLY,
    PENDING,
    REJECTED,
    TIPOS_EVENTO,
    FilaGuardada,
    GateResult,
    RowExtraida,
    ThreadCtx,
)

REPLY = ThreadCtx(etapa=ETAPA_REPLY, customer="danone", direccion="inbound")
INIT = ThreadCtx(etapa=ETAPA_INIT, customer="danone")
FILAS = ThreadCtx(
    etapa=ETAPA_REPLY,
    customer="danone",
    filas=(
        FilaGuardada(1, PENDING, "SF1", "DB1"),
        FilaGuardada(2, ACCEPTED, "SF2", "DB2"),
        FilaGuardada(3, CANCELLED),
        FilaGuardada(4, REJECTED),
    ),
)


def g(tipo, es_os=None, conf=0.9):
    if es_os is None:
        es_os = tipo not in ("no_os", "duplicado")
    return GateResult(es_os, tipo, conf)


# ------------------------------------------------------------------ gate
def test_tipos_evento_cerrados():
    assert TIPOS_EVENTO == (
        "nueva_solicitud", "agregar_filas", "modificar_filas", "cancelar_filas",
        "cancelar_solicitud", "estatus", "duplicado", "no_os",
    )


@pytest.mark.parametrize("tipo", ["agregar_filas", "modificar_filas", "estatus", "no_os", "duplicado"])
def test_gate_valido_en_hilo(tipo):
    assert validate.validar_gate(g(tipo), REPLY, 0.7) == []


@pytest.mark.parametrize(
    "resultado, ctx, error",
    [
        ({"es_os": True}, REPLY, "gate:tipo_invalido"),
        (GateResult("si", "estatus", 0.9), REPLY, "gate:es_os_no_bool"),
        (GateResult(True, "otra_cosa", 0.9), REPLY, "gate:tipo_evento_invalido"),
        (GateResult(True, "estatus", 1.5), REPLY, "gate:confidence_fuera_de_rango"),
        (GateResult(True, "estatus", True), REPLY, "gate:confidence_fuera_de_rango"),
        (GateResult(True, "estatus", "0.9"), REPLY, "gate:confidence_fuera_de_rango"),
        (GateResult(True, "estatus", 0.5), REPLY, "gate:confianza_baja"),
        (GateResult(True, "no_os", 0.9), REPLY, "gate:es_os_incoherente"),
        (GateResult(False, "modificar_filas", 0.9), REPLY, "gate:es_os_incoherente"),
        (g("modificar_filas"), INIT, "ctx:evento_de_hilo_sin_hilo"),
        (g("nueva_solicitud"), REPLY, "ctx:nueva_solicitud_en_hilo"),
        (g("estatus"), ThreadCtx(etapa="otra"), "ctx:etapa_invalida"),
    ],
)
def test_gate_invalido(resultado, ctx, error):
    assert error in validate.validar_gate(resultado, ctx, 0.7)


def test_confianza_minima_configurable():
    assert validate.validar_gate(g("estatus", conf=0.5), REPLY, 0.4) == []


# ------------------------------------------------------------------ rows
def test_rows_validas():
    rows = [RowExtraida("modificar", serie_fabricante="X", row_number=1),
            RowExtraida("modificar", row_number=2)]
    assert validate.validar_rows(rows, g("modificar_filas"), FILAS) == []
    assert validate.validar_rows([RowExtraida("agregar", modelo="M")], g("agregar_filas"), FILAS) == []
    assert validate.validar_rows([], g("estatus"), REPLY) == []


@pytest.mark.parametrize(
    "rows, tipo, ctx, error",
    [
        ("nada", "modificar_filas", FILAS, "rows:tipo_invalido"),
        ([RowExtraida("agregar")], "no_os", FILAS, "rows:sin_os"),
        ([RowExtraida("cancelar", row_number=1)], "cancelar_solicitud", FILAS, "rows:evento_sin_filas"),
        ([{"accion": "agregar"}], "agregar_filas", FILAS, "rows[0]:tipo_invalido"),
        ([RowExtraida("borrar", row_number=1)], "modificar_filas", FILAS, "rows[0]:accion_invalida"),
        ([RowExtraida("cancelar", row_number=1)], "modificar_filas", FILAS, "rows[0]:accion_incoherente_con_evento"),
        ([RowExtraida("agregar", modelo=5)], "agregar_filas", FILAS, "rows[0]:modelo_invalido"),
        ([RowExtraida("agregar", direccion="x" * 301)], "agregar_filas", FILAS, "rows[0]:direccion_invalido"),
        ([RowExtraida("modificar", row_number=0)], "modificar_filas", FILAS, "rows[0]:row_number_invalido"),
        ([RowExtraida("modificar", row_number="1")], "modificar_filas", FILAS, "rows[0]:row_number_invalido"),
        ([RowExtraida("agregar", row_number=9)], "agregar_filas", FILAS, "rows[0]:agregar_con_row_number"),
        ([RowExtraida("modificar")], "modificar_filas", FILAS, "rows[0]:row_number_requerido"),
        ([RowExtraida("modificar", row_number=1)], "modificar_filas", REPLY, "rows[0]:filas_no_cargadas"),
        ([RowExtraida("cancelar", row_number=99)], "cancelar_filas", FILAS, "rows[0]:fila_inexistente"),
        ([RowExtraida("cancelar", row_number=1), RowExtraida("cancelar", row_number=1)],
         "cancelar_filas", FILAS, "rows[1]:fila_repetida"),
    ],
)
def test_rows_invalidas(rows, tipo, ctx, error):
    assert error in validate.validar_rows(rows, g(tipo), ctx)


def test_errores_sin_valores_del_correo():
    rows = [RowExtraida("modificar", serie_fabricante="SERIE-SECRETA", direccion="Calle Falsa 123", row_number=99)]
    errores = validate.validar_rows(rows, g("modificar_filas"), FILAS)
    assert errores and not any("SECRETA" in e or "Calle" in e for e in errores)


# ------------------------------------------------------------------ revisión
def test_accepted_nunca_se_aplica_pending_si():
    rows = (RowExtraida("modificar", row_number=1), RowExtraida("modificar", row_number=2))
    aplicables, revision = validate.separar_revision(rows, g("modificar_filas"), FILAS)
    assert [r.row_number for r in aplicables] == [1]
    assert len(revision) == 1
    r = revision[0]
    assert (r.row_number, r.accion, r.status, r.motivo) == (2, "modificar", ACCEPTED, "fila_accepted")
    assert r.comentario == COMENTARIO_REVISION == "requiere revisión"


def test_cancelar_accepted_va_a_revision():
    rows = (RowExtraida("cancelar", row_number=2), RowExtraida("cancelar", row_number=1))
    aplicables, revision = validate.separar_revision(rows, g("cancelar_filas"), FILAS)
    assert [r.row_number for r in aplicables] == [1]
    assert [(r.row_number, r.accion) for r in revision] == [(2, "cancelar")]


def test_estado_no_pending_va_a_revision_por_precaucion():
    rows = (RowExtraida("modificar", row_number=3), RowExtraida("modificar", row_number=4))
    aplicables, revision = validate.separar_revision(rows, g("modificar_filas"), FILAS)
    assert aplicables == ()
    assert [r.motivo for r in revision] == ["estado_no_pending", "estado_no_pending"]


def test_agregar_se_aplica():
    rows = (RowExtraida("agregar", modelo="M"),)
    assert validate.separar_revision(rows, g("agregar_filas"), FILAS) == (rows, ())


def test_cancelar_solicitud_marca_las_accepted_del_hilo():
    _, revision = validate.separar_revision((), g("cancelar_solicitud"), FILAS)
    assert [(r.row_number, r.status) for r in revision] == [(2, ACCEPTED), (4, REJECTED)]
    _, revision = validate.separar_revision((), g("cancelar_solicitud"), REPLY)
    assert revision == ()
