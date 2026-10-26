from parsers.core.modelos import llenar_modelo
import pandas as pd
from config.customers.penafiel.movimientos_penafiel import DIC_SABANAS_MOV 
from repository.penafiel.consultas_postgre import DB_POSTGRE
from config.customers.penafiel.datos_esenciales_solicitud import get_cbu_name
from geopy.geocoders import Nominatim

from parsers.gen_parse.catalog import GEN_CATALOG


from parsers.penafiel_parse.process_data import PENAFIEL_PROCESS

import os
import requests
import pandas as pd


import pandas as pd

geolocator = Nominatim(user_agent="mi_app")

db = DB_POSTGRE()

class PENAFIEL_CATALOG:

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.process = PENAFIEL_PROCESS((self.duckConn))
        self.gen_catalog  = GEN_CATALOG((self.duckConn))


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





    def calcula_distribuidora(self, table):

        movimientos = DIC_SABANAS_MOV["MOVIMIENTOS"]
        rutas = DIC_SABANAS_MOV["RUTA"]

        return self.gen_catalog.calcula_distribuidora(
            table,
            get_cbu_name,
            movimientos,
            rutas,
        )


    

    def calcula_modelo(self, table):
        llenar_modelo(self.duckConn, table, "SERIE FABRICANTE", "SERIE")


    def calcula_coordenadas(self, table):
        table = self.gen_catalog.calcula_coordenadas(table)
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
