"""SQL de coolers contra un PostgreSQL LOCAL y desechable.

Corre el código real de ``repository/*/consultas_postgre.py`` y el
``execute_query`` real; solo cambia ``get_connection`` por una conexión local
y la tabla por una en un esquema temporal.

Se activa con ``E2C_TEST_PG_DSN`` (por ejemplo
``host=/ruta/al/socket port=55432 dbname=postgres user=postgres``). Sin la
variable, o si no hay servidor, se salta. Solo acepta un socket Unix o
127.0.0.1/localhost: nunca apunta a otra base.

El DDL es mínimo, reconstruido de los .sql del repo y de
``okf/data/modelo-datos.md``: todas las columnas son ``text`` salvo
``row_number``.
"""

import importlib
import os
import uuid

import pandas as pd
import pytest

import infrastructure.database.postgres as postgres

psycopg2 = pytest.importorskip("psycopg2")
from psycopg2.extras import RealDictCursor  # noqa: E402

# ``block_database`` reemplaza execute_query en cada prueba; se guarda el real.
REAL_EXECUTE_QUERY = postgres.execute_query

DSN = os.environ.get("E2C_TEST_PG_DSN")

REPO_MODULES = [
    "repository.danone.consultas_postgre",
    "repository.gen.consultas_postgre",
    "repository.penafiel.consultas_postgre",
]

COOLER_KEYS = (
    "id_cliente fecha_solicitud modelo tipo_servicio canal region plaza razon_social direccion "
    "cp ciudad colonia latitud longitud ruta telefono_1 telefono_2 comentarios cbu cliente os "
    "rejection_reason prioridad folio ticket_solicitud assigned_to gestion_observaciones "
    "fecha_asignacion fecha_atencion fecha_completado"
).split()

REQUEST = "REPARE_000001"


def _dsn_local():
    if not DSN:
        pytest.skip("E2C_TEST_PG_DSN no definido: sin PostgreSQL local")
    params = psycopg2.extensions.parse_dsn(DSN)
    host = params.get("host", "")
    if not (host.startswith("/") or host in ("127.0.0.1", "localhost")):
        pytest.fail(f"E2C_TEST_PG_DSN debe ser local (socket Unix o 127.0.0.1), no {host!r}")
    return DSN


def _connect():
    return psycopg2.connect(_dsn_local(), cursor_factory=RealDictCursor)


@pytest.fixture(scope="module")
def schema():
    try:
        conn = _connect()
    except psycopg2.OperationalError as exc:
        pytest.skip(f"PostgreSQL local no disponible: {exc}")
    conn.close()
    name = f"e2c_test_{uuid.uuid4().hex[:8]}"
    yield name
    conn = _connect()
    with conn, conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {name} CASCADE")
    conn.close()


@pytest.fixture(params=REPO_MODULES, ids=["danone", "gen", "penafiel"])
def repo(request, schema, monkeypatch):
    table = f"{schema}.cooler_request"
    columnas = ",\n".join(f"{c} text" for c in ["serie_fabricante", "serie_dnn_bnf", "status"] + COOLER_KEYS)
    conn = _connect()
    with conn, conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        cur.execute(
            f"CREATE TABLE {table} (id serial PRIMARY KEY, request_code text NOT NULL, "
            f"row_number int, {columnas}, created_at timestamp, updated_at timestamp)"
        )
    conn.close()

    module = importlib.import_module(request.param)
    monkeypatch.setattr(postgres, "get_connection", _connect)
    monkeypatch.setattr(module, "execute_query", REAL_EXECUTE_QUERY)
    monkeypatch.setattr(module, "COOLER_REQUEST", table)
    module.table = table
    return module


def cooler(row_number, serie_fabricante, serie_dnn_bnf, **overrides):
    base = dict.fromkeys(COOLER_KEYS)
    base.update(
        request_code=REQUEST,
        row_number=row_number,
        serie_fabricante=serie_fabricante,
        serie_dnn_bnf=serie_dnn_bnf,
        status="PENDING",
        id_cliente="1000001",
    )
    base.update(overrides)
    return base


def filas(repo):
    return REAL_EXECUTE_QUERY(
        f"SELECT row_number, serie_fabricante, serie_dnn_bnf, status, ticket_solicitud "
        f"FROM {repo.table} ORDER BY id"
    )


def aceptar(repo, row_number):
    REAL_EXECUTE_QUERY(
        f"UPDATE {repo.table} SET status = 'ACCEPTED' WHERE row_number = %s", (row_number,)
    )


# ---------------------------------------------------------------------------
# insert_update_cooler (email_update_cooler.sql + cooler_request.sql)
# ---------------------------------------------------------------------------

def test_reenvio_de_fila_pending_actualiza_sin_insertar(repo):
    repo.DB_POSTGRE.insert_update_cooler(cooler(1, "FAB-0001", "DNN-0001"))

    resultado = repo.DB_POSTGRE.insert_update_cooler(cooler(1, "FAB-0001-CORR", "DNN-0001"))

    assert [dict(r) for r in resultado] == [{"request_code": REQUEST, "row_number": 1}]
    assert [(f["row_number"], f["serie_fabricante"]) for f in filas(repo)] == [(1, "FAB-0001-CORR")]


def test_filas_con_ambas_series_vacias_no_colapsan(repo):
    repo.DB_POSTGRE.insert_update_cooler(cooler(1, "", ""))
    repo.DB_POSTGRE.insert_update_cooler(cooler(2, "", ""))

    assert [f["row_number"] for f in filas(repo)] == [1, 2]


@pytest.mark.parametrize("serie_reenviada", ["FAB-0001-CORR", "FAB-0001"], ids=["con_cambios", "identica"])
def test_reenvio_de_fila_accepted_no_inserta_ni_sobrescribe(repo, serie_reenviada, capsys):
    # El log sale también con un reenvío idéntico: no se comparan columnas.
    repo.DB_POSTGRE.insert_update_cooler(cooler(1, "FAB-0001", "DNN-0001"))
    aceptar(repo, 1)

    resultado = repo.DB_POSTGRE.insert_update_cooler(cooler(1, serie_reenviada, "DNN-0001"))

    assert resultado == []
    assert [(f["row_number"], f["serie_fabricante"], f["status"]) for f in filas(repo)] == [
        (1, "FAB-0001", "ACCEPTED")
    ]
    assert "requiere revisión" in capsys.readouterr().out


def test_misma_serie_con_otro_row_number_no_duplica(repo):
    repo.DB_POSTGRE.insert_update_cooler(cooler(1, "FAB-0001", "DNN-0001"))
    aceptar(repo, 1)

    assert repo.DB_POSTGRE.insert_update_cooler(cooler(7, "FAB-0001", "DNN-0001")) == []
    assert len(filas(repo)) == 1


# ---------------------------------------------------------------------------
# update_cooler (update_cooler.sql)
# ---------------------------------------------------------------------------

def test_update_cooler_cuenta_solo_filas_actualizadas(repo):
    repo.DB_POSTGRE.insert_update_cooler(cooler(1, "FAB-0001", "DNN-0001"))
    repo.DB_POSTGRE.insert_update_cooler(cooler(2, "FAB-0002", "DNN-0002"))
    respuesta = pd.DataFrame([
        {"status": "ACCEPTED", "os": "403111", "serial_number": "FAB-0001", "serial_dnn": "DNN-0001"},
        {"status": "ACCEPTED", "os": "403222", "serial_number": "NO-EXISTE", "serial_dnn": ""},
    ])

    assert repo.DB_POSTGRE.update_cooler(REQUEST, respuesta) == 1
    assert [(f["row_number"], f["status"], f["ticket_solicitud"]) for f in filas(repo)] == [
        (1, "ACCEPTED", "403111"),
        (2, "PENDING", None),
    ]


def test_update_cooler_con_series_vacias_no_toca_filas(repo):
    repo.DB_POSTGRE.insert_update_cooler(cooler(1, "", ""))
    repo.DB_POSTGRE.insert_update_cooler(cooler(2, "", ""))
    respuesta = pd.DataFrame([{"status": "REJECTED", "os": "", "serial_number": "", "serial_dnn": ""}])

    assert repo.DB_POSTGRE.update_cooler(REQUEST, respuesta) == 0
    assert {f["status"] for f in filas(repo)} == {"PENDING"}


# ---------------------------------------------------------------------------
# send_email_coolers (cooler_request.sql, carga inicial)
# ---------------------------------------------------------------------------

def test_send_email_coolers_inserta_y_no_duplica_row_number(repo):
    assert repo.DB_POSTGRE.send_email_coolers(cooler(1, "FAB-0001", "DNN-0001"))
    assert repo.DB_POSTGRE.send_email_coolers(cooler(1, "FAB-0009", "DNN-0009")) == []
    assert repo.DB_POSTGRE.send_email_coolers(cooler(2, "", ""))
    assert repo.DB_POSTGRE.send_email_coolers(cooler(3, "", ""))
    assert [f["row_number"] for f in filas(repo)] == [1, 2, 3]
