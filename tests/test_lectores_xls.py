"""Regresión: los lectores viejos usaban ``book.sheet_visibility`` (no existe en
xlrd 2.x), así que cualquier .xls reventaba. Con un .xls cuya primera hoja está
oculta deben tomar la primera hoja visible."""

import asyncio

import duckdb
import pytest

from parsers.danone_parse.reader import DANONE_READER
from parsers.gen_parse.reader import GEN_READER
from parsers.penafiel_parse.reader import PENAFIEL_READER
from tests.fixtures.lector import build_lector_fixtures as fx
from tests.support.fakes import FakeGraph
from tests.support.emails import make_email

XLS = (fx.DIR / "oculta_primero.xls").read_bytes()


def _graph():
    g = FakeGraph()
    msg = make_email(subject="s", body="b", sender=("A", "a@example.com"), to=["b@example.com"], message_id="m1")
    g.add_message(msg, [("solicitud.xls", XLS)])
    return g, msg.id


def test_gen_reader_lee_xls_con_primera_hoja_oculta():
    g, mid = _graph()
    (archivo,) = asyncio.run(GEN_READER.get_adjuntos(g, "u", mid))
    assert list(archivo["dataframe"].columns) == ["FOLIO", "No SERIE"]
    assert archivo["dataframe"]["FOLIO"].tolist() == ["F-1"]


def test_penafiel_pasa_por_gen_reader_con_xls():
    g, mid = _graph()
    archivos = asyncio.run(PENAFIEL_READER.get_adjuntos(g, "u", mid, duckdb.connect()))
    assert archivos is not None  # no revienta (antes: AttributeError); el contenido lo valida el parser


def test_danone_lee_xls_con_primera_hoja_oculta():
    g, mid = _graph()
    con = duckdb.connect()
    tablas = asyncio.run(DANONE_READER.get_adjuntos(g, "u", mid, con))
    assert tablas
    cols = [c[0] for c in con.execute(f'DESCRIBE "{tablas[0]["table"]}"').fetchall()]
    assert "COLUMNA OCULTA" not in cols
    assert con.execute(f'SELECT COUNT(*) FROM "{tablas[0]["table"]}"').fetchone()[0] == 1
