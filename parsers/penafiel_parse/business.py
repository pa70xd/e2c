from config.customers.penafiel.columns_names import EXPECTED_COLUMNS
from repository.penafiel.consultas_postgre import DB_POSTGRE
from config.customers.penafiel.datos_esenciales_solicitud import get_cbu_names_valid
from config.customers.penafiel.movimientos_penafiel import DIC_SABANAS_MOV

from parsers.penafiel_parse.utils import PENAFIEL_UTILS
from pathlib import Path

utils = PENAFIEL_UTILS()
db = DB_POSTGRE()

class PENAFIEL_BUSINESS:
    
    def __init__(self, duckConn):
        self.duckConn = duckConn

    def _insert_rejected_rows(self, table_name, condition, reason):
        self.duckConn.execute(f"""
            INSERT INTO solicitudes_rechazadas (
                "ID CLIENTE",
                "FECHA DE SOLICITUD",
                "MODELO",
                "SERIE FABRICANTE",
                "SERIE",
                "TIPO DE SERVICIO",
                "CANAL",
                "REGION",
                "PLAZA",
                "RAZON SOCIAL",
                "DIRECCION",
                "CP",
                "CIUDAD",
                "COLONIA",
                "LATITUD",
                "LONGITUD",
                "RUTA",
                "TELEFONO 1",
                "TELEFONO 2",
                "COMENTARIOS",
                "CBU",
                "CLIENTE",
                "OS"
            )
            SELECT
                "ID CLIENTE",
                "FECHA DE SOLICITUD",
                "MODELO",
                "SERIE FABRICANTE",
                "SERIE",
                "TIPO DE SERVICIO",
                "CANAL",
                "REGION",
                "PLAZA",
                "RAZON SOCIAL",
                "DIRECCION",
                "CP",
                "CIUDAD",
                "COLONIA",
                "LATITUD",
                "LONGITUD",
                "RUTA",
                "TELEFONO 1",
                "TELEFONO 2",
                "COMENTARIOS",
                "CBU",
                NULL AS "CLIENTE",
                ? AS "OS"
            FROM "{table_name}"
            WHERE {condition}
        """, [reason])

    def business_rules_pre_creation(self, table_name):

        TIPOS_SERVICIO_VALIDOS =  DIC_SABANAS_MOV["MOVIMIENTOS"] + DIC_SABANAS_MOV["RUTA"]

        ruta = Path("config/customers/penafiel/querys/solicitud_rechazadas.sql")
        sql_rechazadas = (ruta).read_text(encoding="utf-8")

        # categorias_disponibles = db.get_available_catalog("PENAFIEL")

        self.duckConn.execute(sql_rechazadas)

        rejected = False
        missing_tables = {}

        # ==========================================================
        # Regla: El Documento solicitante debe contener las columnas
        # básicas para hacer operaciones
        # ==========================================================

        required_columns = EXPECTED_COLUMNS

        columns = {
            row[1].strip().upper()
            for row in self.duckConn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
        }

        missing = required_columns - columns

        if missing:
            missing_tables[table_name] = sorted(missing)
            return missing_tables, False



        # ==========================================================
        # Regla: Debe contar con información indispensable
        # SERIE o SERIE DE FABRICA
        # ==========================================================

        invalid = self.duckConn.execute(f"""
            SELECT COUNT(*)
            FROM "{table_name}"
            WHERE 
                ("SERIE" IS NULL OR "SERIE" = '')          
        """).fetchone()[0]

        if invalid > 0:


            rejected = True

            self._insert_rejected_rows(
                table_name,
                '"SERIE" IS NULL OR "SERIE" = \'\'',
                "[RECHAZADO] La serie de fabricante no es válida o no fue encontrada",
            )

            self.duckConn.execute(f"""
                DELETE FROM "{table_name}"
                WHERE 
                ("SERIE" IS NULL OR "SERIE" = '')
                """)



        # ==========================================================
        # Regla: Cliente válido CBU
        # ==========================================================
        CLIENTES_VALIDOS = get_cbu_names_valid()
        patron = "|".join(c.upper() for c in CLIENTES_VALIDOS)

        invalid = self.duckConn.execute(f"""
            SELECT COUNT(*)
            FROM "{table_name}"
            WHERE
                CBU IS NULL
                OR TRIM(CAST(CBU AS VARCHAR)) = ''
                OR NOT regexp_matches(
                    UPPER(TRIM(CAST(CBU AS VARCHAR))),
                    '^({patron})$'
                )
        """).fetchone()[0]

        

        if invalid > 0:

            rejected = True

            self._insert_rejected_rows(
                table_name,
                f"""
                    CBU IS NULL
                    OR TRIM(CAST(CBU AS VARCHAR)) = ''
                    OR NOT regexp_matches(
                        UPPER(TRIM(CAST(CBU AS VARCHAR))),
                        '^({patron})$'
                    )
                """,
                "[RECHAZADO] Cliente CBU no encontrado",
            )

            self.duckConn.execute(f"""
                DELETE FROM "{table_name}"
            WHERE
                CBU IS NULL
                OR TRIM(CAST(CBU AS VARCHAR)) = ''
                OR NOT regexp_matches(
                    UPPER(TRIM(CAST(CBU AS VARCHAR))),
                    '^({patron})$'
                )
            """)

        # ==========================================================
        # Regla: Tipo de servicio
        # ==========================================================

        invalid = self.duckConn.execute(f"""
            SELECT COUNT(*)
            FROM "{table_name}"
            WHERE UPPER(CAST("TIPO DE SERVICIO" AS VARCHAR))
            NOT IN ({utils.sql_list(TIPOS_SERVICIO_VALIDOS)})
        """).fetchone()[0]

        if invalid > 0:

            rejected = True

            self._insert_rejected_rows(
                table_name,
                f'UPPER(CAST("TIPO DE SERVICIO" AS VARCHAR)) NOT IN ({utils.sql_list(TIPOS_SERVICIO_VALIDOS)})',
                "[RECHAZADO] Tipo de servicio no reconocido",
            )

            self.duckConn.execute(f"""
                DELETE FROM "{table_name}"
                WHERE UPPER(CAST("TIPO DE SERVICIO" AS VARCHAR))
                NOT IN ({utils.sql_list(TIPOS_SERVICIO_VALIDOS)})
            """)

        # ==========================================================
        # Regla: ID CLIENTE
        # ==========================================================

        invalid = self.duckConn.execute(f"""
            SELECT COUNT(*)
            FROM "{table_name}"
            WHERE "ID CLIENTE" IS NULL
            OR TRIM("ID CLIENTE") = ''
        """).fetchone()[0]

        if invalid > 0:

            rejected = True

            self._insert_rejected_rows(
                table_name,
                '"ID CLIENTE" IS NULL OR TRIM("ID CLIENTE") = \'\'',
                "[RECHAZADO] ID de cliente vacío o no válido",
            )

            self.duckConn.execute(f"""
                DELETE FROM "{table_name}"
                WHERE "ID CLIENTE" IS NULL
                OR TRIM("ID CLIENTE") = ''
            """)

        # ==========================================================
        # Regla: Coordenadas
        # ==========================================================
        invalid = self.duckConn.execute(f"""
            SELECT COUNT(*)
            FROM "{table_name}"
            WHERE
                "LATITUD" IS NULL
                OR TRIM("LATITUD") = ''
                OR "LONGITUD" IS NULL
                OR TRIM("LONGITUD") = ''
                OR CAST("LATITUD" AS DOUBLE) = 0
                OR CAST("LONGITUD" AS DOUBLE) = 0
        """).fetchone()[0]

        if invalid > 0:

            rejected = True

            self._insert_rejected_rows(
                table_name,
                """
                    "LATITUD" IS NULL
                    OR TRIM("LATITUD") = ''
                    OR "LONGITUD" IS NULL
                    OR TRIM("LONGITUD") = ''
                    OR CAST("LATITUD" AS DOUBLE) = 0
                    OR CAST("LONGITUD" AS DOUBLE) = 0
                    """,
                    "[RECHAZADO] Coordenadas geográficas vacías o no válidas",
                    )

            self.duckConn.execute(f"""
                DELETE FROM "{table_name}"
                WHERE
                    "LATITUD" IS NULL
                    OR TRIM("LATITUD") = ''
                    OR "LONGITUD" IS NULL
                    OR TRIM("LONGITUD") = ''
                    OR CAST("LATITUD" AS DOUBLE) = 0
                    OR CAST("LONGITUD" AS DOUBLE) = 0
            """)

            # ==========================================================
            # Regla: Categoría permitida para la solicitud
            # ==========================================================

            # print("\n[INFO] Consultando categorías válidas")

            # categorias_disponibles = db.get_available_catalog("PENAFIEL")

            # # Obtiene todas las categorías disponibles sin importar el cliente
            # categorias_validas = {
            #     categoria.upper()
            #     for categorias in categorias_disponibles.values()
            #     for categoria in categorias
            # }

            # if categorias_validas:

            #     condicion = " OR ".join(
            #         f'UPPER("CATEGORIA_GEN") LIKE \'%{categoria}%\''
            #         for categoria in categorias_validas
            #     )

            #     invalid = self.duckConn.execute(f"""
            #         SELECT COUNT(*)
            #         FROM "{table_name}"
            #         WHERE NOT ({condicion})
            #     """).fetchone()[0]

            #     if invalid > 0:

            #         rejected = True

            #         self.duckConn.execute(f"""
            #             INSERT INTO solicitudes_rechazadas
            #             SELECT
            #                 *,
            #                 '[RECHAZADO] Categoría no encontrada' AS OS,
            #                 '{table_name}' AS TABLA_ORIGEN
            #             FROM "{table_name}"
            #             WHERE NOT ({condicion})
            #         """)

            #         self.duckConn.execute(f"""
            #             DELETE FROM "{table_name}"
            #             WHERE NOT ({condicion})
            #         """)


        if rejected:
            print(" [RESULTS] Se detectaron solicitudes rechazadas")
            
            
        else:
            self.duckConn.execute(f"""
                DELETE FROM solicitudes_rechazadas
                """)
            

        return missing_tables, rejected