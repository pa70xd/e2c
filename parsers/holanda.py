"""Parser de Holanda (Unilever) -- cliente.holanda@repare.com.mx

Diseño:
  - emails_log / email_request / cooler_request son las tablas compartidas
    de todos los clientes (vía DB_POSTGRE). Las filas de Holanda se
    distinguen por cliente; el mapeo de columnas está en
    repository/holanda/consultas_postgre.py.
  - El hilo de correo de Holanda es único y nunca se cierra, así que NO se
    resuelve la solicitud por hilo (email_reply_validate): cada correo con
    Excel genera su propio email_request, y todo lo demás se resuelve por
    CASO2 (casos) o por folio REPARE_xxxxxx (comandos del bot).
  - Llave del caso = CASO2 (TE puede no venir). Serie/Congelador
    identifican el EQUIPO y solo se usan para detectar duplicados.
  - Todo correo inbound trae solo casos nuevos; la protección contra
    reprocesos es el WHERE NOT EXISTS por CASO2 al insertar.
  - Reglas de negocio y dudas abiertas: config/customers/holanda/
    reglas_holanda.py.
"""

from parsers.holanda_parse.reader import HOLANDA_READER
from parsers.holanda_parse.business import HOLANDA_BUSINESS
from parsers.holanda_parse.sabana import HOLANDA_SABANA
from parsers.holanda_parse.process_data import HOLANDA_PROCESS
from parsers.holanda_parse.utils import HOLANDA_UTILS
from parsers.holanda_parse.catalog import HOLANDA_CATALOG
from parsers.danone_parse.reader import DANONE_READER
from infrastructure.geocoding.geocoding import GEOCODING

from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.users.item.messages.item.message_item_request_builder import MessageItemRequestBuilder

from repository.danone.consultas_postgre import DB_POSTGRE
from repository.holanda.consultas_postgre import DB_HOLANDA

from config.config_general.messages import MENSAJES_REPARE
from config.config_general.fails_response import get_fail_response as libreria_errores

from config.customers.holanda.reglas_holanda import ASUNTO_HOLANDA
from config.customers.holanda.columns_names import COL_ARCHIVO, COL_FILA_EXCEL

from src.excel_ingestion import Excel_Ingestion

import os
import re
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"

excel_ingestion = Excel_Ingestion()
msj = MENSAJES_REPARE()
db = DB_POSTGRE()
db_holanda = DB_HOLANDA()

# Folio de REPARE (p. ej. REPARE_000157), tal como lo muestra el bot.
PATRON_FOLIO = re.compile(r"REPARE_\d+", re.IGNORECASE)


def _respuesta(mensaje, attachments=None):
    return {"mensaje": mensaje, "attachments": attachments}


_PREFIJOS_RESPUESTA = re.compile(r"^\s*((re|rv|fw|fwd)\s*:\s*)+", re.IGNORECASE)
_ETIQUETAS = re.compile(r"\[[^\]]*\]")


def es_asunto_holanda(asunto: str | None) -> bool:
    """True si el asunto es el del hilo de Holanda (ASUNTO_HOLANDA),
    ignorando mayúsculas, espacios, prefijos RE:/RV:/FW: y etiquetas
    [..]. Los demás correos del buzón se ignoran sin contestar."""
    texto = _ETIQUETAS.sub(" ", asunto or "")
    texto = _PREFIJOS_RESPUESTA.sub("", texto)
    return " ".join(texto.split()).lower() == ASUNTO_HOLANDA


class HOLANDA_INIT:
    """Cualquier correo de Holanda con Excel: se lee, se valida, se
    deduplica, se enriquece, se registra y se contesta con la pre-sábana."""

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.business = HOLANDA_BUSINESS(duckConn)
        self.sabana = HOLANDA_SABANA(duckConn)
        self.process = HOLANDA_PROCESS(duckConn)
        self.geocoding = GEOCODING(duckConn)
        self.catalog = HOLANDA_CATALOG(duckConn)

    async def parse(self, client, user_id, mail_id, mail, customer=None):

        if not es_asunto_holanda(mail.subject):
            print(f"[HOLANDA][INIT][INFO] Asunto no procesado: {mail.subject!r}")
            return None

        # Graph puede notificar el mismo correo más de una vez.
        if db.email_init_exist(mail.id) and not DEBUG:
            print("[HOLANDA][INIT][ALERT] Correo omitido por existencia")
            return None

        try:
            archivos = await HOLANDA_READER.get_adjuntos(
                client=client,
                user_id=user_id,
                mail_id=mail_id,
                duck_conn=self.duckConn,
            )
        except Exception:
            return _respuesta(libreria_errores("adjuntos_02"))

        if not archivos:
            return _respuesta(libreria_errores("adjuntos_01"))

        try:
            table = HOLANDA_UTILS.unir_tablas(archivos, self.duckConn)
        except Exception:
            return _respuesta(libreria_errores("adjuntos_02"))

        try:
            missing_columns, _ = self.business.business_rules_pre_creation(table)
        except Exception:
            return _respuesta(libreria_errores("business_01"))

        if missing_columns:
            return _respuesta({"status": "ERROR", "missing_columns": missing_columns})

        self.business.marcar_duplicados_por_equipo(table)

        # Enriquecimiento para la pre-sábana: columnas *_GEN por
        # geocodificación y DISTRIBUIDORA_GEN por CP.
        self.geocoding.calcula_coordenadas(table)
        self.catalog.calcula_distribuidora(table)

        # holanda_sabana es la tabla que se registra en cooler_request;
        # sabana_ruta es la pre-sábana (único adjunto).
        self.sabana.fill_template(table)
        self.sabana.fill_sabana_ruta(table)

        email_model = self.process.fill_email_model(mail)
        request_code = db.save_email_log_init(email_model)

        db.send_email_request(self.process.prepare_data_request(request_code))
        db_holanda.insert_coolers(request_code, self.process.prepare_data_coolers())

        presabana = excel_ingestion.get_excelv2_attachment(
            self.duckConn, "sabana_ruta", request_code
        )
        if presabana is None:
            return None

        # Observación de Julio: la respuesta lleva también el mismo archivo
        # de solicitud que se recibió, con las filas rechazadas pintadas,
        # junto con la pre-sábana.
        rechazadas = self._rechazadas_por_archivo()
        originales = [
            (
                archivo["name"],
                HOLANDA_UTILS.pintar_rechazadas(
                    archivo["content"], rechazadas.get(archivo["table"], {})
                ),
            )
            for archivo in archivos
            if archivo.get("content")
        ]

        return _respuesta(
            msj.msj_send_presabana(request_code, mail.web_link),
            [*originales, presabana],
        )

    def _rechazadas_por_archivo(self) -> dict[str, dict[int, str]]:
        """{tabla del archivo: {fila de Excel: motivo}} de las filas que
        business_rules_pre_creation movió a solicitudes_rechazadas."""
        filas = self.duckConn.execute(f"""
            SELECT "{COL_ARCHIVO}", "{COL_FILA_EXCEL}", MOTIVO
            FROM solicitudes_rechazadas
        """).fetchall()

        resultado: dict[str, dict[int, str]] = {}
        for archivo, fila, motivo in filas:
            if archivo and fila:
                resultado.setdefault(archivo, {})[int(fila)] = motivo
        return resultado


class HOLANDA_REPLY:
    """Cualquier correo posterior en el hilo de Holanda:
      - inbound (cliente manda más casos) -> igual que HOLANDA_INIT.
      - outbound (REPARE contesta con las OS) -> se concilia por CASO2.
      - reply_to_bot -> comandos del bot, resueltos por folio REPARE_xxxxxx.
    """

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.init = HOLANDA_INIT(duckConn)
        self.process = self.init.process

    async def parse(self, client, user_id, mail_id, mail, direccion, customer=None, customer_email=None):

        if not es_asunto_holanda(mail.subject):
            print(f"[HOLANDA][REPLY][INFO] Asunto no procesado: {mail.subject!r}")
            return None

        result_type = await DANONE_READER.detectar_tipo_correo(
            client=client,
            user_id=user_id,
            mail_id=mail_id,
            email=mail,
        )

        if direccion == "inbound":
            # Los comandos del bot solo los usa el operador (reply_to_bot);
            # en inbound solo cuenta el Excel.
            if not result_type.get("tiene_excel"):
                return None
            return await self.init.parse(client, user_id, mail_id, mail, customer)

        if direccion == "outbound":
            return await self._outbound(client, user_id, mail_id, mail, result_type)

        if direccion == "reply_to_bot":
            return await self._comando_bot(client, user_id, mail_id, mail, result_type)

        # "bot": correo generado por el propio bot.
        return None

    async def _outbound(self, client, user_id, mail_id, mail, result_type):
        """REPARE -> cliente con las OS ya generadas: se concilia fila por
        fila por CASO2, sin importar a qué email_request pertenece cada
        caso."""

        if result_type.get("tiene_excel") and result_type.get("tiene_palabra_reservada"):
            return _respuesta("Solo puede enviar un archivo Excel o una palabra reservada.")

        if not result_type.get("tiene_excel"):
            return None

        try:
            archivos = await HOLANDA_READER.get_adjuntos(
                client=client, user_id=user_id, mail_id=mail_id,
                duck_conn=self.duckConn,
            )
        except Exception:
            return None

        if not archivos:
            return None

        table = HOLANDA_UTILS.unir_tablas(archivos, self.duckConn)
        pares_caso2_os = self.process.leer_caso2_y_os_de_respuesta(table)

        # Sin pares CASO2/OS no hay nada que conciliar ni que contestar.
        if not pares_caso2_os:
            print("[HOLANDA][outbound] Excel sin pares CASO2/OS -- nada que conciliar")
            return None

        for caso2, os_value in pares_caso2_os:
            db_holanda.update_os_by_caso2(caso2, os_value)

        print(f"[HOLANDA][outbound] {len(pares_caso2_os)} OS actualizadas por CASO2")

        # Un outbound puede cubrir casos de varios request_code: se
        # recalculan todos, excepto los cancelados (update_email_request
        # recalcula el status desde cero y los reabriría).
        request_codes = db_holanda.get_request_codes_by_caso2(
            [caso2 for caso2, _ in pares_caso2_os]
        )
        for request_code in request_codes:
            if db.get_email_request_status(request_code) != "CANCELLED":
                db.update_email_request(request_code)

        # Todas las filas conciliadas traen OS: con_os = total, sin_os = 0.
        total = len(pares_caso2_os)
        folio = ", ".join(request_codes) if request_codes else "N/A"
        return _respuesta(msj.msj_cambios(folio, mail.web_link, total, total, 0, 0))

    async def _comando_bot(self, client, user_id, mail_id, mail, result_type):
        """Mismos comandos que Danone. La diferencia: la solicitud se
        resuelve por folio (el hilo de Holanda mezcla muchas), ver
        _resolver_folio. Si no hay folio, se pide -- no se adivina."""

        if not result_type.get("tiene_palabra_reservada"):
            return None

        palabra = (result_type.get("palabra") or "").lower()

        if palabra in ("bot.help", "bot.ayuda"):
            return _respuesta(msj.msj_ayuda())

        if palabra == "bot.global":
            file = None
            try:
                data = db_holanda.global_status()
                if data:
                    file = self.process.process_email_request_global(data)
            except Exception as e:
                print(f"[HOLANDA][BOT][ERROR] No se logró generar el estado global: {e}")
            return _respuesta(msj.msj_global(), [file] if file else None)

        if palabra not in ("bot.estatus", "bot.status", "bot.cancelar", "bot.finalizar", "bot.cerrar"):
            return _respuesta(msj.msj_comando_no_reconocido())

        folio = await self._resolver_folio(client, user_id, mail_id, mail)
        if not folio:
            return _respuesta(msj.msj_folio_requerido())

        solicitud = db_holanda.get_request(folio)
        if not solicitud:
            return _respuesta(msj.msj_folio_requerido(folio))

        request_code = solicitud["request_code"]

        if palabra in ("bot.estatus", "bot.status"):
            try:
                data = db_holanda.bot_status(request_code)
            except Exception as e:
                print(f"[HOLANDA][BOT][ERROR] No se logró consultar el estatus de {request_code}: {e}")
                data = None
            if not data:
                return _respuesta(msj.msj_folio_requerido(folio))
            return _respuesta(msj.msj_status_solicitud(data))

        if palabra == "bot.cancelar":
            # También se cancelan sus casos PENDING, para que un outbound
            # posterior no reviva la solicitud.
            try:
                db.cancel_pending_coolers(request_code)
                db.cancel_email_request(request_code)
            except Exception as e:
                print(f"[HOLANDA][BOT][ERROR] No se logró cancelar {request_code}: {e}")
            return _respuesta(msj.msj_cancelar(request_code))

        # bot.finalizar / bot.cerrar
        try:
            db.complete_email_request(request_code)
        except Exception as e:
            print(f"[HOLANDA][BOT][ERROR] No se logró finalizar {request_code}: {e}")
        return _respuesta(msj.msj_finalizar(request_code))

    async def _resolver_folio(self, client, user_id, mail_id, mail):
        """Folio sobre el que actúa un comando del bot:
          1. El que el operador escribió en su texto nuevo (unique_body).
          2. Si no, el primero del cuerpo COMPLETO: el correo del bot que
             está contestando (service.py solo pide uniqueBody, por eso
             aquí se pide `body` aparte).
          3. Si no hay, None."""

        texto_nuevo = getattr(getattr(mail, "unique_body", None), "content", "") or ""
        encontrado = PATRON_FOLIO.search(texto_nuevo)
        if encontrado:
            return encontrado.group(0).upper()

        try:
            query_params = MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(
                select=["body"],
            )
            config = RequestConfiguration(query_parameters=query_params)
            config.headers.add("Prefer", 'outlook.body-content-type="text"')

            mensaje = await (
                client.users
                .by_user_id(user_id)
                .messages
                .by_message_id(mail_id)
                .get(request_configuration=config)
            )
            cuerpo = getattr(getattr(mensaje, "body", None), "content", "") or ""
        except Exception as e:
            print(f"[HOLANDA][BOT][ERROR] No se pudo leer el cuerpo completo del correo: {e}")
            return None

        encontrado = PATRON_FOLIO.search(cuerpo)
        return encontrado.group(0).upper() if encontrado else None
