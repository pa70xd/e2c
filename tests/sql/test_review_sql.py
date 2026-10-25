"""SQL de review/ contra un PostgreSQL LOCAL y desechable (mismo arnés que
``test_cooler_sql.py``: ``E2C_TEST_PG_DSN``, se salta sin servidor).

* ``cooler_rows_by_request.sql`` (``get_cooler_rows``): solo row_number,
  series y status de la solicitud, en orden.
* ``update_pending_cooler_row.sql`` y ``cancel_pending_cooler_row.sql``: una
  fila, filtrada por request_code + row_number + status = 'PENDING'."""

from tests.sql.test_cooler_sql import (  # noqa: F401  (fixtures)
    REAL_EXECUTE_QUERY,
    REQUEST,
    aceptar,
    cooler,
    repo,
    schema,
)


def _filas(repo):
    return REAL_EXECUTE_QUERY(
        f"SELECT request_code, row_number, serie_fabricante, serie_dnn_bnf, modelo, direccion, status "
        f"FROM {repo.table} ORDER BY request_code, row_number"
    )


def _cargar(repo):
    repo.DB_POSTGRE.send_email_coolers(cooler(2, "FAB-0002", None, modelo="M2", direccion="CALLE 2"))
    repo.DB_POSTGRE.send_email_coolers(cooler(1, "FAB-0001", "DNN-0001", modelo="M1", direccion="CALLE 1"))
    repo.DB_POSTGRE.send_email_coolers(cooler(3, "FAB-0003", None))
    repo.DB_POSTGRE.send_email_coolers(cooler(1, "FAB-9001", None, request_code="REPARE_000999"))
    aceptar(repo, 3)


# --------------------------------------------------------------- get_cooler_rows
def test_get_cooler_rows_solo_la_solicitud_y_sin_pii(repo):
    _cargar(repo)

    rows = [dict(r) for r in repo.DB_POSTGRE.get_cooler_rows(REQUEST)]

    assert rows == [
        {"row_number": 1, "serie_fabricante": "FAB-0001", "serie_dnn_bnf": "DNN-0001", "status": "PENDING"},
        {"row_number": 2, "serie_fabricante": "FAB-0002", "serie_dnn_bnf": None, "status": "PENDING"},
        {"row_number": 3, "serie_fabricante": "FAB-0003", "serie_dnn_bnf": None, "status": "ACCEPTED"},
    ]


def test_get_cooler_rows_sin_filas(repo):
    assert repo.DB_POSTGRE.get_cooler_rows("REPARE_000404") == []


# --------------------------------------------------------------- update por fila
def test_update_pending_cooler_row_cambia_solo_campos_no_vacios(repo):
    _cargar(repo)

    tocadas = repo.DB_POSTGRE.update_pending_cooler_row(
        REQUEST, 1, {"modelo": "M1-CORR", "direccion": "  ", "serie_dnn_bnf": None}
    )

    assert [dict(r) for r in tocadas] == [{"request_code": REQUEST, "row_number": 1}]
    fila = next(f for f in _filas(repo) if f["request_code"] == REQUEST and f["row_number"] == 1)
    assert (fila["modelo"], fila["direccion"], fila["serie_dnn_bnf"]) == ("M1-CORR", "CALLE 1", "DNN-0001")


def test_update_pending_cooler_row_no_toca_accepted_ni_otra_solicitud(repo):
    _cargar(repo)
    antes = _filas(repo)

    assert repo.DB_POSTGRE.update_pending_cooler_row(REQUEST, 3, {"modelo": "X"}) == []
    assert repo.DB_POSTGRE.update_pending_cooler_row(REQUEST, 99, {"modelo": "X"}) == []
    assert repo.DB_POSTGRE.update_pending_cooler_row("REPARE_000404", 1, {"modelo": "X"}) == []
    assert _filas(repo) == antes


def test_update_pending_cooler_row_reenvio_identico(repo):
    _cargar(repo)
    repo.DB_POSTGRE.update_pending_cooler_row(REQUEST, 2, {"modelo": "M2-CORR"})
    antes = _filas(repo)

    assert repo.DB_POSTGRE.update_pending_cooler_row(REQUEST, 2, {"modelo": "M2-CORR"})
    assert _filas(repo) == antes


# --------------------------------------------------------------- cancel por fila
def test_cancel_pending_cooler_row_solo_esa_fila(repo):
    _cargar(repo)

    tocadas = repo.DB_POSTGRE.cancel_pending_cooler_row(REQUEST, 2)

    assert [dict(r) for r in tocadas] == [{"request_code": REQUEST, "row_number": 2}]
    estados = {(f["request_code"], f["row_number"]): f["status"] for f in _filas(repo)}
    assert estados == {
        (REQUEST, 1): "PENDING",
        (REQUEST, 2): "CANCELLED",
        (REQUEST, 3): "ACCEPTED",
        ("REPARE_000999", 1): "PENDING",
    }


def test_cancel_pending_cooler_row_no_toca_accepted_ni_cancelada(repo):
    _cargar(repo)
    repo.DB_POSTGRE.cancel_pending_cooler_row(REQUEST, 2)
    antes = _filas(repo)

    assert repo.DB_POSTGRE.cancel_pending_cooler_row(REQUEST, 3) == []
    assert repo.DB_POSTGRE.cancel_pending_cooler_row(REQUEST, 2) == []  # reenvío
    assert _filas(repo) == antes


# --------------------------------------------------------------- aplicador real
def test_aplicar_contra_postgres(repo, monkeypatch):
    """review.aplicar con el DB_POSTGRE real: cambio y cancelación de PENDING;
    la ACCEPTED y el alta desde texto quedan fuera y van a revisión."""
    import review
    from classifier.contracts import (
        AGREGAR, CANCELAR, ETAPA_REPLY, MODIFICAR, MODIFICAR_FILAS, Decision, FilaRevision,
        GateResult, RowExtraida, ThreadCtx,
    )
    from review.contexto import filas_guardadas

    _cargar(repo)
    # La tabla email_request no existe en el DDL mínimo.
    monkeypatch.setattr(repo.DB_POSTGRE, "update_email_request", staticmethod(lambda request_code: []))
    ctx = ThreadCtx(
        etapa=ETAPA_REPLY, customer="danone", direccion="inbound", request_code=REQUEST,
        filas=filas_guardadas(repo.DB_POSTGRE.get_cooler_rows(REQUEST)),
    )
    aplicables = (
        RowExtraida(accion=MODIFICAR, row_number=1, modelo="M1-CORR"),
        RowExtraida(accion=CANCELAR, row_number=2),
        RowExtraida(accion=AGREGAR, serie_fabricante="FAB-0010", modelo="M10"),
    )
    decision = Decision(
        gate=GateResult(True, MODIFICAR_FILAS, 0.9),
        proveedor_gate="fake",
        proveedor_extract="fake",
        rows=aplicables + (RowExtraida(accion=MODIFICAR, row_number=3, modelo="X"),),
        filas_aplicables=aplicables,
        filas_revision=(FilaRevision(3, MODIFICAR, "ACCEPTED", "fila_accepted"),),
    )

    resultado = review.aplicar(decision, ctx, repo.DB_POSTGRE)

    assert [(f.row_number, f.accion) for f in resultado.aplicadas] == [(1, MODIFICAR), (2, CANCELAR)]
    assert [(f.row_number, f.motivo) for f in resultado.revision] == [
        (3, "fila_accepted"), (None, "alta sin Excel; requiere datos completos")
    ]
    assert resultado.errores == ()
    propias = [
        (f["row_number"], f["serie_fabricante"], f["modelo"], f["status"])
        for f in _filas(repo) if f["request_code"] == REQUEST
    ]
    assert propias == [
        (1, "FAB-0001", "M1-CORR", "PENDING"),
        (2, "FAB-0002", "M2", "CANCELLED"),
        (3, "FAB-0003", None, "ACCEPTED"),
    ]
