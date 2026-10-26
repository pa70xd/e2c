"""Flujo común de Imbera y Torrey ("Lay Out Repare"). parsers/imbera.py y
parsers/torrey.py solo eligen su PerfilLayout.

INIT: correo nuevo con el layout -> se lee (hojas ocultas solo si traen el
encabezado de datos), se clasifica por contenido (sub-cliente, folio
IMB-/REP-, garantía), se aplican las reglas, se registra y se contesta con
las aceptadas, las rechazadas y la pre-sábana.

REPLY (la solicitud se resuelve por hilo, como Danone):
  * inbound: el cliente reenvía el layout -> mismas reglas, insert_update.
  * outbound: REPARE contesta con la OS en Excel (por serie) o en TEXTO
    ("Comparto orden generada: <n>"). Un estatus sin OS ("espera de
    pieza") es no_os: no se concilia ni se contesta.
  * reply_to_bot: comandos bot.* (bot/commands.py).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from bot import commands as bot_commands
from config.config_general.messages import MENSAJES_REPARE
from parsers.core.correo import detectar_tipo_correo
from parsers.core.tablas import unir_tablas
from parsers.imbera_parse import reader
from parsers.imbera_parse.business import aplicar_reglas
from parsers.imbera_parse.clasificacion import clasificar
from parsers.imbera_parse.conciliacion import conciliar_texto, es_estatus_sin_os
from parsers.imbera_parse.mensajes import msj_solicitud_layout
from parsers.imbera_parse.perfil import PerfilLayout
from parsers.imbera_parse.process_data import LAYOUT_PROCESS
from parsers.imbera_parse.sabana import LAYOUT_SABANA
from repository.imbera.consultas_postgre import DB_POSTGRE as DB_IMBERA
from src.excel_ingestion import Excel_Ingestion

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"

excel_ingestion = Excel_Ingestion()
msj = MENSAJES_REPARE()
db = DB_IMBERA()


def _respuesta(mensaje, attachments=None):
    return {"mensaje": mensaje, "attachments": attachments}


def _texto(mail) -> str:
    return getattr(getattr(mail, "unique_body", None), "content", "") or ""


def _buzones(mail) -> list[str]:
    direcciones = []
    for r in [getattr(mail, "sender", None), *(mail.to_recipients or []), *(mail.cc_recipients or [])]:
        address = getattr(getattr(r, "email_address", None), "address", None)
        if address:
            direcciones.append(address.lower())
    return direcciones


class LAYOUT_INIT:

    perfil: PerfilLayout  # lo fija la subclase de cada cliente

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.process = LAYOUT_PROCESS(duckConn, self.perfil)
        self.sabana = LAYOUT_SABANA(duckConn)

    def _log(self, nivel, texto):
        print(f"[{self.perfil.etiqueta}][{nivel}] {texto}")

    async def leer(self, client, user_id, mail_id, mail):
        """(adjuntos, clasificación, tabla unida o None)."""
        adjuntos = await reader.get_adjuntos(client, user_id, mail_id, self.duckConn)
        nombres = adjuntos.otros + [t["name"] for t in adjuntos.tablas] + adjuntos.excel_sin_layout
        clasificacion = clasificar(mail.subject, _texto(mail), nombres, _buzones(mail))
        tabla = unir_tablas(adjuntos.tablas, self.duckConn) if adjuntos.tablas else None
        return adjuntos, clasificacion, tabla

    def preparar(self, tabla, clasificacion) -> list:
        """Reglas y pre-sábanas. Regresa los adjuntos de la respuesta."""
        aplicar_reglas(self.duckConn, tabla, clasificacion, self.perfil)
        self.sabana.fill_sabana_ruta()
        self.sabana.fill_sabana_movimiento()
        attachments = [
            excel_ingestion.get_excelv2_attachment(self.duckConn, "sabana_ruta"),
            excel_ingestion.get_excelv2_attachment(self.duckConn, "sabana_movimiento"),
        ]
        return [a for a in attachments if a is not None]

    def avisos(self, adjuntos, clasificacion, aceptadas) -> list[str]:
        avisos = []
        if self.perfil.exige_factura_pdf and "factura_pdf" not in clasificacion.senales_garantia:
            avisos.append("No se encontró la factura en PDF (formato obligatorio: Lay Out Repare con factura).")
        for nombre in adjuntos.excel_sin_layout:
            avisos.append(f"El archivo {nombre} no tiene el formato Lay Out Repare y no se procesó.")
        otros = [f for f in aceptadas if f["cliente"] and f["cliente"] != self.perfil.cliente_os]
        if otros:
            avisos.append(
                f"{len(otros)} equipo(s) se generan para el cliente {otros[0]['cliente']} "
                "y se contestan en este hilo."
            )
        return avisos

    async def parse(self, client, user_id, mail_id, mail, customer=None):

        if db.email_init_exist(mail.id) and not DEBUG:
            self._log("ALERT", "Correo omitido por existencia")
            return None

        try:
            adjuntos, clasificacion, tabla = await self.leer(client, user_id, mail_id, mail)
        except Exception as e:
            self._log("ERROR", f"No se pudieron leer los adjuntos: {type(e).__name__}")
            return None

        if tabla is None:
            if adjuntos.excel_sin_layout:
                return _respuesta(msj.formato_desconocido())
            # Seguimiento, consulta de estatus, queja o correo sin layout:
            # no se da de alta nada.
            self._log("INFO", f"Sin layout; tipo={clasificacion.tipo}")
            return None

        if self.duckConn.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0] < 1:
            return _respuesta(msj.formato_desconocido())

        attachments = self.preparar(tabla, clasificacion)

        request_code = db.save_email_log_init(self.process.fill_email_model(mail))
        db.send_email_request(self.process.prepare_data_request(request_code))
        for cooler in self.process.prepare_data_coolers(request_code):
            db.send_email_coolers(cooler)

        aceptadas, rechazadas = self.process.resumen()
        self._log(
            "INFO",
            f"{request_code}: tipo={clasificacion.tipo} variante={clasificacion.variante_ruta} "
            f"garantia={clasificacion.garantia} aceptadas={len(aceptadas)} rechazadas={len(rechazadas)}",
        )
        return _respuesta(
            msj_solicitud_layout(
                request_code, aceptadas, rechazadas,
                self.avisos(adjuntos, clasificacion, aceptadas),
            ),
            attachments,
        )


class LAYOUT_REPLY:

    init_cls: type[LAYOUT_INIT]  # lo fija la subclase de cada cliente
    perfil_bot = None  # callable(db, msj, process) -> PerfilBot

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.init = self.init_cls(duckConn)
        self.perfil = self.init.perfil
        self.process = self.init.process

    def _log(self, nivel, texto):
        print(f"[{self.perfil.etiqueta}][REPLY][{nivel}] {texto}")

    async def parse(self, client, user_id, mail_id, mail, direccion, customer=None, customer_email=None):

        reply = db.email_reply_validate(conversation_id=mail.conversation_id, subject=mail.subject)
        if reply is None:
            return None
        request_code = reply["request_code"]

        result_type = await detectar_tipo_correo(client=client, user_id=user_id, mail_id=mail_id, email=mail)

        if direccion == "inbound":
            if not result_type.get("tiene_excel"):
                return None
            return await self._inbound(client, user_id, mail_id, mail, request_code)

        if direccion == "outbound":
            if result_type.get("tiene_excel") and result_type.get("tiene_palabra_reservada"):
                return None
            return await self._outbound(client, user_id, mail_id, mail, request_code, result_type)

        if direccion == "reply_to_bot":
            return await bot_commands.ejecutar(
                type(self).perfil_bot(db, msj, self.process),
                result_type,
                bot_commands.solicitud_fija(request_code),
            )

        # "bot": correo generado por el propio bot.
        return None

    async def _inbound(self, client, user_id, mail_id, mail, request_code):
        try:
            adjuntos, clasificacion, tabla = await self.init.leer(client, user_id, mail_id, mail)
        except Exception as e:
            self._log("ERROR", f"No se pudieron leer los adjuntos: {type(e).__name__}")
            return None

        if tabla is None or self.duckConn.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0] < 1:
            return _respuesta(msj.formato_desconocido())

        attachments = self.init.preparar(tabla, clasificacion)
        for cooler in self._renumerar(request_code, self.process.prepare_data_coolers(request_code)):
            db.insert_update_cooler(cooler)
        db.update_email_request(request_code)

        aceptadas, rechazadas = self.process.resumen()
        return _respuesta(
            msj_solicitud_layout(
                request_code, aceptadas, rechazadas,
                self.init.avisos(adjuntos, clasificacion, aceptadas),
                actualizacion=True,
            ),
            attachments,
        )

    @staticmethod
    def _renumerar(request_code, coolers):
        """El reenvío del cliente puede traer solo algunas filas: una serie
        ya registrada conserva su row_number (insert_update_cooler la
        actualiza si sigue PENDING; si no, no la toca y la loguea para
        revisión) y una serie nueva va al final, sin pisar otra fila."""
        existentes = db.get_cooler_rows(request_code)
        por_serie = {
            serie: f["row_number"]
            for f in existentes
            for serie in (f.get("serie_fabricante"), f.get("serie_dnn_bnf"))
            if serie
        }
        siguiente = max((f["row_number"] for f in existentes), default=0)
        for cooler in coolers:
            serie = cooler.get("serie_fabricante")
            if serie in por_serie:
                cooler["row_number"] = por_serie[serie]
            else:
                siguiente += 1
                cooler["row_number"] = siguiente
        return coolers

    async def _outbound(self, client, user_id, mail_id, mail, request_code, result_type):
        actualizadas = 0

        if result_type.get("tiene_excel"):
            try:
                adjuntos = await reader.get_adjuntos(client, user_id, mail_id, self.duckConn)
            except Exception as e:
                self._log("ERROR", f"No se pudieron leer los adjuntos: {type(e).__name__}")
                return None
            if adjuntos.tablas:
                tabla = unir_tablas(adjuntos.tablas, self.duckConn)
                for serie, os_value in self.process.leer_series_y_os(tabla):
                    actualizadas += db.update_os_por_serie(request_code, serie, os_value) or 0

        if not actualizadas and self.perfil.conciliar_texto:
            texto = _texto(mail)
            if es_estatus_sin_os(texto):
                self._log("INFO", f"{request_code}: estatus sin OS (no_os)")
                return None
            resultado = conciliar_texto(texto, db.get_cooler_rows(request_code))
            if resultado.tipo == "ambiguo":
                self._log(
                    "REVISION",
                    f"{request_code}: {len(resultado.os_encontradas)} OS en el texto sin fila "
                    "asignable; requiere revisión",
                )
                return None
            for row_number, os_value in resultado.asignaciones:
                actualizadas += db.update_os_por_fila(request_code, row_number, os_value) or 0

        if not actualizadas:
            return None

        if db.get_email_request_status(request_code) == "CANCELLED":
            # update_email_request recalcula el status y la reabriría.
            return None
        db.update_email_request(request_code)
        status = db.get_email_request_status(request_code)
        totales = db.get_total_coolers(request_code)[0]

        if status == "COMPLETED":
            return _respuesta(msj.msj_solicitud_completa_esc1(
                request_code,
                url=mail.web_link,
                total=totales["total_coolers"],
                con_os=totales["completed_coolers"],
                sin_os=totales["pending_coolers"],
            ))
        return _respuesta(msj.msj_cambios(
            request_code,
            url=mail.web_link,
            total=totales["total_coolers"],
            con_os=totales["completed_coolers"],
            sin_os=totales["pending_coolers"],
            desconocidos=totales["failed_coolers"],
        ))
