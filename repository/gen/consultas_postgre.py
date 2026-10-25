# Constantes de módulo (DEBUG, DB_SCHEMA, *_TABLE, SQL_FILE_*), execute_query, pd...:
# la clase base se ejecuta con los globals de este módulo. Ver repository/core/.
from repository.core.consultas_postgre import *  # noqa: F401,F403
from repository.core.consultas_postgre import DBPostgreBase, anunciar_destino

anunciar_destino(DEBUG)  # noqa: F405


class DB_POSTGRE(DBPostgreBase):
    # Gen es la base: no difiere en nada.
    pass
