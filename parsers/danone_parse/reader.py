from parsers.core.correo import detectar_tipo_correo as core_detectar_tipo_correo
import hashlib

from config.customers.danone.columns_names import (
    COL_FILA_ORIGINAL,
    COL_HASH_ORIGINAL,
    NAMES_COLUMNS,
)
from pathlib import Path
from io import BytesIO
import pandas as pd
import unicodedata
import shutil
import base64
import traceback
from io import BytesIO
from pathlib import Path
from config.config_general.palabras_reser import palabras_reservadas
from parsers.gen_parse.reader import GEN_READER


class DANONE_READER:
    NAMES_COLUMNS = NAMES_COLUMNS
    EXCEL_EXTENSIONS = (".xlsx", ".xls")

    @staticmethod
    async def get_adjuntos(
        client,
        user_id,
        mail_id,
        duck_conn,
        debug=False,
        output_dir="Documentos_Adjuntos"
    ):

        debug_path = Path(output_dir)

        if debug:
            shutil.rmtree(debug_path, ignore_errors=True)
            debug_path.mkdir(parents=True, exist_ok=True)

        attachments = await (
            client.users
            .by_user_id(user_id)
            .messages
            .by_message_id(mail_id)
            .attachments
            .get()
        )

        if not attachments.value:
            return []


        tables = []

        for index, attachment in enumerate(attachments.value, start=1):

            # Ignorar adjuntos sin contenido
            if not hasattr(attachment, "content_bytes"):
                continue

            # Ignorar archivos temporales de Excel
            if attachment.name.startswith("~$"):
                continue

            # Solo aceptar archivos Excel
            extension = Path(attachment.name).suffix.lower()
            if extension not in DANONE_READER.EXCEL_EXTENSIONS:
                continue

            content = attachment.content_bytes

            # Algunos archivos llegan codificados en Base64
            if content.startswith(b"UEs"):
                content = base64.b64decode(content)

            if debug:
                with open(debug_path / attachment.name, "wb") as file:
                    file.write(content)

            # Leer únicamente la primera hoja visible
            excel_file = pd.ExcelFile(BytesIO(content))
            if excel_file.engine == "openpyxl":
                visible_sheets = [
                    sheet.title
                    for sheet in excel_file.book.worksheets
                    if sheet.sheet_state == "visible"
                ]
            elif excel_file.engine == "xlrd":
                visible_sheets = [
                    sheet_name
                    for sheet_name, visibility in zip(
                        excel_file.sheet_names,
                        excel_file.book.sheet_visibility
                    )
                    if visibility == 0
                ]
            else:
                visible_sheets = excel_file.sheet_names

            if not visible_sheets:
                continue

            main_sheet = visible_sheets[0]
            df = excel_file.parse(sheet_name=main_sheet, dtype=str)
            first_data_row = 2

            # Algunos archivos tienen encabezado BNF / IVY
            if (
                len(df.columns) >= 2
                and str(df.columns[0]).strip().upper() == "BNF"
                and str(df.columns[1]).strip().upper() == "IVY"
            ):
                df = excel_file.parse(
                    sheet_name=main_sheet,
                    dtype=str,
                    skiprows=2
                )
                first_data_row = 4

            # Normalizar nombres de columnas
            df = DANONE_READER.normalize_columns(df)


            columnas_esperadas = [
                "ID CLIENTE",
                "FECHA DE SOLICITUD",
                "MODELO",
                "SERIE FABRICANTE",
                "SERIE DNN/BNF",
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
                    df[columna] = None

            df[COL_HASH_ORIGINAL] = hashlib.sha256(content).hexdigest()
            df[COL_FILA_ORIGINAL] = (df.index + first_data_row).astype(str)

            # if "CLIENTE" in df.columns:
            #     df["CLIENTE"] = df["CLIENTE"].astype("string")

            table_name = f"excel_{index}"

            duck_conn.register("tmp_df", df)

            duck_conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT *
                FROM tmp_df
            """)
            # columnas_guardadas = [
            #     columna[0]
            #     for columna in duck_conn.execute(
            #         f"DESCRIBE {table_name}"
            #     ).fetchall()
            # ]
            # print(f"Columnas guardadas en {table_name}: {columnas_guardadas}")

 
            duck_conn.unregister("tmp_df")

            tables.append({
                "name": attachment.name,
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
            DANONE_READER.normalize(k): v
            for k, v in NAMES_COLUMNS.items()
        }

        columns = {}

        for column in df.columns:
            normalized = DANONE_READER.normalize(column)
            columns[column] = normalized_catalog.get(normalized, normalized)

        df.rename(columns=columns, inplace=True)

        valid_columns = set(NAMES_COLUMNS.values())
        df = df[[col for col in df.columns if col in valid_columns]]

        return df


    @staticmethod
    async def download_original_files(client, user_id, mail_id):
        return await GEN_READER.download_original_files(
            client,
            user_id,
            mail_id,
            prefix="danone",
        )


    detectar_tipo_correo = staticmethod(core_detectar_tipo_correo)
