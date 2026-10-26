from parsers.core.correo import detectar_tipo_correo as core_detectar_tipo_correo
from config.config_general.palabras_reser import palabras_reservadas
from config.customers.penafiel.columns_names import NAMES_COLUMNS
import unicodedata
import traceback
import shutil
import pandas as pd
from pathlib import Path
from io import BytesIO

from parsers.gen_parse.reader import GEN_READER

gen_reader = GEN_READER()


class PENAFIEL_READER:

    NAMES_COLUMNS = NAMES_COLUMNS
    EXCEL_EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".ods")

    @staticmethod
    async def get_adjuntos(
        client,
        user_id,
        mail_id,
        duck_conn
        # debug=False,
        # output_dir="Documentos_Adjuntos"
    ):

        tables = []

        archivos = await gen_reader.get_adjuntos(
                client,
                user_id,
                mail_id,
                debug=False,
                output_dir="Documentos_Adjuntos"
            )

        for index, archivo in enumerate(archivos, start=1):
            df = archivo["dataframe"]
            df.columns = df.columns.str.upper()
            # Normalizar nombres de columnas
            df = PENAFIEL_READER.normalize_columns(df)

            if "CANAL" not in df.columns:
                df["CANAL"] = "Sin Canal"
            #cliente penafiel no agregan CBU
            if "CBU" not in df.columns:
                df["CBU"] = 'PENAFIEL'

            columnas_esperadas = [
                "ID CLIENTE",
                "FECHA DE SOLICITUD",
                "MODELO",
                "SERIE FABRICANTE",
                "SERIE",
                "TIPO DE SERVICIO",
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
                "OS"
            ]

            # Crear cualquier columna faltante con NULL
            for columna in columnas_esperadas:
                if columna not in df.columns:
                    df[columna] = ""

            falta_serie = (
                df["SERIE"].fillna("").astype(str).str.strip().eq("")
            )
            falta_serie_fabricante = (
                df["SERIE FABRICANTE"]
                .fillna("")
                .astype(str)
                .str.strip()
                .eq("")
            )
            falta_modelo = (
                df["MODELO"].fillna("").astype(str).str.strip().eq("")
            )
            df = df.loc[
                ~(falta_serie & falta_serie_fabricante & falta_modelo)
            ].copy()

            if "CLIENTE" in df.columns:
                df["CLIENTE"] = df["CLIENTE"].astype("string")

            table_name = f"excel_{index}"

            duck_conn.register("tmp_df", df)

            duck_conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT *
                FROM tmp_df
            """)

            duck_conn.unregister("tmp_df")

            tables.append({
                "name": archivo["name"],
                "type": "excel",
                "table": table_name
            })

        return tables
       

    @staticmethod
    def normalize(text: str) -> str:
        text = str(text).strip().upper()

        text = unicodedata.normalize("NFKD", text)
        text = "".join(
            c for c in text
            if not unicodedata.combining(c)
        )

        return " ".join(text.split())


    @staticmethod
    def normalize_columns(df):

        normalized_catalog = {
            PENAFIEL_READER.normalize(k): v
            for k, v in NAMES_COLUMNS.items()
        }

        columns = {}

        for column in df.columns:
            normalized = PENAFIEL_READER.normalize(column)
            columns[column] = normalized_catalog.get(normalized, normalized)

        df.rename(columns=columns, inplace=True)

        valid_columns = set(NAMES_COLUMNS.values())
        df = df[[col for col in df.columns if col in valid_columns]]

        return df


    detectar_tipo_correo = staticmethod(core_detectar_tipo_correo)

    @staticmethod
    async def download_original_files(client, user_id, mail_id):

        return  await gen_reader.download_original_files(client, user_id, mail_id)