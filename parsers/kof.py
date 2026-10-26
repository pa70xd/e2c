"""Parser de KOF (Coca-Cola FEMSA). Mismo flujo por hilo que Danone/Penafiel:

  * INIT: correo nuevo con Excel (o texto plano de proyectos especiales) ->
    solicitud con sus registros de ruta y movimiento.
  * REPLY inbound: el cliente agrega filas en el hilo.
  * REPLY outbound: REPARE responde el Excel con la columna OS llena
    (conciliación por serie).
  * reply_to_bot: comandos bot.* (bot/commands.py con el perfil de KOF).

Reglas en config/customers/kof/reglas_kof.py.
"""

import os

from dotenv import load_dotenv

from bot import commands as bot_commands
from bot.perfiles import perfil_kof
from config.customers.kof.reglas_kof import CUSTOMER
from parsers.kof_parse.business import KOF_BUSINESS
from parsers.kof_parse.mensajes import MENSAJES_KOF
from parsers.kof_parse.process_data import KOF_PROCESS
from parsers.kof_parse.reader import KOF_READER
from parsers.kof_parse.sabana import KOF_SABANA
from repository.gen.consultas_postgre import DB_POSTGRE
from src.excel_ingestion import Excel_Ingestion

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"

excel_ingestion = Excel_Ingestion()
msj = MENSAJES_KOF()
db = DB_POSTGRE()
reader = KOF_READER()


def _respuesta(mensaje, attachments=None):
    return {"mensaje": mensaje, "attachments": attachments}


class _KOF_BASE:

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.process = KOF_PROCESS(duckConn)
        self.sabana = KOF_SABANA(duckConn)

    def _adjuntos(self, request_code, aceptados, rechazados):
        tablas = self.sabana.fill(aceptados)
        adjuntos = [excel_ingestion.get_excelv2_attachment(self.duckConn, t, request_code) for t in tablas]
        adjuntos = [a for a in adjuntos if a is not None]
        adjuntos.append(self.process.resultado_xlsx(request_code, aceptados, rechazados))
        return adjuntos


class KOF_INIT(_KOF_BASE):

    async def parse(self, client, user_id, mail_id, mail, customer=CUSTOMER):
        if db.email_init_exist(mail.id) and not DEBUG:
            print("[KOF][ALERT] Correo omitido por existencia")
            return None

        try:
            df, hubo_excel = await reader.get_tabla(client, user_id, mail_id, mail)
        except Exception as e:
            print(f"[KOF][ERROR] Problema al obtener adjuntos: {type(e).__name__}")
            return None

        if df.empty:
            # Excel sin un encabezado de KOF: se avisa. Sin Excel ni texto
            # plano reconocible: no es una solicitud.
            return _respuesta(msj.formato_desconocido()) if hubo_excel else None

        aceptados, rechazados = KOF_BUSINESS.aplicar(df)
        print(f"[KOF][INIT] aceptados={len(aceptados)} rechazados={len(rechazados)}")

        if not aceptados:
            return _respuesta(
                msj.msj_sin_aceptadas(len(rechazados)),
                [self.process.resultado_xlsx(None, aceptados, rechazados)],
            )

        request_code = db.save_email_log_init(self.process.fill_email_model(mail, customer))
        db.send_email_request(self.process.prepare_data_request(request_code, aceptados, customer))
        for cooler in self.process.prepare_data_cooler(request_code, aceptados):
            db.send_email_coolers(cooler)

        return _respuesta(
            msj.msj_init_kof(request_code, mail.web_link, len(aceptados), len(rechazados)),
            self._adjuntos(request_code, aceptados, rechazados),
        )


class KOF_REPLY(_KOF_BASE):

    async def parse(self, client, user_id, mail_id, mail, direccion, customer=CUSTOMER, customer_host=None):
        reply = db.email_reply_validate(conversation_id=mail.conversation_id, subject=mail.subject)
        if reply is None:
            return None

        request_code = reply["request_code"]
        link_email = reply["link_email"]

        result_type = await reader.detectar_tipo_correo(
            client=client, user_id=user_id, mail_id=mail_id, email=mail,
        )

        if direccion == "inbound":
            return await self._inbound(client, user_id, mail_id, request_code, link_email, result_type)

        if direccion == "outbound":
            return await self._outbound(client, user_id, mail_id, mail, request_code, result_type)

        if direccion == "reply_to_bot":
            return await bot_commands.ejecutar(
                perfil_kof(db, msj, self.process),
                result_type,
                bot_commands.solicitud_fija(request_code),
            )

        return None

    async def _inbound(self, client, user_id, mail_id, request_code, link_email, result_type):
        """El cliente agrega filas en el hilo: se insertan después de las que
        ya tiene la solicitud (una serie ya registrada no se duplica)."""
        if not result_type["tiene_excel"]:
            return None

        try:
            df, _ = await reader.get_tabla(client, user_id, mail_id)
        except Exception as e:
            print(f"[KOF][ERROR] Problema al obtener adjuntos de respuesta: {type(e).__name__}")
            return None

        if df.empty:
            return _respuesta(msj.formato_desconocido())

        aceptados, rechazados = KOF_BUSINESS.aplicar(df)
        if aceptados:
            existentes = db.get_cooler_rows(request_code)
            siguiente = max((f["row_number"] for f in existentes), default=0) + 1
            for cooler in self.process.prepare_data_cooler(request_code, aceptados, siguiente):
                db.send_email_coolers(cooler)
            db.update_email_request(request_code)

        return _respuesta(
            msj.msj_add_kof(request_code, link_email, len(aceptados), len(rechazados)),
            self._adjuntos(request_code, aceptados, rechazados),
        )

    async def _outbound(self, client, user_id, mail_id, mail, request_code, result_type):
        """REPARE responde con la columna OS llena: concilia por serie."""
        if not result_type["tiene_excel"] or result_type["tiene_palabra_reservada"]:
            return None

        try:
            df, _ = await reader.get_tabla(client, user_id, mail_id)
        except Exception as e:
            print(f"[KOF][ERROR] Problema al obtener adjuntos de salida: {type(e).__name__}")
            return None

        upd_coolers = self.process.prepare_cooler_update(df)
        if upd_coolers.empty:
            return _respuesta(msj.formato_desconocido())

        db.update_cooler(request_code, upd_coolers)
        db.update_email_request(request_code)
        status = db.get_email_request_status(request_code)

        totales = db.get_total_coolers(request_code)
        totales = totales[0] if totales else dict.fromkeys(
            ("total_coolers", "completed_coolers", "pending_coolers", "failed_coolers"), 0,
        )
        datos = dict(
            url=mail.web_link,
            total=totales["total_coolers"],
            con_os=totales["completed_coolers"],
            sin_os=totales["pending_coolers"],
        )

        if status == "COMPLETED":
            return _respuesta(msj.msj_solicitud_completa_esc1(request_code, **datos))
        return _respuesta(msj.msj_cambios(request_code, desconocidos=totales["failed_coolers"], **datos))
