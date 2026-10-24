"""Geocodificación inversa (Latitud/Longitud -> CP/Colonia/Ciudad/Estado/
País) vía Google Maps. Hoy solo la usa Holanda; Danone y Peñafiel tienen su
propia copia idéntica (DANONE_CATALOG.calcula_coordenadas /
DANONE_PROCESS.get_address) pendiente de consolidar aquí."""

import os
import requests


class GEOCODING:

    def __init__(self, duckConn):
        self.duckConn = duckConn

    def get_address(self, latitud, longitud):
        """Una coordenada por llamada; los errores los maneja
        calcula_coordenadas por fila."""

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        API_KEY = os.getenv('MAPS_KEY')

        params = {
            "latlng": f"{latitud},{longitud}",
            "key": API_KEY,
            "language": "es",
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            raise Exception(f"Error HTTP: {response.status_code}")

        data = response.json()

        if data["status"] != "OK":
            raise Exception(
                f"Error de Google Maps: {data['status']} - "
                f"{data.get('error_message', '')}"
            )

        resultado = data["results"][0]

        direccion = resultado.get("formatted_address")

        datos = {
            "direccion": direccion,
            "codigo_postal": None,
            "colonia": None,
            "ciudad": None,
            "estado": None,
            "pais": None,
        }

        for componente in resultado["address_components"]:
            tipos = componente["types"]
            nombre = componente["long_name"]

            if "postal_code" in tipos:
                datos["codigo_postal"] = nombre

            elif "sublocality" in tipos or "neighborhood" in tipos:
                datos["colonia"] = nombre

            elif "locality" in tipos:
                datos["ciudad"] = nombre

            elif "administrative_area_level_1" in tipos:
                datos["estado"] = nombre

            elif "country" in tipos:
                datos["pais"] = nombre

        return datos

    def calcula_coordenadas(self, table):
        """Agrega y llena CP_GEN/COLONIA_GEN/CIUDAD_GEN/ESTADO_GEN/PAIS_GEN
        geocodificando LATITUD/LONGITUD de cada fila."""

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

                resultado = self.get_address(
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
