"""SQL de Oxxo: cantidad de parámetros (siempre) y ejecución contra un
PostgreSQL LOCAL y desechable (con E2C_TEST_PG_DSN; ver tests/README.md).
Mismo esquema mínimo que tests/sql/test_cooler_sql.py."""

import pytest

import infrastructure.database.postgres as postgres
import repository.oxxo.consultas_postgre as oxxo_repo
from parsers.oxxo_parse.process_data import OXXO_PROCESS
from tests.sql.test_cooler_sql import REAL_EXECUTE_QUERY, _connect, schema  # noqa: F401  (fixture)

psycopg2 = pytest.importorskip("psycopg2")

DB = oxxo_repo.DB_OXXO


def _fila(**cambios):
    fila = {campo: None for campo in oxxo_repo.CAMPOS_INSERT}
    fila.update(cliente="OXXO", prioridad="MEDIA")
    fila.update(cambios)
    return fila


# ---------------------------------------------------------------- sin PostgreSQL

def test_los_parametros_cuadran(monkeypatch):
    llamadas = []

    def falso(query, params=()):
        llamadas.append((query, params))
        return []

    monkeypatch.setattr(oxxo_repo, "execute_query", falso)
    DB.insert_fila("REPARE_000001", 1, _fila(folio="F1"))
    DB.insert_fila("REPARE_000001", 2, _fila())
    DB.get_by_folio("F1")
    DB.marcar_escalacion("REPARE_000001", 1, "nota")
    DB.get_request("REPARE_000001", "oxxo")
    DB.bot_status("REPARE_000001", "oxxo_garantias")
    DB.global_status("oxxo")
    assert len(llamadas) == 7
    for query, params in llamadas:
        assert query.count("%s") == len(params), query.split("\n", 1)[0]


def test_las_filas_de_process_data_traen_todos_los_campos():
    from parsers.oxxo_parse.plantillas import Mantenimiento, Seguimiento

    for fila in (
        OXXO_PROCESS.fila_mantenimiento(Mantenimiento(ticket="10000001")),
        OXXO_PROCESS.fila_garantia(Seguimiento(folio="G1")),
        OXXO_PROCESS.fila_excel({}),
    ):
        assert set(oxxo_repo.CAMPOS_INSERT) <= set(fila)


# ---------------------------------------------------------------- PostgreSQL local

@pytest.fixture
def pg(schema, monkeypatch):
    cooler = f"{schema}.cooler_request"
    email = f"{schema}.email_request"
    conn = _connect()
    with conn, conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        cur.execute(f"DROP TABLE IF EXISTS {cooler}")
        cur.execute(f"DROP TABLE IF EXISTS {email}")
        columnas = ", ".join(f"{c} text" for c in oxxo_repo.CAMPOS_INSERT if c != "fecha_solicitud")
        cur.execute(
            f"CREATE TABLE {cooler} (id serial PRIMARY KEY, request_code text NOT NULL, row_number int, "
            f"status text, fecha_solicitud timestamp, {columnas}, "
            f"created_at timestamp, updated_at timestamp)"
        )
        cur.execute(
            f"CREATE TABLE {email} (request_code text, customer text, status text, priority text, "
            f"total_coolers int, completed_coolers int, pending_coolers int, failed_coolers int, "
            f"assigned_to text, created_at timestamp DEFAULT now(), updated_at timestamp, completed_at timestamp)"
        )
    conn.close()
    monkeypatch.setattr(postgres, "get_connection", _connect)
    monkeypatch.setattr(oxxo_repo, "execute_query", REAL_EXECUTE_QUERY)
    monkeypatch.setattr(oxxo_repo, "COOLER_REQUEST", cooler)
    monkeypatch.setattr(oxxo_repo, "EMAIL_REQUEST", email)
    return cooler, email


def _folios(pg):
    return [tuple(r.values()) for r in REAL_EXECUTE_QUERY(
        f"SELECT request_code, row_number, folio, cliente FROM {pg[0]} ORDER BY id"
    )]


def test_el_mismo_folio_no_se_inserta_dos_veces(pg):
    assert DB.insert_fila("REPARE_000001", 1, _fila(folio="10000001")) is True
    assert DB.insert_fila("REPARE_000002", 1, _fila(folio="10000001")) is False
    assert _folios(pg) == [("REPARE_000001", 1, "10000001", "OXXO")]


def test_el_folio_es_unico_entre_los_dos_buzones(pg):
    assert DB.insert_fila("REPARE_000001", 1, _fila(folio="GAR-1", cliente="OXXO_GARANTIAS")) is True
    assert DB.insert_fila("REPARE_000002", 1, _fila(folio="GAR-1", cliente="OXXO")) is False


def test_el_folio_de_otro_cliente_no_choca(pg):
    REAL_EXECUTE_QUERY(
        f"INSERT INTO {pg[0]} (request_code, row_number, folio, cliente, status) "
        f"VALUES ('REPARE_000009', 1, 'F9', 'HOLANDA', 'PENDING')"
    )
    assert DB.insert_fila("REPARE_000001", 1, _fila(folio="F9")) is True


def test_sin_folio_solo_cuenta_la_fila(pg):
    assert DB.insert_fila("REPARE_000001", 1, _fila()) is True
    assert DB.insert_fila("REPARE_000001", 2, _fila()) is True
    assert DB.insert_fila("REPARE_000002", 1, _fila()) is True
    assert DB.insert_fila("REPARE_000001", 2, _fila()) is False


def test_guarda_los_campos_y_el_status_pending(pg):
    DB.insert_fila("REPARE_000001", 1, _fila(folio="F1", id_cliente="50EJE", tipo_servicio="Refrigeración"))
    [fila] = REAL_EXECUTE_QUERY(f"SELECT status, id_cliente, tipo_servicio, prioridad FROM {pg[0]}")
    assert dict(fila) == {
        "status": "PENDING", "id_cliente": "50EJE", "tipo_servicio": "Refrigeración", "prioridad": "MEDIA",
    }


def test_get_by_folio_devuelve_la_mas_antigua(pg):
    DB.insert_fila("REPARE_000001", 1, _fila(folio="F1", cliente="OXXO_GARANTIAS"))
    assert DB.get_by_folio("NO-EXISTE") is None
    assert DB.get_by_folio("F1") == {
        "request_code": "REPARE_000001", "row_number": 1, "status": "PENDING", "cliente": "OXXO_GARANTIAS",
    }


def test_marcar_escalacion_agrega_sin_cambiar_el_status(pg):
    DB.insert_fila("REPARE_000001", 1, _fila(folio="F1", gestion_observaciones="Reporta: Persona Ejemplo"))
    assert DB.marcar_escalacion("REPARE_000001", 1, "ESCALACION 2026-03-02: sin atender") is True
    assert DB.marcar_escalacion("REPARE_000001", 1, "ESCALACION 2026-03-03: sigue") is True
    assert DB.marcar_escalacion("REPARE_000001", 9, "x") is False
    [fila] = REAL_EXECUTE_QUERY(f"SELECT status, gestion_observaciones FROM {pg[0]}")
    assert fila["status"] == "PENDING"
    assert fila["gestion_observaciones"] == (
        "Reporta: Persona Ejemplo | ESCALACION 2026-03-02: sin atender | ESCALACION 2026-03-03: sigue"
    )


def test_comandos_del_bot_se_acotan_al_cliente(pg):
    cooler, email = pg
    for codigo, customer in (("REPARE_000001", "oxxo"), ("REPARE_000002", "oxxo_garantias"), ("REPARE_000003", "holanda")):
        REAL_EXECUTE_QUERY(
            f"INSERT INTO {email} (request_code, customer, status, total_coolers, completed_coolers, "
            f"pending_coolers, failed_coolers) VALUES (%s, %s, 'IN_PROGRESS', 1, 0, 1, 0)",
            (codigo, customer),
        )
    DB.insert_fila("REPARE_000001", 1, _fila(folio="10000001"))
    DB.insert_fila("REPARE_000002", 1, _fila(folio="GAR-1", cliente="OXXO_GARANTIAS"))

    assert DB.get_request("repare_000001", "oxxo") == {"request_code": "REPARE_000001", "status": "IN_PROGRESS"}
    assert DB.get_request("REPARE_000001", "oxxo_garantias") is None
    assert DB.get_request("REPARE_000003", "oxxo") is None

    estatus = DB.bot_status("REPARE_000001", "oxxo")
    assert estatus["tickets_pending"] == ["10000001"]
    assert DB.bot_status("REPARE_000002", "oxxo") is None
    assert DB.bot_status("REPARE_000002", "oxxo_garantias")["tickets_pending"] == ["GAR-1"]

    assert [r["request_code"] for r in DB.global_status("oxxo")] == ["REPARE_000001"]
