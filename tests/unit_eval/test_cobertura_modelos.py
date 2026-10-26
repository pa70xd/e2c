"""Cobertura de modelos: datos inventados, sin base ni red."""

import json

import pytest

from eval import cobertura_modelos as cob
from parsers.core.modelos import IndiceModelos

CAT = {"12 | ENF": {"VR": ["VR-12"]}, "16 | CONG": {"CH": ["CH170"]}, "17 | CORT": {"CH": ["CH170"]}}
IND = IndiceModelos(CAT)
FILAS = [
    ("danone", "VR-12", 6), ("danone", "vr12", 2), ("danone", "CH170", 1),
    ("danone", "ZZ-9", 3), ("danone", "", 2),
    ("penafiel", "ZZ-9", 1), ("penafiel", "Texto con nombre Juan Pérez", 4),
]


def test_calcular():
    r = cob.calcular(FILAS, IND)
    d = r["clientes"]["danone"]
    assert d["total"] == 14
    assert (d["exacto"]["n"], d["normalizado"]["n"], d["ambiguo"]["n"]) == (6, 2, 1)
    assert (d["no_en_catalogo"]["n"], d["sin_modelo"]["n"]) == (3, 2)
    assert d["exacto"]["pct"] == pytest.approx(42.9, abs=0.1)
    assert {"modelo": cob.LIBRE, "n": 4} in r["top_no_encontrados"]
    assert {"modelo": "ZZ-9", "n": 4} in r["top_no_encontrados"]
    assert "Juan" not in json.dumps(r)


def test_top_limitado_a_30():
    filas = [("c", f"X{i}Q", i + 1) for i in range(50)]
    assert len(cob.calcular(filas, IND)["top_no_encontrados"]) == 30


def test_csv(tmp_path, capsys):
    ruta = tmp_path / "m.csv"
    ruta.write_text("cliente,modelo,n\nDanone,VR-12,3\nDanone,ZZ,1\n", encoding="utf-8")
    salida = tmp_path / "r.json"
    assert cob.main(["--csv", str(ruta), "--json", str(salida)]) == 0
    assert "danone (n=4)" in capsys.readouterr().out
    assert json.loads(salida.read_text())["clientes"]["danone"]["total"] == 4


def test_csv_sin_columnas(tmp_path):
    ruta = tmp_path / "m.csv"
    ruta.write_text("a,b\n1,2\n", encoding="utf-8")
    assert cob.main(["--csv", str(ruta)]) == 4


def test_prod_exige_confirmacion():
    assert cob.main(["--tablas", "prod"]) == 2


class _Cur:
    def __init__(self):
        self.sqls = []
    def execute(self, sql, params=None):
        self.sqls.append(sql)
    def fetchall(self):
        return [{"cliente": "Danone", "modelo": "VR-12", "n": 5}, {"cliente": None, "modelo": None, "n": 1}]


class _Conn:
    def __init__(self):
        self.cur, self.cerrada, self.rollback_ok = _Cur(), False, False
    def cursor(self):
        return self.cur
    def rollback(self):
        self.rollback_ok = True
    def close(self):
        self.cerrada = True


def test_pg_solo_lectura(capsys):
    conn = _Conn()
    # el catálogo real no tiene VR-12; solo importa el flujo y las protecciones
    assert cob.main(["--tablas", "qa"], abrir_pg=lambda: conn) == 0
    sqls = conn.cur.sqls
    assert sqls[0] == "SET TRANSACTION READ ONLY"
    assert all(s.lstrip().upper().startswith(("SET TRANSACTION READ ONLY", "-- SOLO LECTURA")) or "SELECT" in s.upper() for s in sqls)
    assert "cooler_request_qa" in sqls[1]
    assert conn.rollback_ok and conn.cerrada
    assert "(sin cliente)" in capsys.readouterr().out


def test_query_es_select_valido():
    from eval.backfill import TABLAS, cargar_sql
    cargar_sql("modelos_historicos", TABLAS["prod"])  # validar_select no lanza
