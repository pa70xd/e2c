"""Parser de Heineken (cliente.hnk@). Dos flujos según el asunto:
  - D2D (precarga de movimientos): un hilo por día = una solicitud; los reenvíos la actualizan.
  - Ruta (Mantenimiento Ferguez): hilo eterno; cada correo con Excel = una solicitud.
"""

from parsers.heineken_parse.reader import HEINEKEN_READER
from parsers.heineken_parse.business import HEINEKEN_BUSINESS
from parsers.heineken_parse.sabana import HEINEKEN_SABANA
from parsers.heineken_parse.process_data import HEINEKEN_PROCESS
from parsers.heineken_parse.serie_generica import asignar_series_genericas
from parsers.heineken_parse.utils import flujo_por_asunto, originales_pintados, resolver_folio
from parsers.holanda_parse.utils import HOLANDA_UTILS
from parsers.danone_parse.reader import DANONE_READER
from infrastructure.geocoding.geocoding import GEOCODING

from repository.danone.consultas_postgre import DB_POSTGRE
from repository.heineken.consultas_postgre import DB_HEINEKEN

from config.customers.heineken.reglas_heineken import FLUJO_D2D
from config.config_general.messages import MENSAJES_REPARE
from config.config_general.fails_response import get_fail_response as libreria_errores

from src.excel_ingestion import Excel_Ingestion

import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"

excel_ingestion = Excel_Ingestion()
msj = MENSAJES_REPARE()
db = DB_POSTGRE()
db_heineken = DB_HEINEKEN()


def _respuesta(mensaje, attachments=None):
    return {"mensaje": mensaje, "attachments": attachments}


class HEINEKEN_INIT:
    """Correo con Excel que abre una solicitud (o, en D2D, un reenvío a una existente)."""

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.business = HEINEKEN_BUSINESS(duckConn)
        self.sabana = HEINEKEN_SABANA(duckConn)
        self.process = HEINEKEN_PROCESS(duckConn)
        self.geocoding = GEOCODING(duckConn)

    async def parse(self, client, user_id, mail_id, mail, customer=None, request_code=None):
        flujo = flujo_por_asunto(mail.subject)
        if flujo is None:
            print(f"[HEINEKEN][INFO] Asunto no procesado: {mail.subject!r}")
            return None

        if db.email_init_exist(mail.id) and not DEBUG:
            print("[HEINEKEN][ALERT] Correo omitido por existencia")
            return None

        try:
            archivos = await HEINEKEN_READER.get_adjuntos(
                client=client, user_id=user_id, mail_id=mail_id,
                duck_conn=self.duckConn, flujo=flujo,
            )
        except Exception:
            return _respuesta(libreria_errores("adjuntos_02"))

        if not archivos:
            return None if request_code else _respuesta(libreria_errores("adjuntos_01"))

        faltantes = self.business.faltantes(archivos, flujo)
        if faltantes:
            return _respuesta({"status": "ERROR", "missing_columns": faltantes})

        try:
            tabla = HOLANDA_UTILS.unir_tablas(archivos, self.duckConn)
        except Exception:
            return _respuesta(libreria_errores("adjuntos_02"))

        try:
            if flujo == FLUJO_D2D:
                self.business.traducir_d2d(tabla)
            self.business.business_rules_pre_creation(tabla, flujo)
        except Exception:
            return _respuesta(libreria_errores("business_01"))

        self.business.marcar_duplicados(tabla)

        series = {}
        if flujo == FLUJO_D2D:
            series = asignar_series_genericas(self.duckConn, tabla, request_code)
        else:
            self.geocoding.calcula_coordenadas(tabla)

        destino = self.sabana.fill_sabana(tabla, flujo)

        if request_code is None:
            request_code = db.save_email_log_init(self.process.fill_email_model(mail))
            db.send_email_request(self.process.prepare_data_request(request_code, tabla))

        db_heineken.guardar_casos(request_code, self.process.prepare_data_coolers(tabla, flujo, mail), flujo)
        db.update_email_request(request_code)

        presabana = excel_ingestion.get_excelv2_attachment(self.duckConn, destino, request_code)
        adjuntos = originales_pintados(self.duckConn, archivos, series)
        if presabana:
            adjuntos.append(presabana)

        return _respuesta(msj.msj_send_presabana(request_code, mail.web_link), adjuntos)


class HEINEKEN_REPLY:
    """Correos posteriores en el hilo."""

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.init = HEINEKEN_INIT(duckConn)

    async def parse(self, client, user_id, mail_id, mail, direccion, customer=None, customer_email=None):
        flujo = flujo_por_asunto(mail.subject)
        if flujo is None:
            print(f"[HEINEKEN][INFO] Asunto no procesado: {mail.subject!r}")
            return None

        request_code = None
        if flujo == FLUJO_D2D:
            hilo = db.email_reply_validate(conversation_id=mail.conversation_id, subject=mail.subject)
            request_code = hilo["request_code"] if hilo else None

        if direccion == "inbound":
            return await self.init.parse(client, user_id, mail_id, mail, customer, request_code)

        if direccion == "outbound":
            return await self._outbound(client, user_id, mail_id, mail, flujo, request_code)

        if direccion == "reply_to_bot":
            return await self._comando_bot(client, user_id, mail_id, mail, request_code)

        return None

    async def _comando_bot(self, client, user_id, mail_id, mail, request_code):
        """Comandos del operador. Solicitud: D2D por hilo (o folio si no se encuentra); ruta por folio."""
        tipo = await DANONE_READER.detectar_tipo_correo(
            client=client, user_id=user_id, mail_id=mail_id, email=mail,
        )
        if not tipo.get("tiene_palabra_reservada"):
            return None

        palabra = (tipo.get("palabra") or "").lower()

        if palabra in ("bot.help", "bot.ayuda"):
            return _respuesta(msj.msj_ayuda())

        if palabra == "bot.global":
            archivo = None
            try:
                data = db_heineken.global_status()
                if data:
                    archivo = self.init.process.process_email_request_global(data)
            except Exception as e:
                print(f"[HEINEKEN][BOT][ERROR] No se logró generar el estado global: {e}")
            return _respuesta(msj.msj_global(), [archivo] if archivo else None)

        if palabra not in ("bot.estatus", "bot.status", "bot.cancelar", "bot.finalizar", "bot.cerrar"):
            return _respuesta(msj.msj_comando_no_reconocido())

        if request_code is None:
            folio = await resolver_folio(client, user_id, mail_id, mail)
            if not folio:
                return _respuesta(msj.msj_folio_requerido())
            solicitud = db_heineken.get_request(folio)
            if not solicitud:
                return _respuesta(msj.msj_folio_requerido(folio))
            request_code = solicitud["request_code"]

        if palabra in ("bot.estatus", "bot.status"):
            try:
                data = db_heineken.bot_status(request_code)
            except Exception as e:
                print(f"[HEINEKEN][BOT][ERROR] No se logró consultar el estatus de {request_code}: {e}")
                data = None
            if not data:
                return _respuesta(msj.msj_folio_requerido(request_code))
            return _respuesta(msj.msj_status_solicitud(data))

        if palabra == "bot.cancelar":
            # Se cancelan también los casos PENDING para que un outbound no reviva la solicitud.
            try:
                db.cancel_pending_coolers(request_code)
                db.cancel_email_request(request_code)
            except Exception as e:
                print(f"[HEINEKEN][BOT][ERROR] No se logró cancelar {request_code}: {e}")
            return _respuesta(msj.msj_cancelar(request_code))

        try:
            db.complete_email_request(request_code)
        except Exception as e:
            print(f"[HEINEKEN][BOT][ERROR] No se logró finalizar {request_code}: {e}")
        return _respuesta(msj.msj_finalizar(request_code))

    async def _outbound(self, client, user_id, mail_id, mail, flujo, request_code):
        """Respuesta del operador: concilia la OS de cada fila (D2D por serie, ruta por ORDEN)."""
        if flujo == FLUJO_D2D and request_code is None:
            return None

        try:
            archivos = await HEINEKEN_READER.get_adjuntos(
                client=client, user_id=user_id, mail_id=mail_id,
                duck_conn=self.duckConn, flujo=flujo, vaciar_os=False,
            )
        except Exception:
            return None

        archivos = [a for a in archivos if "OS" in a.get("presentes", set())]
        if not archivos:
            return None

        tabla = HOLANDA_UTILS.unir_tablas(archivos, self.duckConn)
        filas = self.init.process.leer_respuesta(tabla, flujo)

        solicitudes, conciliadas = set(), []
        for fila in filas:
            encontrada = db_heineken.conciliar(fila, flujo, request_code)
            if encontrada:
                solicitudes.add(encontrada)
                conciliadas.append(fila)

        if not conciliadas:
            print("[HEINEKEN][outbound] Ninguna fila conciliada")
            return None

        for codigo in solicitudes:
            if db.get_email_request_status(codigo) != "CANCELLED":
                db.update_email_request(codigo)

        aceptadas = sum(f["status"] == "ACCEPTED" for f in conciliadas)
        no_encontradas = len(filas) - len(conciliadas)

        if flujo == FLUJO_D2D:
            totales = db.get_total_coolers(request_code)[0]
            if db.get_email_request_status(request_code) == "COMPLETED":
                mensaje = msj.msj_solicitud_completa_esc1(
                    request_code, mail.web_link, totales["total_coolers"],
                    totales["completed_coolers"], totales["pending_coolers"],
                )
            else:
                mensaje = msj.msj_cambios(
                    request_code, mail.web_link, len(filas), aceptadas,
                    len(conciliadas) - aceptadas, no_encontradas,
                )
        else:
            mensaje = msj.msj_cambios(
                ", ".join(sorted(solicitudes)), mail.web_link, len(filas), aceptadas,
                len(conciliadas) - aceptadas, no_encontradas,
            )

        return _respuesta(mensaje)
