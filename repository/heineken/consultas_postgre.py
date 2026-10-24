from pathlib import Path

from infrastructure.database.postgres import execute_query
from repository.danone.consultas_postgre import COOLER_REQUEST, EMAIL_REQUEST
from config.customers.heineken.reglas_heineken import CUSTOMER, CLIENTE_COOLER, FLUJO_D2D, SERIE_GENERICA

SQL_DIR = Path(__file__).resolve().parent / "querys"
SQL_SERIES_ABIERTAS = SQL_DIR / "heineken_series_abiertas.sql"
SQL_SERIE_GENERICA = SQL_DIR / "heineken_generar_serie_generica.sql"
SQL_UPSERT_D2D = SQL_DIR / "heineken_cooler_upsert_d2d.sql"
SQL_INSERT_RUTA = SQL_DIR / "heineken_cooler_insert_ruta.sql"
SQL_MAX_ROW = SQL_DIR / "heineken_max_row_number.sql"
SQL_CONCILIAR_D2D = SQL_DIR / "heineken_conciliar_d2d.sql"
SQL_CONCILIAR_D2D_RESPALDO = SQL_DIR / "heineken_conciliar_d2d_respaldo.sql"
SQL_CONCILIAR_RUTA = SQL_DIR / "heineken_conciliar_ruta.sql"
SQL_SERIE_PENDIENTE = SQL_DIR / "heineken_serie_generica_pendiente.sql"
SQL_REQUEST_BY_CODE = SQL_DIR / "heineken_request_by_code.sql"
SQL_BOT_STATUS = SQL_DIR / "heineken_bot_status.sql"
SQL_GLOBAL_STATUS = SQL_DIR / "heineken_global_status.sql"


def _sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").format(
        cooler_request_table=COOLER_REQUEST,
        email_request_table=EMAIL_REQUEST,
        cliente=CLIENTE_COOLER,
        customer=CUSTOMER,
    )


class DB_HEINEKEN:

    @staticmethod
    def get_series_con_caso_abierto(series: list[str]) -> list[str]:
        if not series:
            return []
        result = execute_query(query=_sql(SQL_SERIES_ABIERTAS), params=(list(series),))
        return [row["serie"] for row in (result or [])]

    @staticmethod
    def guardar_casos(request_code: str, filas: list[dict], flujo: str) -> None:
        """D2D: inserta o actualiza por request_code + serie. Ruta: inserta si no existe el ORDEN."""
        if not filas:
            return
        sql = _sql(SQL_UPSERT_D2D if flujo == FLUJO_D2D else SQL_INSERT_RUTA)
        inicio = execute_query(query=_sql(SQL_MAX_ROW), params=(request_code,))[0]["maximo"]
        for numero, fila in enumerate(filas, start=inicio + 1):
            execute_query(query=sql, params={**fila, "request_code": request_code, "row_number": numero})

    @staticmethod
    def conciliar(fila: dict, flujo: str, request_code: str | None = None) -> str | None:
        """Aplica la OS de una fila de la respuesta. Regresa el request_code del caso o None si no se encontró."""
        params = {**fila, "request_code": request_code}
        if (params.get("serie") or "").strip().upper() == SERIE_GENERICA:
            params["serie"] = None
        if flujo == FLUJO_D2D:
            result = None
            if params["serie"]:
                result = execute_query(query=_sql(SQL_CONCILIAR_D2D), params=params)
            if not result:
                result = execute_query(query=_sql(SQL_CONCILIAR_D2D_RESPALDO), params=params)
        else:
            result = execute_query(query=_sql(SQL_CONCILIAR_RUTA), params=params)
        return result[0]["request_code"] if result else None

    @staticmethod
    def serie_generica_pendiente(request_code, cliente, activo, falla, usadas: list[str]) -> str | None:
        result = execute_query(query=_sql(SQL_SERIE_PENDIENTE), params={
            "request_code": request_code, "cliente": cliente, "activo": activo,
            "falla": falla, "usadas": usadas,
        })
        return result[0]["serie"] if result else None

    @staticmethod
    def generar_serie_generica(prefijo: str) -> str:
        """Serie completa (HEI/MOB + fecha + consecutivo) desde Postgres."""
        result = execute_query(query=_sql(SQL_SERIE_GENERICA), params=(prefijo,))
        return result[0]["serie"]

    @staticmethod
    def get_request(request_code: str) -> dict | None:
        """{request_code, status} si el folio existe y es de Heineken."""
        result = execute_query(query=_sql(SQL_REQUEST_BY_CODE), params=(request_code,))
        return dict(result[0]) if result else None

    @staticmethod
    def bot_status(request_code: str) -> dict | None:
        result = execute_query(query=_sql(SQL_BOT_STATUS), params=(request_code,))
        return dict(result[0]) if result else None

    @staticmethod
    def global_status():
        return execute_query(query=_sql(SQL_GLOBAL_STATUS))
