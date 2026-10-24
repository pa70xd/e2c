from config.customers.danone.columns_names import EXPECTED_COLUMNS
from repository.danone.consultas_postgre import DB_POSTGRE
from config.customers.danone.datos_esenciales_solicitud import get_cbu_names_valid
from config.customers.danone.movimientos_danone import DIC_SABANAS_MOV

from parsers.danone_parse.utils import DANONE_UTILS
from pathlib import Path

utils = DANONE_UTILS()
db = DB_POSTGRE()

class DANONE_BUSINESS:
    
    def __init__(self, duckConn):
        self.duckConn = duckConn

    def business_rules_pre_creation(self, table_name):

        TIPOS_SERVICIO_VALIDOS =  DIC_SABANAS_MOV["MOVIMIENTOS"] + DIC_SABANAS_MOV["RUTA"]

        ruta = Path("config/customers/danone/querys/solicitud_rechazadas.sql")
        sql_rechazadas = (ruta).read_text(encoding="utf-8")

        # print("tabla solicitudes_rechazadas creadas")

        # categorias_disponibles = db.get_available_catalog("DANONE")

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
        # SERIE DNN/BNF o SERIE DE FABRICA
        # ==========================================================

        invalid = self.duckConn.execute(f"""
            SELECT COUNT(*)
            FROM "{table_name}"
            WHERE 
                ("SERIE DNN/BNF" IS NULL OR "SERIE DNN/BNF" = '')
                    and
                ("SERIE FABRICANTE" IS NULL OR "SERIE FABRICANTE" = '')
          
        """).fetchone()[0]

        if invalid > 0:


            rejected = True

            self.duckConn.execute(f"""
                INSERT INTO solicitudes_rechazadas BY NAME
                SELECT
                    * REPLACE ('[RECHAZADO] La serie de fabricante no es válida o no fue encontrada' AS OS)
                FROM "{table_name}"
                WHERE
                ("SERIE DNN/BNF" IS NULL OR "SERIE DNN/BNF" = '')
                    and
                ("SERIE FABRICANTE" IS NULL OR "SERIE FABRICANTE" = '')
            """)

            self.duckConn.execute(f"""
                DELETE FROM "{table_name}"
                WHERE 
                ("SERIE DNN/BNF" IS NULL OR "SERIE DNN/BNF" = '')
                    and
                ("SERIE FABRICANTE" IS NULL OR "SERIE FABRICANTE" = '')
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
            print("Cliente CBU no válido encontrado")
            

            rejected = True

            self.duckConn.execute(f"""
                INSERT INTO solicitudes_rechazadas BY NAME
                SELECT
                    * REPLACE ('[RECHAZADO] Cliente CBU no encontrado' AS OS)
                FROM "{table_name}"
                WHERE
                    CBU IS NULL
                    OR TRIM(CAST(CBU AS VARCHAR)) = ''
                    OR NOT regexp_matches(
                        UPPER(TRIM(CAST(CBU AS VARCHAR))),
                        '^({patron})$'
                    )
            """)

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
            WHERE UPPER("TIPO DE SERVICIO")
            NOT IN ({utils.sql_list(TIPOS_SERVICIO_VALIDOS)})
        """).fetchone()[0]

        if invalid > 0:

            rejected = True

            self.duckConn.execute(f"""
                INSERT INTO solicitudes_rechazadas BY NAME
                SELECT
                    * REPLACE ('[RECHAZADO] Tipo de servicio no reconocido' AS OS)
                FROM "{table_name}"
                WHERE UPPER("TIPO DE SERVICIO")
                NOT IN ({utils.sql_list(TIPOS_SERVICIO_VALIDOS)})
            """)

            self.duckConn.execute(f"""
                DELETE FROM "{table_name}"
                WHERE UPPER("TIPO DE SERVICIO")
                NOT IN ({utils.sql_list(TIPOS_SERVICIO_VALIDOS)})
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

            self.duckConn.execute(f"""
                INSERT INTO solicitudes_rechazadas BY NAME
                SELECT
                    * REPLACE ('[RECHAZADO] Coordenadas geográficas vacías o no válidas' AS OS)
                FROM "{table_name}"
                WHERE
                    "LATITUD" IS NULL
                    OR TRIM("LATITUD") = ''
                    OR "LONGITUD" IS NULL
                    OR TRIM("LONGITUD") = ''
                    OR CAST("LATITUD" AS DOUBLE) = 0
                    OR CAST("LONGITUD" AS DOUBLE) = 0
            """)

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

            # categorias_disponibles = db.get_available_catalog("DANONE")

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
            #                 '[RECHAZADO] Categoría no encontrada' AS OS       
            #             FROM "{table_name}"
            #             WHERE NOT ({condicion})
            #         """)

            #         self.duckConn.execute(f"""
            #             DELETE FROM "{table_name}"
            #             WHERE NOT ({condicion})
            #         """)


        if rejected:
            pass
            print(" [RESULTS] Se detectaron solicitudes rechazadas")
        else:
            self.duckConn.execute(f"""
                DELETE FROM solicitudes_rechazadas
                """)
            

        return missing_tables, rejected