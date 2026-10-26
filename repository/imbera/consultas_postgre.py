"""Repositorio de Imbera y Torrey (mismo layout, mismas tablas).

Constantes de módulo (DEBUG, DB_SCHEMA, *_TABLE, SQL_FILE_*), execute_query,
pd...: la clase base se ejecuta con los globals de este módulo. Ver
repository/core/. La base es el comportamiento de Gen (sin overrides);
aquí solo se agregan las dos actualizaciones de OS del outbound.
"""

from repository.core.consultas_postgre import *  # noqa: F401,F403
from repository.core.consultas_postgre import DBPostgreBase, anunciar_destino

anunciar_destino(DEBUG)  # noqa: F405

SQL_DIR = Path(__file__).resolve().parent / "querys"  # noqa: F405
SQL_UPDATE_OS_POR_SERIE = SQL_DIR / "imbera_update_os_por_serie.sql"
SQL_UPDATE_OS_POR_FILA = SQL_DIR / "imbera_update_os_por_fila.sql"


def _sql(path):
    return path.read_text(encoding="utf-8").format(cooler_request_table=COOLER_REQUEST)  # noqa: F405


class DB_POSTGRE(DBPostgreBase):

    @staticmethod
    def update_os_por_serie(request_code: str, serie: str, os_value: str) -> int:
        """Outbound con Excel: OS de la fila con esa serie. Regresa cuántas
        filas tocó (0 si la serie no existe o la fila está cancelada)."""
        result = execute_query(  # noqa: F405
            query=_sql(SQL_UPDATE_OS_POR_SERIE),
            params=(os_value, request_code, serie, serie),
        )
        return len(result or [])

    @staticmethod
    def update_os_por_fila(request_code: str, row_number: int, os_value: str) -> int:
        """Outbound desde el texto: OS de una fila PENDING."""
        result = execute_query(  # noqa: F405
            query=_sql(SQL_UPDATE_OS_POR_FILA),
            params=(os_value, request_code, row_number),
        )
        return len(result or [])
