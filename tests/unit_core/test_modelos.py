import logging
import time

import duckdb
import pytest

from parsers.core import modelos
from parsers.core.modelos import IndiceModelos, resolver_modelo

CATALOGO = {
    "12 | ENFRIADOR": {"VR": ["VR-12", "VR 20", "XXXXX"]},
    "16 | CONGELADOR": {"CH": ["CH170", "CH-200"], "HC": ["HC1"]},
    "17 | CORTINA DE AIRE": {"CH": ["CH170"]},
}


@pytest.fixture
def indice():
    return IndiceModelos(CATALOGO)


def test_exacto_trim_y_mayusculas(indice):
    assert indice.resolver("  vr-12 ") == ("VR-12", "12 | ENFRIADOR", "VR", "exacto")


def test_normalizado(indice):
    r = indice.resolver("vr12")
    assert r == ("VR-12", "12 | ENFRIADOR", "VR", "normalizado")
    assert indice.resolver("VR.20/") .motivo == "normalizado"
    assert indice.resolver("CH 200").modelo == "CH-200"


def test_no_en_catalogo(indice):
    assert indice.resolver("MODELO-A100") == (None, None, None, "no_en_catalogo")


def test_placeholder_no_es_modelo(indice):
    assert indice.resolver("XXXXX").motivo == "no_en_catalogo"


def test_ambiguo_vacio_y_log(indice, caplog):
    with caplog.at_level(logging.WARNING, logger=modelos.log.name):
        assert indice.resolver("CH170") == (None, None, None, "ambiguo")
        indice.resolver("ch-170")  # normalizado también ambiguo
    assert "16 | CONGELADOR / CH" in caplog.text and "17 | CORTINA DE AIRE / CH" in caplog.text


@pytest.mark.parametrize("v", [None, "", "  ", "NA", "n/a", float("nan")])
def test_sin_modelo(indice, v):
    assert indice.resolver(v) == (None, None, None, "sin_modelo")


def test_idempotente(indice):
    for v in ("vr12", "CH170", "zzz", ""):
        assert indice.resolver(v) == indice.resolver(v)


def test_rendimiento_851_modelos():
    ms = [f"M{i}" for i in range(851)]
    ind = IndiceModelos({"1 | A": {"L": ms}})
    entradas = (ms + ["m-12", "NOEXISTE", ""]) * 11
    entradas = (entradas * 10)[:10000]
    t = time.perf_counter()
    for e in entradas:
        ind.resolver(e)
    assert time.perf_counter() - t < 1.0


def test_catalogo_real():
    ind = modelos.indice_defecto()
    assert modelos.indice_defecto() is ind  # caché
    assert len(ind) == 802  # 803 únicos menos el placeholder XXXXX
    assert ind.resolver("CH-170").motivo in ("normalizado", "ambiguo")


def test_normalizar_id():
    assert modelos.normalizar_id(" ab12 ") == "AB12"
    for v in (None, "", "NA", "n/a", float("nan")):
        assert modelos.normalizar_id(v) is None


@pytest.mark.parametrize("clase", ["danone", "penafiel"])
def test_calcula_modelo_en_duckdb(clase):
    con = duckdb.connect()
    s2 = "SERIE DNN/BNF" if clase == "danone" else "SERIE"
    con.execute(f'CREATE TABLE t ("MODELO" VARCHAR, "SERIE FABRICANTE" VARCHAR, "{s2}" VARCHAR)')
    con.execute("INSERT INTO t VALUES ('MODELO-A100', ' ab1 ', 'N/A'), ('', NULL, 'x2'), (NULL, 'na', NULL)")
    modelos.llenar_modelo(con, "t", "SERIE FABRICANTE", s2)
    con.execute("INSERT INTO t (\"MODELO\") VALUES ('vr12')")
    modelos.llenar_modelo(con, "t", "SERIE FABRICANTE", s2)  # idempotente
    filas = con.execute(
        'SELECT "MODELO_GEN_MOTIVO","ACTIVO_GEN","SERIE_GEN" FROM t ORDER BY rowid'
    ).fetchall()
    assert filas[:3] == [("no_en_catalogo", "AB1", None), ("sin_modelo", None, "X2"), ("sin_modelo", None, None)]
    assert filas[3][0] == "no_en_catalogo"


def test_calcula_modelo_llena_modelo_real():
    from parsers.danone_parse.catalog import DANONE_CATALOG
    from parsers.penafiel_parse.catalog import PENAFIEL_CATALOG

    ind = modelos.indice_defecto()
    unico = next(m for m, p in ind._exacto.items() if len(p) == 1)
    cat, lin = next(iter(ind._exacto[unico]))
    for cls, s2 in ((DANONE_CATALOG, "SERIE DNN/BNF"), (PENAFIEL_CATALOG, "SERIE")):
        con = duckdb.connect()
        con.execute(f'CREATE TABLE t ("MODELO" VARCHAR, "SERIE FABRICANTE" VARCHAR, "{s2}" VARCHAR)')
        con.execute("INSERT INTO t VALUES (?, 'a1', 's1')", [unico.lower()])
        cls(con).calcula_modelo("t")
        assert con.execute(
            'SELECT "MODELO_GEN","CATEGORIA_GEN","LINEA_GEN","MODELO_GEN_MOTIVO","ACTIVO_GEN","SERIE_GEN" FROM t'
        ).fetchone() == (unico, cat, lin, "exacto", "A1", "S1")


def test_aviso_modelos_y_html():
    con = duckdb.connect()
    con.execute('CREATE TABLE t ("MODELO_GEN_MOTIVO" VARCHAR)')
    con.execute("INSERT INTO t VALUES ('exacto'),('normalizado')")
    assert modelos.aviso_modelos(con, "t") is None  # todo resuelto: no hay aviso
    con.execute("INSERT INTO t VALUES ('no_en_catalogo'),('no_en_catalogo'),('no_en_catalogo'),('ambiguo'),('sin_modelo')")
    aviso = modelos.aviso_modelos(con, "t")
    assert aviso == "3 equipos sin modelo en catálogo; 1 equipo sin modelo; 1 modelo ambiguo"
    html = modelos.agregar_aviso("<div><div>x</div></div>", aviso)
    assert html.endswith("</div>") and aviso in html
    assert modelos.agregar_aviso("<div>x</div>", None) == "<div>x</div>"
    con.execute("CREATE TABLE sin_col (a INT)")
    assert modelos.aviso_modelos(con, "sin_col") is None
