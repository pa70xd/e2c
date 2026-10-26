from infrastructure.tableau.tableau import getPtoVentaData, getModelo, get_modelo_act_ser
import pandas as pd
from parsers.core.modelos import llenar_modelo
from config.config_general.distribuidoras import CATALOG_DISTRIBUIDORAS
from concurrent.futures import ThreadPoolExecutor
from config.customers.danone.model_line_cat import catalog
from config.customers.danone.movimientos_danone import DIC_SABANAS_MOV 
from repository.danone.consultas_postgre import DB_POSTGRE
from config.customers.danone.datos_esenciales_solicitud import get_cbu_name

from concurrent.futures import ThreadPoolExecutor
from geopy.geocoders import Nominatim

from parsers.danone_parse.process_data import DANONE_PROCESS

import os
import requests
import pandas as pd


import pandas as pd

geolocator = Nominatim(user_agent="mi_app")

db = DB_POSTGRE()

class DANONE_CATALOG:

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.process = DANONE_PROCESS((self.duckConn))

    def extract_serie_id(self, table):

        df = self.duckConn.execute(
            f"""
            SELECT DISTINCT
                "ID CLIENTE",
                "SERIE DNN/BNF",
                "SERIE FABRICANTE",
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
            df["SERIE DNN/BNF"]
            .dropna()
            .astype(str)
            .tolist()
        )

        activos = (
            df["SERIE FABRICANTE"]
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
            "activos": activos,
            "tipos_servicio": tipos_servicio,
        }






    @staticmethod
    def _normaliza_cp(valor):
        if pd.isna(valor):
            return ""
        valor = str(valor).strip()
        return "" if valor.lower() in ("", "na", "nan") else valor

    def _resolver_distribuidora(
        self,
        query_func,
        cp_ori,
        cp_gen,
        cbu_key,
        pre_distribuidora,
        cache_distribuidoras,
        cache_cliente,
    ):
        """Intenta con CP_GEN y, si no hay resultado, reintenta con CP (fallback)."""
        cp_gen_norm = self._normaliza_cp(cp_gen)
        cp_ori_norm = self._normaliza_cp(cp_ori)

        cp_primario = cp_gen_norm or cp_ori_norm
        cp_secundario = cp_ori_norm if cp_ori_norm != cp_primario else ""

        for cp in filter(None, dict.fromkeys([cp_primario, cp_secundario])):
            cache_key = (cp, cbu_key)

            # No consulta PostgreSQL más de una vez por el mismo CP y CBU.
            if cache_key not in cache_distribuidoras:
                resultado = query_func(cp, pre_distribuidora)
                cache_distribuidoras[cache_key] = (
                    resultado["distribuidora_id"] if resultado else None
                )
                cache_cliente[cache_key] = (
                    resultado["nombre_resp_pago"] if resultado else None
                )

            if cache_distribuidoras[cache_key] is not None:
                return cp, cache_distribuidoras[cache_key], cache_cliente[cache_key]

        # Ningún CP devolvió resultado; conserva el primario para mantener la clave de cache.
        cp_final = cp_primario or cp_secundario
        if not cp_final:
            return "", None, None

        cache_key = (cp_final, cbu_key)
        return cp_final, cache_distribuidoras.get(cache_key), cache_cliente.get(cache_key)

    def calcula_distribuidora(self, table):

        movimientos = DIC_SABANAS_MOV["MOVIMIENTOS"]
        rutas = DIC_SABANAS_MOV["RUTA"]

        placeholders_mov = ", ".join(["?"] * len(movimientos))
        placeholders_ruta = ", ".join(["?"] * len(rutas))

        df_movimientos = self.duckConn.execute(
            f"""
            SELECT rowid, *
            FROM "{table}"
            WHERE "TIPO DE SERVICIO" IN ({placeholders_mov})
            """,
            movimientos,
        ).fetchdf()

        # print(f"[DEBUG] Registros movimientos: {len(df_movimientos)}")

        df_rutas = self.duckConn.execute(
            f"""
            SELECT rowid, *
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

                cp, distribuidora_id, nombre_resp_pago = self._resolver_distribuidora(
                    db.get_distribuidora_mov,
                    cp_ori,
                    cp_gen,
                    cbu_key,
                    pre_distribuidora,
                    cache_distribuidoras,
                    cache_cliente,
                )

                if not cp:
                    continue

                df_movimientos.at[indice, "CP_KEY"] = cp
                df_movimientos.at[indice, "CBU_KEY"] = cbu_key
                df_movimientos.at[indice, "DISTRIBUIDORA_GEN"] = distribuidora_id
                df_movimientos.at[indice, "CLIENTE"] = nombre_resp_pago

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
                    ["rowid", "CP_KEY", "CBU_KEY", "DISTRIBUIDORA_GEN", "CLIENTE"],
                ]
            )

            if not distribuidoras_por_cp.empty:
                self.duckConn.register(
                    "_distribuidoras_por_cp",
                    distribuidoras_por_cp,
                )
                try:
                    self.duckConn.execute(f'''
                    UPDATE "{table}" AS sabana
                        SET
                    "DISTRIBUIDORA_GEN" = catalogo."DISTRIBUIDORA_GEN",
                    "CLIENTE" = catalogo."CLIENTE"
                        FROM _distribuidoras_por_cp AS catalogo
                        WHERE sabana.rowid = catalogo.rowid
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
                cbu_key = "" if pd.isna(cbu) else str(cbu).strip()
                pre_distribuidora = get_cbu_name(cbu)

                cp, distribuidora_id, nombre_resp_pago = self._resolver_distribuidora(
                    db.get_distribuidora_ruta,
                    cp_ori,
                    cp_gen,
                    cbu_key,
                    pre_distribuidora,
                    cache_distribuidoras,
                    cache_cliente,
                )

                if not cp:
                    continue

                df_rutas.at[indice, "CP_KEY"] = cp
                df_rutas.at[indice, "CBU_KEY"] = cbu_key
                df_rutas.at[indice, "DISTRIBUIDORA_GEN"] = distribuidora_id
                df_rutas.at[indice, "CLIENTE"] = nombre_resp_pago

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
                        "rowid",
                        "CP_KEY",
                        "CBU_KEY",
                        "DISTRIBUIDORA_GEN",
                        "CLIENTE",
                    ],
                ]
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
                            sabana.rowid = catalogo.rowid

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

    

    def calcula_modelo(self, table):
        llenar_modelo(self.duckConn, table, "SERIE FABRICANTE", "SERIE DNN/BNF")


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

                resultado = self.process.get_address(
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




    def tableau_modelo_distribu(self, table):

        id_clientes, series, activos = self.extract_serie_id(table)

        # -----------------------------
        # PUNTOS DE VENTA
        # -----------------------------
        try:
            pto_venta = getPtoVentaData(id_clientes)
        except Exception as e:
            pto_venta = []

        df_pto_venta = pd.DataFrame(pto_venta)

        if not df_pto_venta.empty and "ID_DISTRIBUIDORA" in df_pto_venta.columns:
            df_pto_venta["DISTRIBUIDORA_GEN"] = (
                df_pto_venta["ID_DISTRIBUIDORA"]
                .astype(str)
                .str.strip()
                .map(CATALOG_DISTRIBUIDORAS)
            )
        else:
            df_pto_venta = pd.DataFrame(columns=[
                "ID_PTO_VENTA",
                "ID_DISTRIBUIDORA",
                "DISTRIBUIDORA_GEN",
                "CLIENTE"
            ])

        # -----------------------------
        # MODELOS
        # -----------------------------
        series_activos = series + activos

        with ThreadPoolExecutor(max_workers=1) as executor:

            future_activos = executor.submit(
                get_modelo_act_ser,
                "ACTIVO",
                series_activos,
            )

            future_series = executor.submit(
                get_modelo_act_ser,
                "SERIE",
                series_activos,
            )

            try:
                modelos_activos = future_activos.result()
            except Exception as e:
                modelos_activos = []

            try:
                modelos_series = future_series.result()
            except Exception as e:
                modelos_series = []

        # -----------------------------
        # UNIR RESULTADOS
        # -----------------------------
        dfs = [
            pd.DataFrame(modelos_activos),
            pd.DataFrame(modelos_series),
        ]

        dfs = [df for df in dfs if not df.empty]

        if dfs:
            df_modelos = pd.concat(dfs, ignore_index=True)
        else:
            df_modelos = pd.DataFrame(columns=[
                "ACTIVO",
                "SERIE",
                "MODELO",
                "CATEGORIA",
                "LINEA"
            ])

        # -----------------------------
        # ASEGURAR COLUMNAS
        # -----------------------------
        if df_modelos.empty:
            df_modelos = pd.DataFrame(columns=[
                "ACTIVO",
                "SERIE",
                "MODELO",
                "CATEGORIA",
                "LINEA"
            ])

        # -----------------------------
        # CATÁLOGO
        # -----------------------------
        if not df_modelos.empty and "MODELO" in df_modelos.columns:
            df_modelos[["CATEGORIA", "LINEA"]] = df_modelos["MODELO"].apply(
                lambda x: pd.Series(self.get_categoria_linea(x))
            )

        # -----------------------------
        # REGISTRAR EN DUCKDB
        # -----------------------------
        self.duckConn.register("tmp_mpto", df_pto_venta)
        self.duckConn.register("tmp_modl", df_modelos)

    @staticmethod
    def get_categoria_linea(modelo):
        if pd.isna(modelo):
            return None, None

        modelo = str(modelo).strip().upper()

        for categoria, lineas in catalog.items():
            for linea, modelos in lineas.items():
                for m in modelos:
                    if modelo == str(m).strip().upper():
                        return categoria, linea

        return None, None


    def union_cap_tables(self, table):

        self.duckConn.execute(f"""
            CREATE OR REPLACE TABLE "{table}" AS
            SELECT
                DISTINCT
                s.*,

                -- Información Punto de Venta
                p.DISTRIBUIDORA_GEN AS DISTRIBUIDORA_GEN,
                p.CLIENTE AS CLIENTE,

                -- Información Equipo
                m.ACTIVO AS ACTIVO_GEN,
                LTRIM(m.SERIE, '0') AS SERIE_GEN,
                COALESCE(m.MODELO, s.MODELO) AS MODELO_GEN,
                CAST(m.CATEGORIA AS VARCHAR) AS CATEGORIA_GEN,
                CAST(m.LINEA AS VARCHAR) AS LINEA_GEN

            FROM "{table}" AS s

            LEFT JOIN tmp_mpto AS p
                ON CAST(s."ID CLIENTE" AS VARCHAR) = p.ID_PTO_VENTA

            LEFT JOIN tmp_modl AS m
                ON
                    CAST(s."SERIE DNN/BNF" AS VARCHAR) = m.ACTIVO

                OR

                    LTRIM(CAST(s."SERIE FABRICANTE" AS VARCHAR), '0')
                    =
                LTRIM(m.SERIE, '0')
    """)

    def complet_catalog_line(self, table):

        df = self.duckConn.execute(f"""
            SELECT rowid, MODELO_GEN
            FROM {table}
            WHERE CATEGORIA_GEN IS NULL
            OR CATEGORIA_GEN = ''
            OR LINEA_GEN IS NULL
            OR LINEA_GEN = ''
        """).fetchdf()

        for _, row in df.iterrows():

            modelo = row["MODELO_GEN"]

            if pd.isna(modelo):
                continue

            modelo = str(modelo).strip().upper().split()[0]

            categoria, linea = DANONE_CATALOG.get_categoria_linea(modelo)

            if categoria is not None:
                self.duckConn.execute("""
                    UPDATE {table}
                    SET
                        CATEGORIA_GEN = ?,
                        LINEA_GEN = ?
                    WHERE rowid = ?
                """.format(table=table), [categoria, linea, row["rowid"]])





    def get_address(self, table) -> str:
        """Guarda direcciones geocodificadas de ``table`` en DuckDB."""

        tabla_direcciones = f"{table}_direcciones"

        api_key = os.getenv("GOOGLE_MAPS_API_KEY")

        if not api_key:
            raise ValueError(
                "No se encontró GOOGLE_MAPS_API_KEY en las variables de entorno."
            )

        coordenadas = self.duckConn.execute(
            f'''
            SELECT DISTINCT "LATITUD", "LONGITUD"
            FROM "{table}"
            WHERE "LATITUD" IS NOT NULL
            AND TRIM(CAST("LATITUD" AS VARCHAR)) <> ''
            AND "LONGITUD" IS NOT NULL
            AND TRIM(CAST("LONGITUD" AS VARCHAR)) <> ''
            '''
        ).fetchall()

        resultados = []

        for latitud, longitud in coordenadas:

            # ---------------------------------------------------------
            # Validar coordenadas
            # ---------------------------------------------------------

            try:
                latitude = float(
                    str(latitud).strip().replace(",", ".")
                )

                longitude = float(
                    str(longitud).strip().replace(",", ".")
                )

            except (TypeError, ValueError):


                continue

            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:

                print(
                    f"[WARNING] Coordenadas fuera de rango: "
                    f"latitud={latitude}, longitud={longitude}"
                )

                continue

            # ---------------------------------------------------------
            # Google Maps Reverse Geocoding
            # ---------------------------------------------------------

            try:

                response = requests.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={
                        "latlng": f"{latitude},{longitude}",
                        "key": api_key,
                        "language": "es",
                        "region": "mx",
                    },
                    timeout=10,
                )

                response.raise_for_status()

                data = response.json()

            except requests.RequestException as e:

                continue

            # ---------------------------------------------------------
            # Validar respuesta de Google
            # ---------------------------------------------------------

            if data.get("status") != "OK":

                resultados.append({
                    "LATITUD": latitude,
                    "LONGITUD": longitude,
                    "codigo_postal": None,
                    "ciudad": None,
                    "calle": None,
                    "pais": None,
                    "estado": None,
                })

                continue

            # ---------------------------------------------------------
            # Obtener componentes de dirección
            # ---------------------------------------------------------

            address_components = data["results"][0].get(
                "address_components",
                []
            )

            address = {}

            for component in address_components:

                for component_type in component.get("types", []):

                    address[component_type] = component.get(
                        "long_name"
                    )

            # ---------------------------------------------------------
            # Construir resultado
            # ---------------------------------------------------------

            resultado = {
                "LATITUD": latitude,
                "LONGITUD": longitude,

                "codigo_postal": address.get(
                    "postal_code"
                ),

                "ciudad": (
                    address.get("locality")
                    or address.get("postal_town")
                    or address.get("administrative_area_level_2")
                    or address.get("administrative_area_level_1")
                ),

                "calle": address.get(
                    "route"
                ),

                "pais": address.get(
                    "country"
                ),

                "estado": address.get(
                    "administrative_area_level_1"
                ),
            }

            resultados.append(resultado)

        # ---------------------------------------------------------
        # Crear DataFrame
        # ---------------------------------------------------------

        columnas = [
            "LATITUD",
            "LONGITUD",
            "codigo_postal",
            "ciudad",
            "calle",
            "pais",
            "estado",
        ]

        df_direcciones = pd.DataFrame(
            resultados,
            columns=columnas
        )

        # ---------------------------------------------------------
        # Guardar en DuckDB
        # ---------------------------------------------------------

        self.duckConn.register(
            "_direcciones_geocodificadas",
            df_direcciones
        )

        try:

            self.duckConn.execute(
                f'''
                CREATE OR REPLACE TABLE "{tabla_direcciones}" AS
                SELECT *
                FROM _direcciones_geocodificadas
                '''
            )

        finally:

            self.duckConn.unregister(
                "_direcciones_geocodificadas"
            )


        return tabla_direcciones
