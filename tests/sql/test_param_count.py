"""Cantidad de ``%s`` del SQL cargado == ``len(params)``, sin PostgreSQL.

Corre siempre. Solo se mockea ``execute_query``: el SQL es el real de
``repository/querys/genericas/`` y los parámetros los arma el código real.
Cubre el hueco de un .sql que cambia de parámetros sin su llamador (el
spy de ``test_known_bugs.py`` no los cuenta)."""

import importlib

import pandas as pd
import pytest

from tests.sql.test_cooler_sql import REPO_MODULES, cooler


@pytest.fixture(params=REPO_MODULES, ids=["danone", "gen", "penafiel"])
def llamadas(request, monkeypatch):
    module = importlib.import_module(request.param)
    calls = []

    def fake(query, params=()):
        calls.append((query, params))
        return None  # el UPDATE "no toca filas": insert_update_cooler sigue al INSERT

    monkeypatch.setattr(module, "execute_query", fake)
    return module.DB_POSTGRE, calls


def assert_params_cuadran(calls, esperadas):
    assert len(calls) == esperadas
    for query, params in calls:
        assert query.count("%s") == len(params), query.split("\n", 1)[0]


def test_send_email_coolers(llamadas):
    db, calls = llamadas
    db.send_email_coolers(cooler(1, "FAB-0001", "DNN-0001"))
    assert_params_cuadran(calls, 1)


def test_insert_update_cooler_update_e_insert(llamadas):
    db, calls = llamadas
    db.insert_update_cooler(cooler(1, "FAB-0001", "DNN-0001"))
    assert_params_cuadran(calls, 2)


def test_update_cooler(llamadas):
    db, calls = llamadas
    df = pd.DataFrame([{"status": "ACCEPTED", "os": "403111", "serial_number": "FAB-0001", "serial_dnn": ""}])
    db.update_cooler("REPARE_000001", df)
    assert_params_cuadran(calls, 1)


# review/ (Fase 3): consulta de contexto y UPDATE por fila.
def test_get_cooler_rows(llamadas):
    db, calls = llamadas
    db.get_cooler_rows("REPARE_000001")
    assert_params_cuadran(calls, 1)


def test_update_pending_cooler_row(llamadas):
    db, calls = llamadas
    db.update_pending_cooler_row("REPARE_000001", 1, {"modelo": "VR-17"})
    assert_params_cuadran(calls, 1)


def test_cancel_pending_cooler_row(llamadas):
    db, calls = llamadas
    db.cancel_pending_cooler_row("REPARE_000001", 1)
    assert_params_cuadran(calls, 1)


@pytest.mark.parametrize("fn, args", [
    ("get_cooler_rows", ("REPARE_000001",)),
    ("update_pending_cooler_row", ("REPARE_000001", 1, {})),
    ("cancel_pending_cooler_row", ("REPARE_000001", 1)),
])
def test_review_usa_la_tabla_del_modulo(llamadas, monkeypatch, fn, args):
    # DEBUG elige cooler_request_qa en COOLER_REQUEST: el SQL usa esa constante.
    db, calls = llamadas
    monkeypatch.setattr(importlib.import_module(db.__module__), "COOLER_REQUEST", "repare_email_parse.cooler_request_qa")
    getattr(db, fn)(*args)
    assert "repare_email_parse.cooler_request_qa" in calls[0][0]

