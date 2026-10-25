from parsers.core.tablas import unir_tablas as core_unir_tablas
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


    unir_tablas = staticmethod(core_unir_tablas)

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


