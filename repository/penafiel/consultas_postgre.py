# Constantes de módulo (DEBUG, DB_SCHEMA, *_TABLE, SQL_FILE_*), execute_query, pd...:
# la clase base se ejecuta con los globals de este módulo. Ver repository/core/.
from repository.core.consultas_postgre import *  # noqa: F401,F403
from repository.core.consultas_postgre import DBPostgreBase, anunciar_destino

anunciar_destino(DEBUG)  # noqa: F405


class DB_POSTGRE(DBPostgreBase):

    @staticmethod
    def get_distribuidora_mov(cp: str, distribuidora: str) -> dict | None:
        # Penafiel devuelve la primera fila aunque no traiga "distribuidora".
        cp = str(cp).strip()
        distribuidora = str(distribuidora).strip()

        if not cp:
            return None
        if not distribuidora:
            return None


        sql = SQL_FILE_DISTRIBUIDORA_MOV.read_text(
            encoding="utf-8"
        )

        resultado = execute_query(
            query=sql,
            params=(cp,distribuidora,),
        )

        if not resultado:
            return None

        return resultado[0]
