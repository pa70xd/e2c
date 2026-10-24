from config.customers.danone.columns_names import NAMES_COLUMNS
import unicodedata
import base64
import shutil
from io import BytesIO
from pathlib import Path

import pandas as pd

class DanoneAttachments:
    NAMES_COLUMNS = NAMES_COLUMNS
    EXCEL_EXTENSIONS = (".xlsx", ".xls")


    @staticmethod
    async def get(
        client,
        user_id,
        mail_id,
        duck_conn,
        debug=False,
        output_dir="debuger"
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

        # print(" [RESULTS] Archivos recibidos:")
        # for attachment in attachments.value:
        #     print(f"    - {attachment.name}")

        tables = []

        try:

            for index, attachment in enumerate(attachments.value, start=1):

                if not hasattr(attachment, "content_bytes"):
                    continue

                if attachment.name.startswith("~$"):
                    continue

                extension = Path(attachment.name).suffix.lower()

                if extension not in DanoneAttachments.EXCEL_EXTENSIONS:
                    continue

                content = attachment.content_bytes

                if content.startswith(b"UEs"):
                    content = base64.b64decode(content)

                if debug:
                    with open(debug_path / attachment.name, "wb") as file:
                        file.write(content)

                df = pd.read_excel(
                BytesIO(content),
                dtype=str
            )

            # Si la primera fila se tomó como encabezado y era "BNF | IVY"
            if (
                len(df.columns) >= 2
                and str(df.columns[0]).strip().upper() == "BNF"
                and str(df.columns[1]).strip().upper() == "IVY"
            ):
                df = pd.read_excel(
                    BytesIO(content),
                    dtype=str,
                    skiprows=2
                )

            df = DanoneAttachments.normalize_columns(df)


            table_name = f"excel_{index}"

            duck_conn.register("tmp_df", df)

            duck_conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT *
                FROM tmp_df
            """)

            duck_conn.unregister("tmp_df")

            tables.append({
                "name": attachment.name,
                "type": "excel",
                "table": table_name
            })


        finally:
            pass
        #     if debug and debug_path.exists():
        #         shutil.rmtree(debug_path, ignore_errors=True)


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
            DanoneAttachments.normalize(k): v
            for k, v in NAMES_COLUMNS.items()
        }

        columns = {}

        for column in df.columns:
            normalized = DanoneAttachments.normalize(column)
            columns[column] = normalized_catalog.get(normalized, normalized)

        df.rename(columns=columns, inplace=True)

        valid_columns = set(NAMES_COLUMNS.values())
        df = df[[col for col in df.columns if col in valid_columns]]

        return df

   