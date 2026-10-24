from parsers.danone_parse.process_data import DANONE_PROCESS
from config.customers.holanda.reglas_holanda import CUSTOMER


def _v(columna: str) -> str:
    """Texto limpio o NULL (el reader siembra "" en columnas faltantes)."""
    return f"""NULLIF(TRIM(CAST("{columna}" AS VARCHAR)), '')"""


# Campos de Holanda sin columna propia en cooler_request: se empaquetan
# como texto en gestion_observaciones para no perder el dato.
_OBSERVACIONES = (
    ("Nombre cliente", "NOMBRE DEL CLIENTE"),
    ("Estado", "ESTADO"),
    ("Segmento", "SEGMENTO"),
    ("Agrupador", "AGRUPADOR"),
    ("Agencia satelite", "AGENCIA SATELITE"),
    ("Oxxo", "OXXO"),
    ("Sin SAP/Sin Congelador", "SIN SAP / SIN CONGELADOR"),
    ("Proveedor", "PROVEEDOR"),
)

# Una fila por caso, ya con las llaves que espera DB_HOLANDA.insert_coolers
# (ver el mapeo a columnas de cooler_request en
# repository/holanda/consultas_postgre.py).
SQL_COOLERS = f"""
    SELECT
        {_v("SAP")}                  AS sap,
        TRY_CAST("FECHA" AS TIMESTAMP) AS fecha,
        {_v("MODELO")}               AS modelo,
        {_v("SERIE")}                AS serie,
        {_v("CONGELADOR")}           AS congelador,
        {_v("TIPO DE QUEJA")}        AS tipo_queja,
        {_v("CANAL")}                AS canal,
        {_v("REGION")}               AS region,
        {_v("AGENCIA")}              AS agencia,
        {_v("NOMBRE NEGOCIO")}       AS nombre_negocio,
        {_v("CALLE Y NUMERO")}       AS direccion,
        {_v("CP")}                   AS cp,
        {_v("MUNICIPIO")}            AS municipio,
        {_v("COLONIA")}              AS colonia,
        {_v("LATITUD")}              AS latitud,
        {_v("LONGITUD")}             AS longitud,
        {_v("RUTA")}                 AS ruta,
        {_v("TELEFONO")}             AS telefono,
        {_v("CLASIFICADOR DE CASO")} AS clasificador_caso,
        {_v("ORIGEN")}               AS origen,
        {_v("OS")}                   AS os_status,
        UPPER({_v("CASO2")})         AS caso2,
        {_v("TE")}                   AS te,
        NULLIF(CONCAT_WS(' | ', {", ".join(f"'{etiqueta}: ' || {_v(col)}" for etiqueta, col in _OBSERVACIONES)}), '')
                                     AS observaciones
    FROM holanda_sabana
    ORDER BY rowid
"""


class HOLANDA_PROCESS:

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self._danone_process = DANONE_PROCESS(duckConn)

    # Genéricos de DANONE_PROCESS, reusados tal cual.
    def fill_email_model(self, email, customer=CUSTOMER):
        return self._danone_process.fill_email_model(email, customer=customer)

    process_email_request_global = staticmethod(
        DANONE_PROCESS.process_email_request_global
    )

    def prepare_data_request(self, id_email, customer=CUSTOMER):
        total = self.duckConn.execute(
            "SELECT COUNT(*) FROM holanda_sabana"
        ).fetchone()[0]

        return {
            "request_code": id_email,
            "customer": customer,
            "status": "IN_PROGRESS",
            "priority": "MEDIUM",
            "total_coolers": total,
            "pending_coolers": total,
            "completed_coolers": 0,
            "failed_coolers": 0,
            "assigned_to": "NA",
        }

    def prepare_data_coolers(self) -> list[dict]:
        """Filas para DB_HOLANDA.insert_coolers, una por CASO2. Las que
        business.marcar_duplicados_por_equipo marcó traen DUPLICADO en
        os_status."""
        cursor = self.duckConn.execute(SQL_COOLERS)
        columnas = [d[0] for d in cursor.description]
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

    def leer_caso2_y_os_de_respuesta(self, table_name) -> list[tuple[str, str]]:
        """Outbound: pares (CASO2, OS) del Excel de respuesta del operador.
        Si el archivo no trae CASO2 u OS, no hay nada que conciliar."""

        columnas = {
            row[1].strip().upper()
            for row in self.duckConn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
        }
        if not {"CASO2", "OS"} <= columnas:
            return []

        return self.duckConn.execute(f"""
            SELECT UPPER({_v("CASO2")}), {_v("OS")}
            FROM "{table_name}"
            WHERE {_v("CASO2")} IS NOT NULL
              AND {_v("OS")} IS NOT NULL
              AND {_v("OS")} NOT LIKE '[RECHAZADO]%'
        """).fetchall()
