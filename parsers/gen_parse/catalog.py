import pandas as pd
# from config.customers.penafiel.movimientos_penafiel import DIC_SABANAS_MOV 
from repository.gen.consultas_postgre import DB_POSTGRE
# from config.customers.penafiel.datos_esenciales_solicitud import get_cbu_name
from geopy.geocoders import Nominatim

from parsers.gen_parse.process_data import GEN_PROCESS

import os
import requests
import pandas as pd


import pandas as pd

geolocator = Nominatim(user_agent="mi_app")

db = DB_POSTGRE()

class GEN_CATALOG:

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.gen_process = GEN_PROCESS((self.duckConn))

    def extract_serie_id(self, table):
        df = self.duckConn.execute(
            f"""
            SELECT DISTINCT
                "ID CLIENTE",
                "SERIE",
                "TIPO DE SERVICIO"
            FROM {table}
            WHERE "ID CLIENTE" IS NOT NULL
              AND TRIM(CAST("ID CLIENTE" AS VARCHAR)) NOT IN ('', 'na', 'nan')
            """
        ).fetchdf()

        id_clientes = (
            df["ID CLIENTE"]
            .dropna()
            .astype(str)
            .tolist()
        )

        series = (
            df["SERIE"]
            .dropna()
            .astype(str)
            .tolist()
        )

        tipos_servicio = (
            df["TIPO DE SERVICIO"]
            .dropna()
            .astype(str)
            .tolist()
        )

        return {
            "id_clientes": id_clientes,
            "series": series,
            "tipos_servicio": tipos_servicio,
        }





    def calcula_distribuidora(
                        self, 
        table,
        get_cbu_name,
        movimientos,
        rutas

        ):

        placeholders_mov = ", ".join(["?"] * len(movimientos))
        placeholders_ruta = ", ".join(["?"] * len(rutas))

        df_movimientos = self.duckConn.execute(
            f"""
            SELECT *
            FROM "{table}"
            WHERE "TIPO DE SERVICIO" IN ({placeholders_mov})
            """,
            movimientos,
        ).fetchdf()

        # print(f"[DEBUG] Registros movimientos: {len(df_movimientos)}")

        df_rutas = self.duckConn.execute(
            f"""
            SELECT *
            FROM "{table}"
            WHERE "TIPO DE SERVICIO" IN ({placeholders_ruta})
            """,
            rutas,
        ).fetchdf()

        # print(f"[DEBUG] Registros rutas: {len(df_rutas)}")

        equipos = self.extract_serie_id(table)


        if not df_movimientos.empty:

            # Evita modificar el DataFrame original.
            df_movimientos = df_movimientos.copy()
            df_movimientos["DISTRIBUIDORA_GEN"] = None
            df_movimientos["CLIENTE"] = None
            df_movimientos["CP_KEY"] = None
            df_movimientos["CBU_KEY"] = None

            cache_distribuidoras = {}
            cache_cliente = {}


            for indice, fila in df_movimientos.iterrows():

                cp_ori = fila.get("CP")
                cp_gen = fila.get("CP_GEN")
                cbu = fila.get("CBU")
                cbu_key = "" if pd.isna(cbu) else str(cbu).strip()
                pre_distribuidora = get_cbu_name(cbu)
                # print("CBUKEY->",cbu_key)


                if cp_ori == cp_gen:
                    cp = cp_ori

                else:
                    cp = cp_gen


                if pd.isna(cp) or str(cp).strip() == "":
                    continue

                cp = str(cp).strip()
                cache_key = (cp, cbu_key)
                df_movimientos.at[indice, "CP_KEY"] = cp
                df_movimientos.at[indice, "CBU_KEY"] = cbu_key

                # No consulta PostgreSQL más de una vez por el mismo CP y CBU.
                if cache_key not in cache_distribuidoras:
                    # print(f"Buscando distribuidora:{cp}, {pre_distribuidora}")
                    resultado = db.get_distribuidora_mov(cp, pre_distribuidora)

                    cache_distribuidoras[cache_key] = (
                        resultado["distribuidora_id"]
                        if resultado
                        else None
                    )
                    cache_cliente[cache_key] = (
                        resultado["nombre_resp_pago"]
                        if resultado
                        else None
                    )

                df_movimientos.at[indice, "DISTRIBUIDORA_GEN"] = (
                    cache_distribuidoras[cache_key]
                )

                df_movimientos.at[indice, "CLIENTE"] = (
                    cache_cliente[cache_key]
                )

            # encontrados = df_movimientos["DISTRIBUIDORA_GEN"].notna().sum()

            self.duckConn.execute(
                f'''ALTER TABLE "{table}"
                ADD COLUMN IF NOT EXISTS "DISTRIBUIDORA_GEN" VARCHAR'''
            )
            self.duckConn.execute(
                f'''ALTER TABLE "{table}"
                ADD COLUMN IF NOT EXISTS "CLIENTE" VARCHAR'''
            )

            self.duckConn.execute(
                f'''UPDATE "{table}"
                SET
                    "DISTRIBUIDORA_GEN" = NULL,
                    "CLIENTE" = NULL
                WHERE "TIPO DE SERVICIO" IN ({placeholders_mov})''',
                movimientos,
            )

            distribuidoras_por_cp = (
                df_movimientos.loc[
                    df_movimientos["CP_KEY"].notna(),
                    ["CP_KEY", "CBU_KEY", "DISTRIBUIDORA_GEN", "CLIENTE"],
                ]
                .drop_duplicates(subset=["CP_KEY", "CBU_KEY"])
            )

            if not distribuidoras_por_cp.empty:
                self.duckConn.register(
                    "_distribuidoras_por_cp",
                    distribuidoras_por_cp,
                )
                try:
                    self.duckConn.execute(
                                                f'''UPDATE "{table}" AS sabana
                        SET
                                                        "DISTRIBUIDORA_GEN" = catalogo."DISTRIBUIDORA_GEN",
                                                        "CLIENTE" = catalogo."CLIENTE"
                        FROM _distribuidoras_por_cp AS catalogo
                                                WHERE TRIM(CAST(sabana."CP_GEN" AS VARCHAR)) = catalogo."CP_KEY"
                                                    AND COALESCE(TRIM(CAST(sabana."CBU" AS VARCHAR)), '') = catalogo."CBU_KEY"
                          AND sabana."TIPO DE SERVICIO" IN ({placeholders_mov})''',
                        movimientos,
                    )
                finally:
                    self.duckConn.unregister("_distribuidoras_por_cp")


        if not df_rutas.empty:
           
            # Evita modificar el DataFrame original.
            df_rutas = df_rutas.copy()
            df_rutas["DISTRIBUIDORA_GEN"] = None
            df_rutas["CLIENTE"] = None
            df_rutas["CP_KEY"] = None
            df_rutas["CBU_KEY"] = None

            cache_distribuidoras = {}
            cache_cliente = {}

            for indice, fila in df_rutas.iterrows():

                cp_ori = fila.get("CP")
                cp_gen = fila.get("CP_GEN")
                cbu = fila.get("CBU")
                # print("CBU->",cbu)
    
                cbu_key = "" if pd.isna(cbu) else str(cbu).strip()
                pre_distribuidora = get_cbu_name(cbu)

                if cp_ori == cp_gen:
                    cp = cp_ori

                else:
                    cp = cp_gen



                if pd.isna(cp) or str(cp).strip() == "":
                    continue

                cp = str(cp).strip()
                cache_key = (cp, cbu_key)
                df_rutas.at[indice, "CP_KEY"] = cp
                df_rutas.at[indice, "CBU_KEY"] = cbu_key

                # No consulta PostgreSQL más de una vez por el mismo CP y CBU.
                if cache_key not in cache_distribuidoras:
                    # print(f"Buscando distribuidora:{cp}, {pre_distribuidora}")
                    resultado = db.get_distribuidora_ruta(cp, pre_distribuidora)

                    cache_distribuidoras[cache_key] = (
                        resultado["distribuidora_id"]
                        if resultado
                        else None
                    )

                    cache_cliente[cache_key] = (
                        resultado["nombre_resp_pago"]
                        if resultado
                        else None
                    )

                df_rutas.at[indice, "DISTRIBUIDORA_GEN"] = (
                    cache_distribuidoras[cache_key]
                )

                df_rutas.at[indice, "CLIENTE"] = (
                    cache_cliente[cache_key]
                )

            encontrados = (
                df_rutas["DISTRIBUIDORA_GEN"].notna().sum()
            )

            self.duckConn.execute(
                f'''
                ALTER TABLE "{table}"
                ADD COLUMN IF NOT EXISTS "DISTRIBUIDORA_GEN" VARCHAR
                '''
            )

            self.duckConn.execute(
                f'''
                ALTER TABLE "{table}"
                ADD COLUMN IF NOT EXISTS "CLIENTE" VARCHAR
                '''
            )

            # Limpia únicamente los registros de RUTA.
            self.duckConn.execute(
                f'''
                UPDATE "{table}"
                SET
                    "DISTRIBUIDORA_GEN" = NULL,
                    "CLIENTE" = NULL
                WHERE "TIPO DE SERVICIO"
                    IN ({placeholders_ruta})
                ''',
                rutas,
            )

            distribuidoras_por_cp = (
                df_rutas.loc[
                    df_rutas["CP_KEY"].notna(),
                    [
                        "CP_KEY",
                        "CBU_KEY",
                        "DISTRIBUIDORA_GEN",
                        "CLIENTE",
                    ],
                ]
                .drop_duplicates(subset=["CP_KEY", "CBU_KEY"])
            )

            if not distribuidoras_por_cp.empty:

                self.duckConn.register(
                    "_distribuidoras_por_cp",
                    distribuidoras_por_cp,
                )

                try:

                    self.duckConn.execute(
                        f'''
                        UPDATE "{table}" AS sabana

                        SET
                            "DISTRIBUIDORA_GEN" =
                                catalogo."DISTRIBUIDORA_GEN",

                            "CLIENTE" =
                                catalogo."CLIENTE"

                        FROM _distribuidoras_por_cp AS catalogo

                        WHERE
                            TRIM(
                                CAST(sabana."CP_GEN" AS VARCHAR)
                            ) = catalogo."CP_KEY"

                        AND COALESCE(
                            TRIM(CAST(sabana."CBU" AS VARCHAR)), ''
                        ) = catalogo."CBU_KEY"

                        AND sabana."TIPO DE SERVICIO"
                            IN ({placeholders_ruta})
                        ''',
                        rutas,
                    )

                finally:
                    self.duckConn.unregister(
                        "_distribuidoras_por_cp"
                    )


        if df_movimientos.empty and df_rutas.empty:
            return {
                "movimientos": df_movimientos,
                "rutas": df_rutas,
                "equipos": equipos,
            }


        return {
            "movimientos": df_movimientos,
            "rutas": df_rutas,
            "equipos": equipos,
        }


    

    # def calcula_modelo(self, table):
    #     columnas = (
    #         "ACTIVO_GEN",
    #         "SERIE_GEN",
    #         "MODELO_GEN",
    #         "CATEGORIA_GEN",
    #         "LINEA_GEN",
    #     )

    #     for columna in columnas:
    #         self.duckConn.execute(
    #             f'''ALTER TABLE "{table}"
    #             ADD COLUMN IF NOT EXISTS "{columna}" VARCHAR'''
    #         )


    def calcula_coordenadas(self, table):

        columnas = (
            "CP_GEN",
            "COLONIA_GEN",
            "CIUDAD_GEN",
            "ESTADO_GEN",
            "PAIS_GEN",
        )

        for columna in columnas:
            self.duckConn.execute(
                f'''
                ALTER TABLE "{table}"
                ADD COLUMN IF NOT EXISTS "{columna}" VARCHAR
                '''
            )

        rows = self.duckConn.execute(
            f'''
            SELECT
                rowid,
                LATITUD,
                LONGITUD
            FROM "{table}"
            WHERE LATITUD IS NOT NULL
            AND LONGITUD IS NOT NULL
            '''
        ).fetchall()


        for rowid, latitud, longitud in rows:

            try:

                resultado = self.gen_process.get_address(
                    latitud,
                    longitud
                )

                self.duckConn.execute(
                    f'''
                    UPDATE "{table}"
                    SET
                        CP_GEN = ?,
                        COLONIA_GEN = ?,
                        CIUDAD_GEN = ?,
                        ESTADO_GEN = ?,
                        PAIS_GEN = ?
                    WHERE rowid = ?
                    ''',
                    [
                        resultado.get("codigo_postal"),
                        resultado.get("colonia"),
                        resultado.get("ciudad"),
                        resultado.get("estado"),
                        resultado.get("pais"),
                        rowid,
                    ],
                )

            except Exception as e:

                print(
                    f"Error obteniendo dirección para "
                    f"{latitud}, {longitud}: {e}"
                )

        return table




    # def union_cap_tables(self, table):

    #     self.duckConn.execute(f"""
    #         CREATE OR REPLACE TABLE "{table}" AS
    #         SELECT
    #             DISTINCT
    #             s.*,

    #             -- Información Punto de Venta
    #             p.DISTRIBUIDORA_GEN AS DISTRIBUIDORA_GEN,
    #             p.CLIENTE AS CLIENTE,

    #             -- Información Equipo
    #             m.ACTIVO AS ACTIVO_GEN,
    #             LTRIM(m.SERIE, '0') AS SERIE_GEN,
    #             COALESCE(m.MODELO, s.MODELO) AS MODELO_GEN,
    #             CAST(m.CATEGORIA AS VARCHAR) AS CATEGORIA_GEN,
    #             CAST(m.LINEA AS VARCHAR) AS LINEA_GEN

    #         FROM "{table}" AS s

    #         LEFT JOIN tmp_mpto AS p
    #             ON CAST(s."ID CLIENTE" AS VARCHAR) = p.ID_PTO_VENTA

    #         LEFT JOIN tmp_modl AS m
    #             ON
    #                 CAST(s."SERIE" AS VARCHAR) = m.ACTIVO

    #             OR

    #                 LTRIM(CAST(s."SERIE FABRICANTE" AS VARCHAR), '0')
    #                 =
    #             LTRIM(m.SERIE, '0')
    # """)




    # def get_address(self, table) -> str:
    #     """Guarda direcciones geocodificadas de ``table`` en DuckDB."""

    #     tabla_direcciones = f"{table}_direcciones"

    #     api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    #     if not api_key:
    #         raise ValueError(
    #             "No se encontró GOOGLE_MAPS_API_KEY en las variables de entorno."
    #         )

    #     coordenadas = self.duckConn.execute(
    #         f'''
    #         SELECT DISTINCT "LATITUD", "LONGITUD"
    #         FROM "{table}"
    #         WHERE "LATITUD" IS NOT NULL
    #         AND TRIM(CAST("LATITUD" AS VARCHAR)) <> ''
    #         AND "LONGITUD" IS NOT NULL
    #         AND TRIM(CAST("LONGITUD" AS VARCHAR)) <> ''
    #         '''
    #     ).fetchall()

    #     resultados = []

    #     for latitud, longitud in coordenadas:

    #         # ---------------------------------------------------------
    #         # Validar coordenadas
    #         # ---------------------------------------------------------

    #         try:
    #             latitude = float(
    #                 str(latitud).strip().replace(",", ".")
    #             )

    #             longitude = float(
    #                 str(longitud).strip().replace(",", ".")
    #             )

    #         except (TypeError, ValueError):


    #             continue

    #         if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:

    #             print(
    #                 f"[WARNING] Coordenadas fuera de rango: "
    #                 f"latitud={latitude}, longitud={longitude}"
    #             )

    #             continue

    #         # ---------------------------------------------------------
    #         # Google Maps Reverse Geocoding
    #         # ---------------------------------------------------------

    #         try:

    #             response = requests.get(
    #                 "https://maps.googleapis.com/maps/api/geocode/json",
    #                 params={
    #                     "latlng": f"{latitude},{longitude}",
    #                     "key": api_key,
    #                     "language": "es",
    #                     "region": "mx",
    #                 },
    #                 timeout=10,
    #             )

    #             response.raise_for_status()

    #             data = response.json()

    #         except requests.RequestException as e:

    #             continue

    #         # ---------------------------------------------------------
    #         # Validar respuesta de Google
    #         # ---------------------------------------------------------

    #         if data.get("status") != "OK":

    #             resultados.append({
    #                 "LATITUD": latitude,
    #                 "LONGITUD": longitude,
    #                 "codigo_postal": None,
    #                 "ciudad": None,
    #                 "calle": None,
    #                 "pais": None,
    #                 "estado": None,
    #             })

    #             continue

    #         # ---------------------------------------------------------
    #         # Obtener componentes de dirección
    #         # ---------------------------------------------------------

    #         address_components = data["results"][0].get(
    #             "address_components",
    #             []
    #         )

    #         address = {}

    #         for component in address_components:

    #             for component_type in component.get("types", []):

    #                 address[component_type] = component.get(
    #                     "long_name"
    #                 )

    #         # ---------------------------------------------------------
    #         # Construir resultado
    #         # ---------------------------------------------------------

    #         resultado = {
    #             "LATITUD": latitude,
    #             "LONGITUD": longitude,

    #             "codigo_postal": address.get(
    #                 "postal_code"
    #             ),

    #             "ciudad": (
    #                 address.get("locality")
    #                 or address.get("postal_town")
    #                 or address.get("administrative_area_level_2")
    #                 or address.get("administrative_area_level_1")
    #             ),

    #             "calle": address.get(
    #                 "route"
    #             ),

    #             "pais": address.get(
    #                 "country"
    #             ),

    #             "estado": address.get(
    #                 "administrative_area_level_1"
    #             ),
    #         }

    #         resultados.append(resultado)

    #     # ---------------------------------------------------------
    #     # Crear DataFrame
    #     # ---------------------------------------------------------

    #     columnas = [
    #         "LATITUD",
    #         "LONGITUD",
    #         "codigo_postal",
    #         "ciudad",
    #         "calle",
    #         "pais",
    #         "estado",
    #     ]

    #     df_direcciones = pd.DataFrame(
    #         resultados,
    #         columns=columnas
    #     )

    #     # ---------------------------------------------------------
    #     # Guardar en DuckDB
    #     # ---------------------------------------------------------

    #     self.duckConn.register(
    #         "_direcciones_geocodificadas",
    #         df_direcciones
    #     )

    #     try:

    #         self.duckConn.execute(
    #             f'''
    #             CREATE OR REPLACE TABLE "{tabla_direcciones}" AS
    #             SELECT *
    #             FROM _direcciones_geocodificadas
    #             '''
    #         )

    #     finally:

    #         self.duckConn.unregister(
    #             "_direcciones_geocodificadas"
    #         )


    #     return tabla_direcciones
