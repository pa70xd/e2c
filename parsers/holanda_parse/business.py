from config.customers.holanda.columns_names import (
    EXPECTED_COLUMNS, SABANA_COLUMNS, ORIGENES_CONOCIDOS, COL_ARCHIVO, COL_FILA_EXCEL,
)

# Columnas que se conservan al mover una fila a solicitudes_rechazadas: el
# layout más la ubicación en el archivo original.
_COLUMNAS_RECHAZADAS = SABANA_COLUMNS + [COL_ARCHIVO, COL_FILA_EXCEL]
from config.customers.holanda.reglas_holanda import MARCA_DUPLICADO
from repository.holanda.consultas_postgre import DB_HOLANDA

db = DB_HOLANDA()

_ORIGENES_SQL = ", ".join(f"'{o}'" for o in sorted(ORIGENES_CONOCIDOS))


class HOLANDA_BUSINESS:

    # Llave del EQUIPO para detectar duplicados: CONGELADOR si viene (número
    # limpio, 1:1 con Serie), SERIE si no (llega en formatos inconsistentes).
    # Misma expresión que holanda_series_abiertas.sql en Postgres.
    _SQL_LLAVE_EQUIPO = (
        'COALESCE('
        'NULLIF(TRIM(CAST("CONGELADOR" AS VARCHAR)), \'\'), '
        'NULLIF(TRIM(CAST("SERIE" AS VARCHAR)), \'\')'
        ')'
    )

    def __init__(self, duckConn):
        self.duckConn = duckConn

    def business_rules_pre_creation(self, table_name):
        """Igual que Danone: lo que incumple una regla se MUEVE a
        `solicitudes_rechazadas` con su motivo. Más corto a propósito
        (Holanda es solo ruta, sin catálogos ni garantías)."""

        columnas_rechazadas = ", ".join(f'"{c}" VARCHAR' for c in _COLUMNAS_RECHAZADAS)
        self.duckConn.execute(f"""
            CREATE OR REPLACE TABLE solicitudes_rechazadas (
                {columnas_rechazadas}, MOTIVO VARCHAR, TABLA_ORIGEN VARCHAR
            )
        """)

        # Columnas mínimas presentes
        columns = {
            row[1].strip().upper()
            for row in self.duckConn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
        }
        faltantes = EXPECTED_COLUMNS - columns
        if faltantes:
            return {table_name: sorted(faltantes)}, False

        rechazadas = 0

        # Llave del caso (CASO2) y Serie no vacíos
        rechazadas += self._mover_a_rechazados(
            table_name,
            'WHERE "CASO2" IS NULL OR TRIM(CAST("CASO2" AS VARCHAR)) = \'\' '
            'OR "SERIE" IS NULL OR TRIM(CAST("SERIE" AS VARCHAR)) = \'\'',
            "[RECHAZADO] Caso2 o Serie vacíos o no válidos",
        )

        # Origen reconocido (columna Origen o inferido del sufijo de CASO2)
        rechazadas += self._mover_a_rechazados(
            table_name,
            f"WHERE COALESCE(UPPER(TRIM(CAST(\"ORIGEN\" AS VARCHAR))), '') NOT IN ({_ORIGENES_SQL})",
            "[RECHAZADO] Origen no reconocido (ni en columna Origen ni en sufijo de Caso2) -- revisar formato de Fecha/Telefono manualmente",
        )

        return {}, rechazadas == 0

    def marcar_duplicados_por_equipo(self, table_name):
        """Serie/Congelador identifican el EQUIPO, no el caso: un equipo
        puede tener casos legítimos repetidos en el tiempo, así que solo es
        duplicado si hay otro caso abierto:
          1. INTRA-LOTE: el mismo equipo más de una vez en el archivo. Gana
             el TE más bajo, luego la Fecha más antigua, luego el orden de
             la fila (el número de CASO2 no sirve: H y G son secuencias
             independientes).
          2. CONTRA HISTÓRICO: el equipo ya tiene un caso sin OS en
             Postgres; aplica también al ganador del punto 1.
        Se escribe siempre MARCA_DUPLICADO en OS."""

        llave = self._SQL_LLAVE_EQUIPO
        marcados = set()

        # 1. Intra-lote
        duplicados_intra = self.duckConn.execute(f"""
            SELECT {llave} AS llave, rowid,
                   ROW_NUMBER() OVER (
                       PARTITION BY {llave}
                       ORDER BY
                           TRY_CAST("TE" AS BIGINT) NULLS LAST,
                           TRY_CAST("FECHA" AS TIMESTAMP) NULLS LAST,
                           rowid
                   ) AS orden
            FROM "{table_name}"
            WHERE {llave} IS NOT NULL
            QUALIFY COUNT(*) OVER (PARTITION BY {llave}) > 1
        """).fetchall()

        for llave_equipo, rowid, orden in duplicados_intra:
            marcados.add(llave_equipo)
            if orden > 1:
                self.duckConn.execute(
                    f'UPDATE "{table_name}" SET "OS" = ? WHERE rowid = ?',
                    [MARCA_DUPLICADO, rowid],
                )

        # 2. Contra histórico en Postgres
        llaves_lote = [
            row[0]
            for row in self.duckConn.execute(
                f'SELECT DISTINCT {llave} FROM "{table_name}" WHERE {llave} IS NOT NULL'
            ).fetchall()
            if row[0]
        ]

        for llave_equipo in db.get_equipos_con_caso_abierto(llaves_lote):
            self.duckConn.execute(
                f'UPDATE "{table_name}" SET "OS" = ? WHERE {llave} = ?',
                [MARCA_DUPLICADO, llave_equipo],
            )
            marcados.add(llave_equipo)

        return list(marcados)

    def _mover_a_rechazados(self, table_name, where_clause, motivo) -> int:
        """Mueve las filas que cumplen `where_clause` a
        solicitudes_rechazadas y regresa cuántas fueron. SELECT explícito:
        la tabla de trabajo trae OS/MERMA además de las columnas que se
        conservan (_COLUMNAS_RECHAZADAS)."""

        total = self.duckConn.execute(
            f'SELECT COUNT(*) FROM "{table_name}" {where_clause}'
        ).fetchone()[0]
        if not total:
            return 0

        columnas = ", ".join(f'"{c}"' for c in _COLUMNAS_RECHAZADAS)
        self.duckConn.execute(f"""
            INSERT INTO solicitudes_rechazadas
            SELECT {columnas}, '{motivo}' AS MOTIVO, '{table_name}' AS TABLA_ORIGEN
            FROM "{table_name}"
            {where_clause}
        """)
        self.duckConn.execute(f'DELETE FROM "{table_name}" {where_clause}')
        return total
