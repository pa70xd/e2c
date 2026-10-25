# Constantes de módulo (DEBUG, DB_SCHEMA, *_TABLE, SQL_FILE_*), execute_query, pd...:
# la clase base se ejecuta con los globals de este módulo. Ver repository/core/.
from repository.core.consultas_postgre import *  # noqa: F401,F403
from repository.core.consultas_postgre import DBPostgreBase, anunciar_destino

anunciar_destino(DEBUG)  # noqa: F405


class DB_POSTGRE(DBPostgreBase):

    @staticmethod
    def _series_insert_update_cooler(parametros):
        # Danone ignora la columna "serie": solo serie_fabricante y serie_dnn_bnf.
        serie_fabricante = parametros.get("serie_fabricante")
        serie_dnn_bnf = parametros.get("serie_dnn_bnf")

        if pd.isna(serie_fabricante):
            serie_fabricante = None
        else:
            serie_fabricante = str(serie_fabricante)

        if pd.isna(serie_dnn_bnf):
            serie_dnn_bnf = None
        else:
            serie_dnn_bnf = str(serie_dnn_bnf)

        return serie_fabricante, serie_dnn_bnf

    @staticmethod
    def get_distribuidora_ruta(cp: str, distribuidora:str) -> dict | None:
        # Danone además descarta una fila sin "distribuidora".
        cp = str(cp).strip()

        if not cp:
            return None

        sql = SQL_FILE_DISTRIBUIDORA_RUTA.read_text(
            encoding="utf-8"
        )

        resultado = execute_query(
            query=sql,
            params=(cp,distribuidora,),
        )

        if not resultado or not resultado[0].get("distribuidora"):
            return None

        return resultado[0]
