"""Parsers de Oxxo -- cliente.oxxo@ (mantenimiento) y cliente.oxogar@ (garantías).

APAGADOS POR DEFECTO. Oxxo ya tiene una PoC automatizada FUERA de este repo
que procesa los mismos buzones. Si las dos corren a la vez, cada ticket o
folio genera dos OS. Estos parsers solo actúan si "oxxo" (mantenimiento) u
"oxxo_garantias" (garantías) están en E2C_CLIENTES_HABILITADOS; sin eso
devuelven None sin tocar la base ni contestar. El dedupe por ticket/folio
protege de reprocesos propios, NO de la PoC externa: no se enciende un buzón
mientras la PoC siga leyéndolo (o hasta apagarla), y el corte lo decide
REPARE.

Diseño:
  - Sin LLM: regex por campo etiquetado (parsers/oxxo_parse/plantillas.py).
    Tolera acentos, mayúsculas, espacios y líneas extra. Si falta el ticket
    o el folio, el correo va a revisión (aviso a REPARE); no se inventa.
  - emails_log / email_request las escribe DB_POSTGRE (repository.core);
    las filas de cooler_request y las consultas por folio, DB_OXXO.
  - Dedupe por ticket (mantenimiento) o folio (garantías): el mismo
    folio no crea dos solicitudes, ni entre los dos buzones.
  - PII (nombre, teléfono, dirección) solo va en los campos del modelo de
    datos que ya la prevén; nunca se imprime.

Plantillas:
  1. Mantenimiento: "Abierto-Asignado ----> <ticket de 8 dígitos>". OS nueva
     de ruta: folio = ticket, sin serie.
  2. Garantías: "Seguimiento a Folio: <folio>". Es una ESCALACIÓN. Si el
     folio ya tiene solicitud, se marca la escalación en la fila y se avisa
     "requiere revisión" a REPARE por el canal de review/. Si no existe, se
     registra como OS nueva de garantía y la respuesta lo avisa.
  3. Garantías con Excel (.xlsx/.xlsm, Lay Out Repare):
     "Solicitud de Orden de Servicio Oxxo <tienda>" y
     "RE: Solicitud de generación de OS para cliente <X> - OXO". Si el cuerpo
     dice "N OS", el Excel debe traer N filas o el correo va a revisión.
     Se lee con el lector común (parsers/core/lector.py, vía
     parsers/oxxo_parse/excel.py).

Las OS entran sin CP, coordenadas ni distribuidora (la plantilla no los
trae) y sin pre-sábana: ese enriquecimiento queda pendiente.
"""

from __future__ import annotations

import base64
import os
import re

from dotenv import load_dotenv
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.users.item.messages.item.message_item_request_builder import MessageItemRequestBuilder

import review
from bot import commands as bot_commands
from bot.perfiles import perfil_oxxo
from classifier.contracts import (
    MODIFICAR_FILAS,
    ETAPA_INIT,
    Decision,
    FilaRevision,
    GateResult,
    ThreadCtx,
)
from config.config_general.messages import MENSAJES_REPARE
from config.customers.oxxo.mensajes import MENSAJES_OXXO
from config.customers.oxxo.reglas_oxxo import (
    CUSTOMER_GARANTIAS,
    CUSTOMER_MANTENIMIENTO,
    MOTIVO_CONTEO_OS,
    MOTIVO_ESCALACION,
    MOTIVO_EXCEL_ILEGIBLE,
    MOTIVO_SIN_EXCEL,
)
from parsers.core.correo import detectar_tipo_correo
from parsers.oxxo_parse import excel as lector_excel
from parsers.oxxo_parse.habilitado import habilitado
from parsers.oxxo_parse.plantillas import (
    contar_os_solicitadas,
    es_asunto_excel_garantias,
    es_asunto_seguimiento,
    parse_mantenimiento,
    parse_seguimiento,
)
from parsers.oxxo_parse.process_data import OXXO_PROCESS
from repository.danone.consultas_postgre import DB_POSTGRE
from repository.oxxo.consultas_postgre import DB_OXXO

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"

msj = MENSAJES_REPARE()
msj_oxxo = MENSAJES_OXXO()
db = DB_POSTGRE()
db_oxxo = DB_OXXO()

# Folio de REPARE (p. ej. REPARE_000157), tal como lo muestra el bot.
PATRON_FOLIO = re.compile(r"REPARE_\d+", re.IGNORECASE)

ACCION_ALTA = "alta"
ACCION_ESCALACION = "escalacion"


def _respuesta(mensaje, attachments=None):
    return {"mensaje": mensaje, "attachments": attachments}


def _cuerpo(mail) -> str:
    return getattr(getattr(mail, "unique_body", None), "content", "") or ""


def _aviso_sin_solicitud(motivo: str, request_code: str | None = None) -> dict:
    """Aviso 'requiere revisión' de un correo que no se pudo convertir en
    OS (campo clave faltante, Excel que no cuadra). No se guarda nada."""
    fila = {"row_number": None, "serie": None, "accion": ACCION_ALTA, "motivo": motivo}
    return _respuesta(msj.msj_revision_repare(request_code or "N/A", [fila]))


class _Buzon:
    """Lo que comparten los cuatro parsers: gate de encendido, dedupe y
    registro. El correo del cliente entra igual en INIT que en un REPLY
    inbound (Oxxo manda varios correos de sistema en el mismo hilo)."""

    CUSTOMER: str = ""

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self.process = OXXO_PROCESS(duckConn)

    # ---- entrada -------------------------------------------------------
    async def _procesar(self, client, user_id, mail_id, mail, *, es_reply: bool):
        if not habilitado(self.CUSTOMER):
            print(f"[OXXO][{self.CUSTOMER}][INFO] Parser apagado (E2C_CLIENTES_HABILITADOS)")
            return None

        # Graph puede notificar el mismo correo más de una vez.
        if db.email_init_exist(mail.id) and not DEBUG:
            print(f"[OXXO][{self.CUSTOMER}][ALERT] Correo omitido por existencia")
            return None

        return await self._plantilla(client, user_id, mail_id, mail, es_reply=es_reply)

    async def _plantilla(self, client, user_id, mail_id, mail, *, es_reply: bool):
        raise NotImplementedError

    # ---- registro ------------------------------------------------------
    def _registrar(self, mail, filas: list[dict]) -> tuple[str, int]:
        """emails_log + email_request + una fila de cooler_request por OS.
        Regresa (request_code, filas insertadas)."""
        request_code = db.save_email_log_init(self.process.fill_email_model(mail, self.CUSTOMER))
        db.send_email_request(self.process.prepare_data_request(request_code, self.CUSTOMER, len(filas)))
        insertadas = sum(
            1 for n, fila in enumerate(filas, start=1) if db_oxxo.insert_fila(request_code, n, fila)
        )
        if insertadas != len(filas):
            # Folios repetidos dentro del lote o ganados por otro proceso.
            db.update_email_request(request_code)
        return request_code, insertadas


# --------------------------------------------------------------- mantenimiento

class _MantenimientoBase(_Buzon):
    CUSTOMER = CUSTOMER_MANTENIMIENTO

    async def _plantilla(self, client, user_id, mail_id, mail, *, es_reply: bool):
        datos = parse_mantenimiento(mail.subject, _cuerpo(mail))
        if datos is None:
            print("[OXXO][oxxo][INFO] Correo fuera de la plantilla de mantenimiento")
            return None

        if datos.ticket is None:
            print(f"[OXXO][oxxo][ALERT] A revisión: {datos.motivo_revision}")
            return _aviso_sin_solicitud(datos.motivo_revision)

        if db_oxxo.get_by_folio(datos.ticket):
            print("[OXXO][oxxo][ALERT] Ticket ya registrado; no se duplica")
            return None

        request_code, insertadas = self._registrar(mail, [self.process.fila_mantenimiento(datos)])
        if not insertadas:
            print("[OXXO][oxxo][ALERT] Ticket ganado por otro proceso; no se duplica")
            return None

        return _respuesta(msj_oxxo.msj_os_registrada(request_code, "TICKET", datos.ticket, mail.web_link))


class OXXO_INIT(_MantenimientoBase):
    """Correo nuevo del buzón de mantenimiento."""

    async def parse(self, client, user_id, mail_id, mail, customer=None):
        return await self._procesar(client, user_id, mail_id, mail, es_reply=False)


# --------------------------------------------------------------- garantías

class _GarantiasBase(_Buzon):
    CUSTOMER = CUSTOMER_GARANTIAS

    async def _plantilla(self, client, user_id, mail_id, mail, *, es_reply: bool):
        if es_asunto_seguimiento(mail.subject):
            return await self._seguimiento(mail)
        if es_asunto_excel_garantias(mail.subject):
            return await self._excel(client, user_id, mail_id, mail, es_reply=es_reply)
        print("[OXXO][oxxo_garantias][INFO] Correo fuera de las plantillas de garantías")
        return None

    # ---- Seguimiento a Folio ------------------------------------------
    async def _seguimiento(self, mail):
        datos = parse_seguimiento(mail.subject, _cuerpo(mail))
        if datos.folio is None:
            print(f"[OXXO][oxxo_garantias][ALERT] A revisión: {datos.motivo_revision}")
            return _aviso_sin_solicitud(datos.motivo_revision)

        existente = db_oxxo.get_by_folio(datos.folio)
        if existente:
            return await self._escalar(mail, existente, datos)

        request_code, insertadas = self._registrar(mail, [self.process.fila_garantia(datos)])
        if not insertadas:
            print("[OXXO][oxxo_garantias][ALERT] Folio ganado por otro proceso; no se duplica")
            return None
        return _respuesta(msj_oxxo.msj_os_registrada(
            request_code, "FOLIO", datos.folio, mail.web_link,
            aviso="El folio no tenía solicitud en la base; se registró como OS nueva de garantía.",
        ))

    async def _escalar(self, mail, existente, datos):
        """Folio ya registrado: se marca la escalación en su fila y se manda
        'requiere revisión' a REPARE con el canal de review/ (nada se aplica)."""
        request_code, row_number = existente["request_code"], existente["row_number"]

        recibido = getattr(mail, "received_date_time", None)
        fecha = f" {recibido:%Y-%m-%d}" if recibido else ""
        nota = f"ESCALACION{fecha}: {datos.mensaje or 'sin mensaje'}"
        try:
            db_oxxo.marcar_escalacion(request_code, row_number, nota)
        except Exception as e:
            print(f"[OXXO][oxxo_garantias][ERROR] Escalación no marcada: {type(e).__name__}")

        decision = Decision(
            gate=GateResult(True, MODIFICAR_FILAS, 1.0, "oxxo_escalacion"),
            proveedor_gate="oxxo",
            proveedor_extract="oxxo",
            filas_revision=(FilaRevision(
                row_number=row_number,
                accion=ACCION_ESCALACION,
                status=existente.get("status") or "PENDING",
                motivo=MOTIVO_ESCALACION,
            ),),
        )
        ctx = ThreadCtx(
            etapa=ETAPA_INIT,
            customer=self.CUSTOMER,
            direccion="inbound",
            request_code=request_code,
            filas=(),
        )

        avisos: list[str] = []

        async def enviar(mensaje):
            avisos.append(mensaje)

        await review.atender(decision, ctx, db, enviar)
        if avisos:
            return _respuesta(avisos[0])
        fila = {"row_number": row_number, "serie": None, "accion": ACCION_ESCALACION, "motivo": MOTIVO_ESCALACION}
        return _respuesta(msj.msj_revision_repare(request_code, [fila]))

    # ---- Excel (Lay Out Repare) ---------------------------------------
    async def _adjuntos_excel(self, client, user_id, mail_id) -> list[tuple[str, bytes]]:
        respuesta = await (
            client.users.by_user_id(user_id).messages.by_message_id(mail_id).attachments.get()
        )
        contenidos = []
        for adjunto in respuesta.value or []:
            nombre = getattr(adjunto, "name", "") or ""
            contenido = getattr(adjunto, "content_bytes", None)
            if nombre.startswith("~$") or not contenido or not lector_excel.es_excel(nombre):
                continue
            if contenido.startswith(b"UEs"):  # Base64 de un zip
                contenido = base64.b64decode(contenido)
            contenidos.append((nombre, contenido))
        return contenidos

    async def _excel(self, client, user_id, mail_id, mail, *, es_reply: bool):
        try:
            contenidos = await self._adjuntos_excel(client, user_id, mail_id)
        except Exception as e:
            print(f"[OXXO][oxxo_garantias][ERROR] Adjuntos no leídos: {type(e).__name__}")
            return _aviso_sin_solicitud(MOTIVO_EXCEL_ILEGIBLE)

        if not contenidos:
            # Un RE: sin Excel es conversación, no solicitud.
            return None if es_reply else _aviso_sin_solicitud(MOTIVO_SIN_EXCEL)

        filas_excel = []
        try:
            for nombre, contenido in contenidos:
                filas_excel.extend(lector_excel.leer_filas(nombre, contenido))
        except lector_excel.ExcelIlegible as e:
            print(f"[OXXO][oxxo_garantias][ALERT] Excel ilegible: {e}")
            return _aviso_sin_solicitud(MOTIVO_EXCEL_ILEGIBLE)
        if not filas_excel:
            return _aviso_sin_solicitud(MOTIVO_EXCEL_ILEGIBLE)

        esperadas = contar_os_solicitadas(_cuerpo(mail))
        if esperadas is not None and esperadas != len(filas_excel):
            print(f"[OXXO][oxxo_garantias][ALERT] Conteo de OS distinto: correo={esperadas} excel={len(filas_excel)}")
            return _aviso_sin_solicitud(f"{MOTIVO_CONTEO_OS} (correo {esperadas}, Excel {len(filas_excel)})")

        request_code, insertadas = self._registrar(mail, [self.process.fila_excel(f) for f in filas_excel])
        if not insertadas:
            print("[OXXO][oxxo_garantias][ALERT] Folios ya registrados; no se duplica")
            return None
        return _respuesta(msj_oxxo.msj_excel_registrado(request_code, insertadas, mail.web_link))


class OXXO_GARANTIAS_INIT(_GarantiasBase):
    """Correo nuevo del buzón de garantías."""

    async def parse(self, client, user_id, mail_id, mail, customer=None):
        return await self._procesar(client, user_id, mail_id, mail, es_reply=False)


# --------------------------------------------------------------- hilos

class _ReplyMixin:
    """Correos posteriores del hilo. inbound -> igual que INIT; reply_to_bot
    -> comandos del bot por folio REPARE_xxxxxx; outbound y bot -> nada."""

    async def parse(self, client, user_id, mail_id, mail, direccion, customer=None, customer_email=None):
        if not habilitado(self.CUSTOMER):
            print(f"[OXXO][{self.CUSTOMER}][INFO] Parser apagado (E2C_CLIENTES_HABILITADOS)")
            return None

        if direccion == "inbound":
            return await self._procesar(client, user_id, mail_id, mail, es_reply=True)

        if direccion == "reply_to_bot":
            return await self._comando_bot(client, user_id, mail_id, mail)

        return None

    async def _comando_bot(self, client, user_id, mail_id, mail):
        result_type = await detectar_tipo_correo(client=client, user_id=user_id, mail_id=mail_id, email=mail)
        return await bot_commands.ejecutar(
            perfil_oxxo(db, db_oxxo, msj, self.process, self.CUSTOMER),
            result_type,
            bot_commands.resolver_por_folio(
                lambda: self._resolver_folio(client, user_id, mail_id, mail),
                lambda folio: db_oxxo.get_request(folio, self.CUSTOMER),
                msj,
            ),
        )

    async def _resolver_folio(self, client, user_id, mail_id, mail):
        """Folio sobre el que actúa un comando del bot: el del texto nuevo
        del operador o, si no, el primero del cuerpo completo (el correo del
        bot al que contesta). None si no hay."""
        encontrado = PATRON_FOLIO.search(_cuerpo(mail))
        if encontrado:
            return encontrado.group(0).upper()

        try:
            query_params = MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(select=["body"])
            config = RequestConfiguration(query_parameters=query_params)
            config.headers.add("Prefer", 'outlook.body-content-type="text"')
            mensaje = await (
                client.users.by_user_id(user_id).messages.by_message_id(mail_id)
                .get(request_configuration=config)
            )
            cuerpo = getattr(getattr(mensaje, "body", None), "content", "") or ""
        except Exception as e:
            print(f"[OXXO][BOT][ERROR] No se pudo leer el cuerpo completo del correo: {type(e).__name__}")
            return None

        encontrado = PATRON_FOLIO.search(cuerpo)
        return encontrado.group(0).upper() if encontrado else None


class OXXO_REPLY(_ReplyMixin, _MantenimientoBase):
    pass


class OXXO_GARANTIAS_REPLY(_ReplyMixin, _GarantiasBase):
    pass
