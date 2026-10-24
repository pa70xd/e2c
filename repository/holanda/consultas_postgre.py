from pathlib import Path
from infrastructure.database.postgres import execute_query
from repository.danone.consultas_postgre import COOLER_REQUEST, EMAIL_REQUEST
from config.customers.holanda.reglas_holanda import CUSTOMER, CLIENTE_COOLER
from dotenv import load_dotenv

load_dotenv()

# Holanda usa las tablas compartidas (email_request, cooler_request) sin
# cambios de esquema. Sus campos se acomodan en las columnas de
# cooler_request por analogía; lo que no tiene columna propia va como
# texto en gestion_observaciones. Mapeo (pendiente de revisión de Zuri):
#
#   Caso2 -> folio (llave del caso)     TE -> ticket_solicitud
#   Origen -> cbu                       Fecha -> fecha_solicitud
#   SAP -> id_cliente                   Nombre Negocio -> razon_social
#   Telefono -> telefono_1              Calle y numero -> direccion
#   Colonia -> colonia                  Municipio -> ciudad
#   CP -> cp                            Latitud/Longitud -> latitud/longitud
#   Canal -> canal                      Region -> region
#   Agencia -> plaza                    Ruta -> ruta
#   Tipo de queja -> tipo_servicio      Congelador -> serie_dnn_bnf
#   Modelo -> modelo                    Serie -> serie_fabricante
#   Clasificador de caso -> comentarios OS -> os
#   gestion_observaciones <- Nombre del cliente, Estado, Segmento,
#       Agrupador, Agencia Satelite, Oxxo, Sin SAP/Sin Congelador, Proveedor
#
# Duplicados: la llave del EQUIPO es serie_dnn_bnf (Congelador) o, si no
# hay, serie_fabricante (Serie).

SQL_DIR = Path(__file__).resolve().parent / "querys"
SQL_INSERT_COOLER = SQL_DIR / "holanda_cooler_insert.sql"
SQL_UPDATE_OS_BY_CASO2 = SQL_DIR / "holanda_cooler_update_os.sql"
SQL_EQUIPOS_ABIERTOS = SQL_DIR / "holanda_series_abiertas.sql"
SQL_REQUEST_CODES_BY_CASO2 = SQL_DIR / "holanda_request_codes_by_caso2.sql"
SQL_REQUEST_BY_CODE = SQL_DIR / "holanda_request_by_code.sql"
SQL_BOT_STATUS = SQL_DIR / "holanda_bot_status.sql"
SQL_GLOBAL_STATUS = SQL_DIR / "holanda_global_status.sql"

# Orden de los parámetros de holanda_cooler_insert.sql después de
# request_code y row_number (llaves de HOLANDA_PROCESS.prepare_data_coolers).
CAMPOS_INSERT = (
    "sap", "fecha", "modelo", "serie", "congelador", "tipo_queja", "canal",
    "region", "agencia", "nombre_negocio", "direccion", "cp", "municipio",
    "colonia", "latitud", "longitud", "ruta", "telefono", "clasificador_caso",
    "origen", "os_status", "caso2", "te", "observaciones",
)


def _sql(path: Path) -> str:
    """Lee un SQL de Holanda y le pone las tablas y el cliente."""
    return path.read_text(encoding="utf-8").format(
        cooler_request_table=COOLER_REQUEST,
        email_request_table=EMAIL_REQUEST,
        cliente=CLIENTE_COOLER,
        customer=CUSTOMER,
    )


class DB_HOLANDA:

    @staticmethod
    def insert_coolers(request_code: str, rows: list[dict]) -> None:
        """Un registro por CASO2 en cooler_request. Idempotente por CASO2
        (WHERE NOT EXISTS sobre folio): reprocesar no duplica filas."""

        if not rows:
            return

        sql = _sql(SQL_INSERT_COOLER)

        for row_number, row in enumerate(rows, start=1):
            execute_query(
                query=sql,
                params=(
                    request_code,
                    row_number,
                    *(row.get(campo) for campo in CAMPOS_INSERT),
                    row.get("caso2"),  # para el WHERE NOT EXISTS
                ),
            )

    @staticmethod
    def get_equipos_con_caso_abierto(llaves: list[str]) -> list[str]:
        """Llaves de equipo de Holanda con un caso abierto (sin OS)."""
        if not llaves:
            return []
        result = execute_query(query=_sql(SQL_EQUIPOS_ABIERTOS), params=(list(llaves),))
        return [row["llave"] for row in (result or [])]

    @staticmethod
    def get_request_codes_by_caso2(casos: list[str]) -> list[str]:
        """request_code(s) que dieron de alta esos CASO2 (folio del
        mensaje de outbound)."""
        if not casos:
            return []
        result = execute_query(query=_sql(SQL_REQUEST_CODES_BY_CASO2), params=(list(casos),))
        return [row["request_code"] for row in (result or [])]

    @staticmethod
    def update_os_by_caso2(caso2: str, os_value: str):
        """Outbound: OS por CASO2, sin importar su email_request."""
        return execute_query(query=_sql(SQL_UPDATE_OS_BY_CASO2), params=(os_value, caso2))

    # Comandos del bot. cancelar/finalizar usan los genéricos de
    # DB_POSTGRE; estos tres existen porque los genéricos no sirven tal
    # cual para Holanda.

    @staticmethod
    def get_request(request_code: str) -> dict | None:
        """{request_code, status} si el folio existe y es de Holanda."""
        result = execute_query(query=_sql(SQL_REQUEST_BY_CODE), params=(request_code,))
        return dict(result[0]) if result else None

    @staticmethod
    def bot_status(request_code: str) -> dict | None:
        """Misma forma que DB_POSTGRE.email_request_bot_status (para
        msj_status_solicitud), con listas por CASO2 en lugar de TE."""
        result = execute_query(query=_sql(SQL_BOT_STATUS), params=(request_code,))
        return dict(result[0]) if result else None

    @staticmethod
    def global_status():
        """Todas las solicitudes de Holanda."""
        return execute_query(query=_sql(SQL_GLOBAL_STATUS))
