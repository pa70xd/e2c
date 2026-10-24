from config.customers.heineken.columns_names import EXPECTED_D2D, EXPECTED_RUTA
from config.customers.heineken.reglas_heineken import (
    FLUJO_D2D, SERIE_GENERICA, MARCA_DUPLICADO, SOLICITUD_D2D, TIPO_MOVIMIENTO_RUTA,
    CANAL_A_PUESTO, PUESTO_A_DISTRIBUIDORA, SERVICIOS_D2D,
)
from repository.heineken.consultas_postgre import DB_HEINEKEN

db = DB_HEINEKEN()

# Columnas que agrega traducir_d2d, en el orden de SERVICIOS_D2D.
_CAMPOS_SERVICIO = ("CATEGORIA", "LINEA", "TIPO_SERVICIO", "ID_SERVICIO",
                    "TIPO_ACTIVIDAD", "ACTIVIDAD", "PREFIJO_SERIE")


def _lit(valor) -> str:
    return "NULL" if valor is None else "'" + str(valor).replace("'", "''") + "'"


def _case(expresion: str, mapa: dict) -> str:
    ramas = " ".join(f"WHEN {_lit(k)} THEN {_lit(v)}" for k, v in mapa.items())
    return f"CASE {expresion} {ramas} ELSE NULL END"


def _norm(columna: str) -> str:
    return f'UPPER(TRIM("{columna}"))'


class HEINEKEN_BUSINESS:

    def __init__(self, duckConn):
        self.duckConn = duckConn

    def faltantes(self, archivos: list[dict], flujo: str) -> dict:
        """{archivo: columnas mínimas que no venían}."""
        esperadas = EXPECTED_D2D if flujo == FLUJO_D2D else EXPECTED_RUTA
        return {
            a["name"]: sorted(esperadas - a.get("presentes", set()))
            for a in archivos if esperadas - a.get("presentes", set())
        }

    def traducir_d2d(self, tabla: str) -> str:
        """Agrega puesto, distribuidora y servicios según CEDIS/DISTRIBUIDORA y FALLA."""
        canal_o_codigo = {**CANAL_A_PUESTO, **{p: p for p in PUESTO_A_DISTRIBUIDORA}}
        puesto = _case(_norm("DISTRIBUIDORA"), canal_o_codigo)
        servicios = ", ".join(
            f'{_case(_norm("FALLA"), {k: v[i] for k, v in SERVICIOS_D2D.items()})} AS "{campo}"'
            for i, campo in enumerate(_CAMPOS_SERVICIO)
        )
        self.duckConn.execute(f"""
            CREATE OR REPLACE TABLE "{tabla}" AS
            SELECT t.*, {servicios}, p.PUESTO,
                   {_case("p.PUESTO", PUESTO_A_DISTRIBUIDORA)} AS DISTRIBUIDORA_CAT
            FROM "{tabla}" t, LATERAL (SELECT {puesto} AS PUESTO) p
        """)
        return tabla

    def business_rules_pre_creation(self, tabla: str, flujo: str) -> int:
        """Mueve a solicitudes_rechazadas lo que no se puede procesar. Regresa cuántas."""
        self.duckConn.execute(f"""
            CREATE OR REPLACE TABLE solicitudes_rechazadas AS
            SELECT *, CAST(NULL AS VARCHAR) AS MOTIVO FROM "{tabla}" WHERE FALSE
        """)

        sin_serie = f'"SERIE" IS NULL'
        if flujo == FLUJO_D2D:
            reglas = [
                ('"CLIENTE DETALLISTA" IS NULL', "[RECHAZADO] Sin No. CLIENTE DETALLISTA"),
                (sin_serie, "[RECHAZADO] Sin serie"),
                ('"ID_SERVICIO" IS NULL', "[RECHAZADO] FALLA no reconocida"),
                ('"DISTRIBUIDORA_CAT" IS NULL', "[RECHAZADO] Distribuidora no reconocida"),
                (f'COALESCE({_norm("SOLICITUD DE SERVICIO")}, {_lit(SOLICITUD_D2D)}) <> {_lit(SOLICITUD_D2D)}',
                 "[RECHAZADO] Tipo de servicio no soportado (solo MOVIMIENTO)"),
            ]
        else:
            reglas = [
                ('"CP" IS NULL', "[RECHAZADO] Sin código postal"),
                (sin_serie, "[RECHAZADO] Sin serie"),
                (f'COALESCE({_norm("TIPO DE MOVIMIENTO")}, \'\') <> {_lit(TIPO_MOVIMIENTO_RUTA)}',
                 "[RECHAZADO] Tipo de movimiento no soportado (solo REPARACION MERCADO)"),
            ]

        return sum(self._mover_a_rechazados(tabla, condicion, motivo) for condicion, motivo in reglas)

    def marcar_duplicados(self, tabla: str) -> list[str]:
        """OS = DUPLICADO para series reales con un caso abierto en Postgres."""
        series = [
            fila[0] for fila in self.duckConn.execute(f"""
                SELECT DISTINCT "SERIE" FROM "{tabla}"
                WHERE "SERIE" IS NOT NULL AND {_norm("SERIE")} <> {_lit(SERIE_GENERICA)}
            """).fetchall()
        ]
        abiertas = db.get_series_con_caso_abierto(series)
        if abiertas:
            self.duckConn.execute(
                f'UPDATE "{tabla}" SET "OS" = ? WHERE "SERIE" IN (SELECT UNNEST(?))',
                [MARCA_DUPLICADO, abiertas],
            )
        return abiertas

    def _mover_a_rechazados(self, tabla: str, condicion: str, motivo: str) -> int:
        total = self.duckConn.execute(f'SELECT COUNT(*) FROM "{tabla}" WHERE {condicion}').fetchone()[0]
        if total:
            self.duckConn.execute(f"""
                INSERT INTO solicitudes_rechazadas
                SELECT *, {_lit(motivo)} FROM "{tabla}" WHERE {condicion}
            """)
            self.duckConn.execute(f'DELETE FROM "{tabla}" WHERE {condicion}')
        return total
