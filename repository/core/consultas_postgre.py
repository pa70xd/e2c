"""Base común de ``DB_POSTGRE`` (Danone, Gen y Penafiel).

Cada ``repository/<cliente>/consultas_postgre.py`` hace
``from repository.core.consultas_postgre import *`` y declara
``class DB_POSTGRE(DBPostgreBase)`` con SOLO lo que difiere de la base.

La base es el comportamiento de Gen. Las funciones de esta clase se
copian en cada subclase y se ejecutan con los globals del módulo del
cliente (ver ``__init_subclass__``): ``execute_query``, ``COOLER_REQUEST``,
``SQL_FILE_*``... se buscan en ``repository.<cliente>.consultas_postgre``
en cada llamada, igual que cuando cada módulo tenía su copia. Así un
``monkeypatch`` sobre el módulo del cliente sigue aplicando.
"""

import builtins
import dis
import sys
import types
from pathlib import Path
from infrastructure.database.postgres import execute_query
from config.config_general.compact_names import SHORT_NAME_CAT_RUTA
from psycopg2.extras import Json
from dotenv import load_dotenv
import os
import pandas as pd
load_dotenv()

# DEBUG = True
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG:
    DB_SCHEMA = "repare_email_parse"
    EMAILS_LOG_TABLE = "emails_log_qa"
    EMAIL_REQUEST_TABLE = "email_request_qa"
    COOLER_REQUEST_TABLE = "cooler_request_qa"
else:
    DB_SCHEMA = "repare_email_parse"
    EMAILS_LOG_TABLE = "emails_log"
    EMAIL_REQUEST_TABLE = "email_request"
    COOLER_REQUEST_TABLE = "cooler_request"

EMAILS_LOG = f"{DB_SCHEMA}.{EMAILS_LOG_TABLE}"
EMAIL_REQUEST = f"{DB_SCHEMA}.{EMAIL_REQUEST_TABLE}"
COOLER_REQUEST = f"{DB_SCHEMA}.{COOLER_REQUEST_TABLE}"


SQL_FILE = (Path(__file__).resolve().parent.parent / "querys" / "genericas" / "catalogo_ruta.sql")
SQL_FILE_EMAIL_LOG = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_log_init.sql")
SQL_LINK_EMAIL = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_link.sql")
SQL_FILE_EMAIL_REQUEST = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_request.sql")
SQL_FILE_EMAIL_COOLER = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "cooler_request.sql")
SQL_FILE_EMAIL_REPLY_VALIDATE = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_reply_validate.sql")
SQL_FILE_UPDATE_COOLER  = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "update_cooler.sql")
SQL_FILE_UPDATE_REQUEST  = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_request_update.sql")
SQL_FILE_COMPLETE_REQUEST  = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "complete_email_request.sql")
SQL_FILE_CANCEL_REQUEST = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "cancel_email_request.sql")
SQL_FILE_EMAIL_REQUEST_STATUS = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_request_status.sql")
SQL_FILE_CANCEL_PENDING_COOLERS = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "cancel_pending_coolers.sql")
SQL_FILE_COUNT_TOTAL_EMAIL_REQUEST = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_request_total.sql")
SQL_FILE_EMAIL_REQUEST_BOT_STATUS = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_request_bot_status.sql")
SQL_FILE_EMAIL_REQUEST_BOT_GLOBAL = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "global_status_lite.sql")
SQL_FILE_TOTAL_COOLERS = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "total_coolers.sql")
SQL_FILE_EXIST_EMAIL = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_exist_validate.sql")
SQL_FILE_INIT_EXIST = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_init_exist.sql")
SQL_FILE_UPDATE_EMAIL_COOLER = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "email_update_cooler.sql")
SQL_FILE_DISTRIBUIDORA_MOV = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "get_distribuidora_mov.sql")
SQL_FILE_DISTRIBUIDORA_RUTA = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "get_distribuidora_ruta.sql")
SQL_FILE_COOLER_ROWS = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "cooler_rows_by_request.sql")
SQL_FILE_UPDATE_PENDING_ROW = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "update_pending_cooler_row.sql")
SQL_FILE_CANCEL_PENDING_ROW = (Path(__file__).resolve().parent.parent/ "querys"/ "genericas"/ "cancel_pending_cooler_row.sql")

# Lo que cada módulo de cliente re-exporta con ``import *``: los mismos
# nombres de módulo que tenía cuando era una copia completa.
__all__ = [
    "Path", "execute_query", "SHORT_NAME_CAT_RUTA", "Json", "load_dotenv", "os", "pd",
    "DEBUG", "DB_SCHEMA", "EMAILS_LOG_TABLE", "EMAIL_REQUEST_TABLE", "COOLER_REQUEST_TABLE",
    "EMAILS_LOG", "EMAIL_REQUEST", "COOLER_REQUEST",
    "SQL_FILE", "SQL_FILE_EMAIL_LOG", "SQL_LINK_EMAIL", "SQL_FILE_EMAIL_REQUEST",
    "SQL_FILE_EMAIL_COOLER", "SQL_FILE_EMAIL_REPLY_VALIDATE", "SQL_FILE_UPDATE_COOLER",
    "SQL_FILE_UPDATE_REQUEST", "SQL_FILE_COMPLETE_REQUEST", "SQL_FILE_CANCEL_REQUEST",
    "SQL_FILE_EMAIL_REQUEST_STATUS", "SQL_FILE_CANCEL_PENDING_COOLERS",
    "SQL_FILE_COUNT_TOTAL_EMAIL_REQUEST", "SQL_FILE_EMAIL_REQUEST_BOT_STATUS",
    "SQL_FILE_EMAIL_REQUEST_BOT_GLOBAL", "SQL_FILE_TOTAL_COOLERS", "SQL_FILE_EXIST_EMAIL",
    "SQL_FILE_INIT_EXIST", "SQL_FILE_UPDATE_EMAIL_COOLER", "SQL_FILE_DISTRIBUIDORA_MOV",
    "SQL_FILE_DISTRIBUIDORA_RUTA",
    "SQL_FILE_COOLER_ROWS", "SQL_FILE_UPDATE_PENDING_ROW", "SQL_FILE_CANCEL_PENDING_ROW",
    "DBPostgreBase", "anunciar_destino",
]


def anunciar_destino(debug: bool) -> None:
    """El print que cada módulo de cliente hace al importarse."""
    if debug:
        print("[BASEDATOS] dirigido a -> QA")
    else:
        print("[BASEDATOS] dirigido a -> PRODUCCIÓN")


def _globals_usados(code: types.CodeType) -> set[str]:
    nombres = {i.argval for i in dis.get_instructions(code) if i.opname == "LOAD_GLOBAL"}
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            nombres |= _globals_usados(const)
    return nombres


def _copiar_funcion(func: types.FunctionType, namespace: dict, cls: type) -> types.FunctionType:
    copia = types.FunctionType(func.__code__, namespace, func.__name__, func.__defaults__, func.__closure__)
    copia.__kwdefaults__ = func.__kwdefaults__
    copia.__annotations__ = dict(func.__annotations__)
    copia.__doc__ = func.__doc__
    copia.__module__ = cls.__module__
    copia.__qualname__ = f"{cls.__name__}.{func.__name__}"
    return copia


class DBPostgreBase:

    def __init_subclass__(cls, **kwargs):
        # Copia cada staticmethod heredado en la subclase, ligado a los globals
        # del módulo del cliente. Quedan en ``vars(cls)`` (el FakeRepo del
        # harness parchea por ``vars``) y resuelven ``execute_query`` y las
        # constantes en ese módulo, como las copias de antes.
        super().__init_subclass__(**kwargs)
        namespace = sys.modules[cls.__module__].__dict__
        for name, member in vars(DBPostgreBase).items():
            if not isinstance(member, staticmethod) or name in vars(cls):
                continue
            func = member.__func__
            # El nombre de la propia clase (``DB_POSTGRE``) aún no está en el
            # módulo mientras se crea; se resuelve en cada llamada.
            faltan = sorted(
                n for n in _globals_usados(func.__code__)
                if n not in namespace and n != cls.__name__ and not hasattr(builtins, n)
            )
            if faltan:
                raise ImportError(f"{cls.__module__} no define {faltan}, que usa DBPostgreBase.{name}")
            setattr(cls, name, staticmethod(_copiar_funcion(func, namespace, cls)))

    @staticmethod
    def get_available_catalog(cliente: str) -> dict[str, list[str]]:
        cliente_info = SHORT_NAME_CAT_RUTA.get(cliente.upper())

        if cliente_info is None:
            raise ValueError(
                f"No existe configuración para el cliente '{cliente}'."
            )

        catalogo_ruta = cliente_info["catalogo_ruta"]

        clientes_compactos = list(catalogo_ruta.values())

        sql = SQL_FILE.read_text(encoding="utf-8")

        placeholders = ", ".join(["%s"] * len(clientes_compactos))
        query = sql.replace("{clientes}", placeholders)

        rows = execute_query(
            query=query,
            params=tuple(clientes_compactos)
        )

        cliente_por_compacto = {
            compacto: cliente
            for cliente, compacto in catalogo_ruta.items()
        }

        resultado = {
            cliente: []
            for cliente in catalogo_ruta.keys()
        }

        for row in rows:
            cliente = cliente_por_compacto[row["cliente"]]
            resultado[cliente].append(row["categoria"])

        return resultado

    @staticmethod
    def save_email_log_init(email_model) -> None:

        sql = SQL_FILE_EMAIL_LOG.read_text(encoding="utf-8").format(
            emails_log_table = EMAILS_LOG
        )

        id_email = execute_query(
            query=sql,
            params=(
                email_model.graph_message_id,
                email_model.internet_message_id,
                email_model.conversation_id,
                email_model.conversation_index,
                email_model.parent_message_id,
                email_model.change_key,
                email_model.direction,
                email_model.sender_name,
                email_model.sender_email,
                Json(email_model.recipients_to),
                Json(email_model.recipients_cc),
                Json(email_model.recipients_bcc),
                email_model.subject,
                email_model.body,
                email_model.has_attachments,
                email_model.attachment_count,
                email_model.processing_status,
                email_model.processing_message,
                email_model.received_at,
                email_model.sent_at,
                email_model.customer,
                email_model.link_email
            ),
        )

        return id_email[0]["request_code"]

    
    @staticmethod
    def consulta_link_email(email_model) -> None:


        sql = SQL_FILE_EMAIL_LOG.read_text(encoding="utf-8").format(
            emails_log_table = EMAILS_LOG
        )

        id_email = execute_query(
            query=sql,
            params=(
                email_model.graph_message_id,
                email_model.internet_message_id,
                email_model.conversation_id,
                email_model.conversation_index,
                email_model.parent_message_id,
                email_model.change_key,
                email_model.direction,
                email_model.sender_name,
                email_model.sender_email,
                Json(email_model.recipients_to),
                Json(email_model.recipients_cc),
                Json(email_model.recipients_bcc),
                email_model.subject,
                email_model.body,
                email_model.has_attachments,
                email_model.attachment_count,
                email_model.processing_status,
                email_model.processing_message,
                email_model.received_at,
                email_model.sent_at,
                email_model.customer,
            ),
        )

        return id_email[0]["request_code"]


    @staticmethod
    def email_init_exist(mail_id: str) -> bool:

        sql = SQL_FILE_INIT_EXIST.read_text(
            encoding="utf-8"
        ).format(
            emails_log_table = EMAILS_LOG
        )


        result = execute_query(
            query=sql,
            params=(mail_id,),
        )

        return bool(result and result[0]["exists_email"])



    @staticmethod
    def send_email_request(parametros):
        sql = SQL_FILE_EMAIL_REQUEST.read_text(encoding="utf-8").format(
            email_request_table = EMAIL_REQUEST
        )

        id_email = execute_query(
            query=sql,
            params=(
                parametros["request_code"],
                parametros["customer"],
                parametros["status"],
                parametros["priority"],
                parametros["total_coolers"],
                parametros["pending_coolers"],
                parametros["completed_coolers"],
                parametros["failed_coolers"],
                parametros["assigned_to"],
            ),
        )

        return id_email

    @staticmethod
    def send_email_coolers(parametros):
        sql = SQL_FILE_EMAIL_COOLER.read_text(
            encoding="utf-8"
        ).format(
            cooler_request_table = COOLER_REQUEST
        )

        serie_fabricante = parametros["serie_fabricante"]
        serie_dnn_bnf = parametros["serie_dnn_bnf"]

        if pd.isna(serie_fabricante):
            serie_fabricante = None
        else:
            serie_fabricante = str(serie_fabricante)

        if pd.isna(serie_dnn_bnf):
            serie_dnn_bnf = None
        else:
            serie_dnn_bnf = str(serie_dnn_bnf)
            
        return execute_query(
            query=sql,
            params=(


                parametros["request_code"],
                parametros["row_number"],


                parametros["id_cliente"],
                parametros["fecha_solicitud"],
                parametros["modelo"],
                serie_fabricante,
                serie_dnn_bnf,
                parametros["tipo_servicio"],
                parametros["canal"],
                parametros["region"],
                parametros["plaza"],
                parametros["razon_social"],
                parametros["direccion"],
                parametros["cp"],
                parametros["ciudad"],
                parametros["colonia"],
                parametros["latitud"],
                parametros["longitud"],
                parametros["ruta"],
                parametros["telefono_1"],
                parametros["telefono_2"],
                parametros["comentarios"],
                parametros["cbu"],
                parametros["cliente"],
                parametros["os"],


                parametros["status"],
                parametros["rejection_reason"],
                parametros["prioridad"],
                parametros["folio"],
                parametros["ticket_solicitud"],
                parametros["assigned_to"],
                parametros["gestion_observaciones"],
                parametros["fecha_asignacion"],
                parametros["fecha_atencion"],
                parametros["fecha_completado"],

                parametros["request_code"],
                parametros["row_number"],
                serie_fabricante,
                serie_dnn_bnf,

            ),
    )

    @staticmethod
    def _series_insert_update_cooler(parametros):
        #insercion de danone dnn mas insercion de otros
        serie_fabricante = parametros.get("serie_fabricante")
        serie = parametros.get("serie")
        serie_dnn_bnf = parametros.get("serie_dnn_bnf")

        if serie is not None and not pd.isna(serie):
            serie_dnn_bnf = serie

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
    def insert_update_cooler(parametros):
        update_sql = SQL_FILE_UPDATE_EMAIL_COOLER.read_text(
            encoding="utf-8"
        ).format(
            cooler_request_table=COOLER_REQUEST
        )

        insert_sql = SQL_FILE_EMAIL_COOLER.read_text(
            encoding="utf-8"
        ).format(
            cooler_request_table=COOLER_REQUEST
        )

        request_code = parametros["request_code"]
        row_number = parametros["row_number"]

        # ``DB_POSTGRE`` es la subclase del cliente (globals de su módulo).
        serie_fabricante, serie_dnn_bnf = DB_POSTGRE._series_insert_update_cooler(parametros)

        update_params = (
            parametros["id_cliente"],
            parametros["fecha_solicitud"],
            parametros["modelo"],
            serie_fabricante,
            serie_dnn_bnf,
            parametros["tipo_servicio"],
            parametros["canal"],
            parametros["region"],
            parametros["plaza"],
            parametros["razon_social"],
            parametros["direccion"],
            parametros["cp"],
            parametros["ciudad"],
            parametros["colonia"],
            parametros["latitud"],
            parametros["longitud"],
            parametros["ruta"],
            parametros["telefono_1"],
            parametros["telefono_2"],
            parametros["comentarios"],
            parametros["cbu"],
            parametros["cliente"],
            parametros["os"],

            parametros["status"],
            parametros["rejection_reason"],
            parametros["prioridad"],
            parametros["folio"],
            parametros["ticket_solicitud"],
            parametros["assigned_to"],
            parametros["gestion_observaciones"],
            parametros["fecha_asignacion"],
            parametros["fecha_atencion"],
            parametros["fecha_completado"],

            request_code,
            row_number,
        )

        updated = execute_query(
            query=update_sql,
            params=update_params,
        )

        if updated:
            return updated


        insert_params = (
            request_code,
            row_number,

            parametros["id_cliente"],
            parametros["fecha_solicitud"],
            parametros["modelo"],
            serie_fabricante,
            serie_dnn_bnf,
            parametros["tipo_servicio"],
            parametros["canal"],
            parametros["region"],
            parametros["plaza"],
            parametros["razon_social"],
            parametros["direccion"],
            parametros["cp"],
            parametros["ciudad"],
            parametros["colonia"],
            parametros["latitud"],
            parametros["longitud"],
            parametros["ruta"],
            parametros["telefono_1"],
            parametros["telefono_2"],
            parametros["comentarios"],
            parametros["cbu"],
            parametros["cliente"],
            parametros["os"],

            parametros["status"],
            parametros["rejection_reason"],
            parametros["prioridad"],
            parametros["folio"],
            parametros["ticket_solicitud"],
            parametros["assigned_to"],
            parametros["gestion_observaciones"],
            parametros["fecha_asignacion"],
            parametros["fecha_atencion"],
            parametros["fecha_completado"],

            request_code,
            row_number,
            serie_fabricante,
            serie_dnn_bnf,
        )

        inserted = execute_query(
            query=insert_sql,
            params=insert_params,
        )

        if not inserted:
            print(f"[BASEDATOS] cooler reenviado no aplicado (fila no PENDING o serie ya registrada), requiere revisión: request_code={request_code} row_number={row_number}")

        return inserted


    
    @staticmethod
    def email_reply_validate(
        conversation_id: str,
        subject: str,
    ):
        sql = SQL_FILE_EMAIL_REPLY_VALIDATE.read_text(encoding="utf-8").format(
            emails_log_table = EMAILS_LOG
        )

        result = execute_query(
            query=sql,
            params=(
                conversation_id,
                subject,
            ),
        )

        return result[0] if result else None

    @staticmethod
    def update_cooler(request_code: str, df):

        sql = SQL_FILE_UPDATE_COOLER.read_text(
            encoding="utf-8"
        ).format(
            cooler_request_table = COOLER_REQUEST
        )

        updated = 0

        for _, row in df.iterrows():

            result = execute_query(
                query=sql,
                params=(
                    row["status"],
                    row["os"],
                    request_code,
                    row["serial_number"],
                    row["serial_dnn"],
                ),
            )

            if result:
                updated += 1

        return updated


    @staticmethod
    def update_email_request(request_code: str):

        sql = SQL_FILE_UPDATE_REQUEST.read_text(encoding="utf-8").format(
            cooler_request_table = COOLER_REQUEST,
            email_request_table = EMAIL_REQUEST
        )

        result = execute_query(
            query=sql,
            params=(
                request_code,
            ),
        )

        return result

    @staticmethod
    def complete_email_request(request_code: str) -> str | None:

        sql = SQL_FILE_COMPLETE_REQUEST.read_text(encoding="utf-8").format(
            email_request_table = EMAIL_REQUEST
        )

        request_code = execute_query(
            query=sql,
            params=(request_code,),
        )
        return request_code


    @staticmethod
    def cancel_email_request(request_code: str):

        sql = SQL_FILE_CANCEL_REQUEST.read_text(encoding="utf-8").format(
            email_request_table = EMAIL_REQUEST
        )

        result = execute_query(
            query=sql,
            params=(request_code,),
        )

        return result


    @staticmethod
    def get_email_request_status(request_code: str) -> str | None:
 
        sql = SQL_FILE_EMAIL_REQUEST_STATUS.read_text(encoding="utf-8").format(
            email_request_table = EMAIL_REQUEST
        )
    
        result = execute_query(
            query=sql,
            params=(request_code,),
        )
    
        if not result:
            return None
    
        return result[0]["status"]
    
    @staticmethod
    def cancel_pending_coolers(request_code: str):
        sql = SQL_FILE_CANCEL_PENDING_COOLERS.read_text(
            encoding="utf-8"
        ).format(
            cooler_request_table = COOLER_REQUEST
        )
    
        result = execute_query(
            query=sql,
            params=(request_code,),
        )
    
        return result

    @staticmethod
    def get_total_coolers(request_code: str) -> int:
        sql = SQL_FILE_TOTAL_COOLERS.read_text(
            encoding="utf-8"
        ).format(
            email_request_table = EMAIL_REQUEST
        )

        result = execute_query(
            query=sql,
            params=(request_code,),
        )

        if not result:
            return 0

        return result

    
    @staticmethod
    def conversation_exists(conversation_id: str) -> bool:
        sql = SQL_FILE_EXIST_EMAIL.read_text(
            encoding="utf-8"
        ).format(
            emails_log_table = EMAILS_LOG
        )

        result = execute_query(
            query=sql,
            params=(conversation_id,),
        )

        return bool(result and result[0]["exists_conversation"])

    @staticmethod
    def email_request_bot_status(request_code: str):

        sql = SQL_FILE_EMAIL_REQUEST_BOT_STATUS.read_text(
            encoding="utf-8"
        ).format(
            email_request_table = EMAIL_REQUEST,
            cooler_request_table = COOLER_REQUEST
        )

        result = execute_query(
            query=sql,
            params=(request_code,),
        )

        return result[0] if result else None

    @staticmethod
    def get_email_request_global():

        sql = SQL_FILE_EMAIL_REQUEST_BOT_GLOBAL.read_text(
            encoding="utf-8"
        ).format(
            email_request_table = EMAIL_REQUEST,
            cooler_request_table = COOLER_REQUEST
        )

        return execute_query(
            query=sql,
        )


    @staticmethod
    def get_distribuidora_ruta(cp: str, distribuidora:str) -> dict | None:
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

        if not resultado:
            return None

        return resultado[0]

    @staticmethod
    def get_distribuidora_mov(cp: str, distribuidora: str) -> dict | None:
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

        if not resultado or not resultado[0].get("distribuidora"):
            return None

        return resultado[0]

    @staticmethod
    def get_cooler_rows(request_code: str) -> list[dict]:
        """Filas de la solicitud para el contexto del hilo (sin PII):
        row_number, serie_fabricante, serie_dnn_bnf y status."""
        sql = SQL_FILE_COOLER_ROWS.read_text(
            encoding="utf-8"
        ).format(
            cooler_request_table = COOLER_REQUEST
        )

        result = execute_query(
            query=sql,
            params=(request_code,),
        )

        return result or []

    @staticmethod
    def update_pending_cooler_row(request_code: str, row_number: int, cambios: dict):
        """Cambia los campos no vacíos de ``cambios`` en UNA fila PENDING.
        Devuelve las filas tocadas (vacío si la fila no existe o ya no es
        PENDING)."""
        sql = SQL_FILE_UPDATE_PENDING_ROW.read_text(
            encoding="utf-8"
        ).format(
            cooler_request_table = COOLER_REQUEST
        )

        result = execute_query(
            query=sql,
            params=(
                cambios.get("folio"),
                cambios.get("serie_fabricante"),
                cambios.get("serie_dnn_bnf"),
                cambios.get("modelo"),
                cambios.get("tipo_servicio"),
                cambios.get("direccion"),
                request_code,
                row_number,
            ),
        )

        return result or []

    @staticmethod
    def cancel_pending_cooler_row(request_code: str, row_number: int):
        """Cancela UNA fila PENDING. Vacío si no existe o ya no es PENDING."""
        sql = SQL_FILE_CANCEL_PENDING_ROW.read_text(
            encoding="utf-8"
        ).format(
            cooler_request_table = COOLER_REQUEST
        )

        result = execute_query(
            query=sql,
            params=(request_code, row_number),
        )

        return result or []
