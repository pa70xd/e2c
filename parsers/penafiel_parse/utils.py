from config.customers.penafiel.columns_names import NAMES_COLUMNS
from config.customers.penafiel.movimientos_penafiel import MOVEMENTS,CREATE_REQUESTS,IGNORE_REQUESTS

from parsers.gen_parse.utils import GEN_UTILS
from parsers.gen_parse.reader import GEN_READER

import re
import pandas as pd

gen_reader = GEN_READER()
gen_utils = GEN_UTILS()

class PENAFIEL_UTILS:


    @staticmethod
    def analizar_proposito(text) -> bool:
        return gen_utils.analizar_proposito( text, MOVEMENTS, CREATE_REQUESTS, IGNORE_REQUESTS )


    @staticmethod
    def unir_tablas(tables: list[dict], duck_conn) -> str:
        if not tables:
            return None

        tabla_destino = tables[0]["table"]

        # Obtener columnas de la primera tabla
        columnas = duck_conn.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{tabla_destino}'
            ORDER BY ordinal_position
        """).fetchall()

        columnas = [c[0] for c in columnas]

        selects = [f'SELECT * FROM "{tabla_destino}"']

        for tabla in tables[1:]:
            nombre = tabla["table"]

            cols = duck_conn.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{nombre}'
                ORDER BY ordinal_position
            """).fetchall()

            cols = [c[0] for c in cols]

            # Si la estructura cambia, regresar la primera tabla sin modificar
            if cols != columnas:
                return tabla_destino

            selects.append(f'SELECT * FROM "{nombre}"')

        union_sql = "\nUNION ALL\n".join(selects)

        duck_conn.execute(f"""
            CREATE OR REPLACE TABLE "{tabla_destino}" AS
            {union_sql}
        """)

        return tabla_destino

    @staticmethod
    def sql_list(values):
        return ", ".join(f"'{v}'" for v in values)

    
    def distinct_type_service(self,table,duckConn):

        type_services = [
            row[0]
            for row in duckConn.execute(
                f'''
                SELECT DISTINCT "TIPO DE SERVICIO"
                FROM {table}
                '''
            ).fetchall()
        ]


        return type_services

    @staticmethod
    def safe_filename(subject, sender, received):
        subject = subject.strip()

        subject = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", subject, flags=re.IGNORECASE)
        subject = re.sub(r'[<>:"/\\|?*]', "", subject)
        subject = re.sub(r"\s+", " ", subject).strip()

        sender = sender.replace("<", "").replace(">", "").strip()

        received = received.strftime("%Y-%m-%d %H-%M")

        return f"{subject} - {sender} - {received}"


    @staticmethod
    def mark_rejected_original_files(duck_conn, temporary_files):
        try:
            return gen_utils.mark_rejected_original_files(
                duck_conn,
                temporary_files,
                NAMES_COLUMNS,
            )
        except Exception:
            gen_reader.cleanup_original_files(temporary_files)
            raise


