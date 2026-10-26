from pathlib import Path

from infrastructure.database.postgres import execute_query
from repository.core.consultas_postgre import COOLER_REQUEST, EMAIL_REQUEST
from config.customers.oxxo.reglas_oxxo import (
    CLIENTE_COOLER_GARANTIAS,
    CLIENTE_COOLER_MANTENIMIENTO,
    CLIENTES_COOLER,
    CUSTOMER_GARANTIAS,
    CUSTOMER_MANTENIMIENTO,
)

# Oxxo usa las tablas compartidas (email_request, cooler_request) sin cambios
# de esquema. El cabecero del correo y la solicitud los escribe DB_POSTGRE
# (repository.core); aquí solo viven las filas de cooler_request y las
# consultas por folio. Mapeo de columnas:
#
#   Mantenimiento                       Garantía (Seguimiento a Folio)
#   ticket          -> folio            folio                  -> folio
#   CR              -> id_cliente       CR Tienda              -> id_cliente
#   plaza + tienda  -> razon_social     Descripción (Plaza)    -> plaza
#   ubicada en      -> direccion        Dirección de Envío     -> direccion
#   Prestador       -> region           Fecha de generación    -> fecha_solicitud
#   Categoría       -> tipo_servicio    (fijo GARANTIA)        -> tipo_servicio
#   Falla específica-> comentarios      Diagnóstico y/o Falla  -> comentarios
#   Motivo, Propiet.,                   Folio Ref. Mant.       -> ticket_solicitud
#   Prioridad       -> gestion_obs.     Teléfono               -> telefono_1
#                                       Modelo / Numero Serie  -> modelo / serie_fabricante
#                                       Reporta, Equipo, Marca,
#                                       Seguimiento            -> gestion_observaciones
#
# PII (nombre, teléfono, dirección) solo va en estos campos; el correo
# electrónico del solicitante no se guarda (no hay columna). Nada se loguea.
# prioridad es siempre MEDIA (la de la plantilla va en gestion_observaciones).

SQL_DIR = Path(__file__).resolve().parent / "querys"
SQL_INSERT_COOLER = SQL_DIR / "oxxo_cooler_insert.sql"
SQL_COOLER_BY_FOLIO = SQL_DIR / "oxxo_cooler_by_folio.sql"
SQL_ESCALACION = SQL_DIR / "oxxo_cooler_escalacion.sql"
SQL_REQUEST_BY_CODE = SQL_DIR / "oxxo_request_by_code.sql"
SQL_BOT_STATUS = SQL_DIR / "oxxo_bot_status.sql"
SQL_GLOBAL_STATUS = SQL_DIR / "oxxo_global_status.sql"

# Cliente de cooler_request por cliente de email_request.
COOLER_POR_CUSTOMER = {
    CUSTOMER_MANTENIMIENTO: CLIENTE_COOLER_MANTENIMIENTO,
    CUSTOMER_GARANTIAS: CLIENTE_COOLER_GARANTIAS,
}

# Orden de los parámetros de oxxo_cooler_insert.sql después de request_code y
# row_number (llaves de OXXO_PROCESS.fila_*).
CAMPOS_INSERT = (
    "id_cliente", "fecha_solicitud", "modelo", "serie_fabricante", "tipo_servicio",
    "region", "plaza", "razon_social", "direccion", "cp", "ciudad", "colonia",
    "telefono_1", "comentarios", "cliente", "prioridad", "folio",
    "ticket_solicitud", "gestion_observaciones",
)


def _sql(path: Path) -> str:
    """Lee un SQL de Oxxo y le pone las tablas y los clientes (constantes)."""
    clientes = ", ".join(f"'{c}'" for c in CLIENTES_COOLER)
    return path.read_text(encoding="utf-8").format(
        cooler_request_table=COOLER_REQUEST,
        email_request_table=EMAIL_REQUEST,
        clientes=clientes,
    )


class DB_OXXO:

    @staticmethod
    def insert_fila(request_code: str, row_number: int, fila: dict) -> bool:
        """Una OS en cooler_request. False si ya existía el folio (o la
        fila): no se duplica."""
        folio = fila.get("folio")
        resultado = execute_query(
            query=_sql(SQL_INSERT_COOLER),
            params=(
                request_code,
                row_number,
                *(fila.get(campo) for campo in CAMPOS_INSERT),
                request_code,   # NOT EXISTS por request_code + row_number
                row_number,
                folio,          # IS NULL: sin folio no se deduplica por folio
                folio,
            ),
        )
        return bool(resultado)

    @staticmethod
    def get_by_folio(folio: str) -> dict | None:
        """{request_code, row_number, status, cliente} de la solicitud más
        antigua de ese folio en cualquiera de los dos clientes, o None."""
        resultado = execute_query(query=_sql(SQL_COOLER_BY_FOLIO), params=(folio,))
        return dict(resultado[0]) if resultado else None

    @staticmethod
    def marcar_escalacion(request_code: str, row_number: int, nota: str) -> bool:
        """Agrega la nota de escalación a gestion_observaciones de la fila."""
        resultado = execute_query(
            query=_sql(SQL_ESCALACION), params=(nota, request_code, row_number)
        )
        return bool(resultado)

    # Comandos del bot. cancelar/finalizar usan los genéricos de DB_POSTGRE.

    @staticmethod
    def get_request(request_code: str, customer: str) -> dict | None:
        """{request_code, status} si el folio existe y es de ese cliente."""
        resultado = execute_query(query=_sql(SQL_REQUEST_BY_CODE), params=(request_code, customer))
        return dict(resultado[0]) if resultado else None

    @staticmethod
    def bot_status(request_code: str, customer: str) -> dict | None:
        resultado = execute_query(
            query=_sql(SQL_BOT_STATUS),
            params=(COOLER_POR_CUSTOMER[customer], request_code, customer),
        )
        return dict(resultado[0]) if resultado else None

    @staticmethod
    def global_status(customer: str):
        return execute_query(query=_sql(SQL_GLOBAL_STATUS), params=(customer,))
