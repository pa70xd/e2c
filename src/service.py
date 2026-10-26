
import json

from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from msgraph.generated.users.item.messages.item.message_item_request_builder import MessageItemRequestBuilder

from infrastructure.graphapi.graphapi import getClient, sendMail
from parsers.danone import DANONE_INIT,DANONE_REPLY
from parsers.holanda import HOLANDA_INIT,HOLANDA_REPLY
from repository.danone.consultas_postgre import DB_POSTGRE

from parsers.danone import DANONE_INIT,DANONE_REPLY
from parsers.penafiel import PENAFIEL_INIT, PENAFIEL_REPLY

from parsers.heineken import HEINEKEN_INIT, HEINEKEN_REPLY   # imports
from parsers.kof import KOF_INIT, KOF_REPLY

import re

from pathlib import Path
from fastapi import HTTPException

from infrastructure.database.engine_duck import DuckEngine
from src.excel_ingestion import Excel_Ingestion
from src.email_type import EMAIL_TYPE, with_test_mailbox
from infrastructure.graphapi.graphapi import reply_mail_onl_text, reply_mail_init_files
from parsers.gen_parse.reader import GEN_READER
import classifier
from classifier.contracts import ETAPA_INIT, ETAPA_REPLY
import review

from datetime import datetime
from zoneinfo import ZoneInfo

import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"
flujo = '[INIT]'


async def reply_with_attachments(
    host_email,
    client,
    user_id,
    mail_id,
    mensaje,
    attachments,
    temporary_files=None,
):
    temporary_files = temporary_files or []

    try:
        attachments = list(attachments or [])
        attachments.extend(
            (filename, Path(path).read_bytes())
            for filename, path in temporary_files
        )
        await reply_mail_init_files(
            host_email=host_email,
            client=client,
            user_id=user_id,
            mail_id=mail_id,
            mensaje=mensaje,
            attachments=attachments,
        )
    finally:
        GEN_READER.cleanup_original_files(temporary_files)

with open("config/email_index.json", "r", encoding="utf-8") as f:
    CUSTOMER_INDEX = with_test_mailbox(json.load(f))



PARSERS_INIT = {

    "danone"    : DANONE_INIT,
    "penafiel"   : PENAFIEL_INIT,
    "holanda"   : HOLANDA_INIT,
    "heineken" : HEINEKEN_INIT,
    "kof"       : KOF_INIT,

    #tests
    "test_danone"    : DANONE_INIT,
    "test_penafiel"   : PENAFIEL_INIT,
    "test_holanda"   : HOLANDA_INIT,
    "test_heineken" : HEINEKEN_INIT,
    "test_kof"      : KOF_INIT,
}
PARSERS_REPLY = {

    "danone"    : DANONE_REPLY,
    "penafiel"   : PENAFIEL_REPLY,
    "holanda"   : HOLANDA_REPLY,
    "heineken": HEINEKEN_REPLY,
    "kof"     : KOF_REPLY,

    #tests
    "test_danone" : DANONE_REPLY,
    "test_penafiel" : PENAFIEL_REPLY,
    "test_holanda"   : HOLANDA_REPLY,
    "test_heineken": HEINEKEN_REPLY,
    "test_kof"     : KOF_REPLY,
}

# Clientes cuyo parser INIT ya pasa por el gate del clasificador en
# analizar_proposito. Los demás pasan por el gate aquí.
GATE_EN_PARSER_INIT = {"danone", "penafiel", "test_danone", "test_penafiel"}


def classifier_evaluar(email, customer, etapa, direccion=None):
    """Gate del clasificador: ``(continuar, decision, ctx)``. Con el proveedor
    por defecto (regex) siempre deja pasar lo que antes pasaba. Si el
    clasificador falla, el flujo sigue como antes (sin decisión). El reply
    usa ``ctx`` (filas del hilo) para el canal de revisión."""
    try:
        decision, ctx = classifier.decidir_correo(email, customer, etapa, direccion)
    except Exception as e:
        print(f"[CLASSIFIER][ERROR] {type(e).__name__}; se sigue sin gate")
        return True, None, None
    if classifier.debe_continuar(decision, ctx):
        return True, decision, ctx
    print(f"[CLASSIFIER][INFO] {etapa} descartado: tipo={decision.tipo_evento}")
    return False, decision, ctx


def classifier_gate(email, customer, etapa, direccion=None):
    """Gate del clasificador: (continuar, Decision o None)."""
    return classifier_evaluar(email, customer, etapa, direccion)[:2]


# SABANA = Template_Sabana()
excel_ingestion = Excel_Ingestion()
validator = EMAIL_TYPE()
db = DB_POSTGRE()

# Contexto del hilo (filas de cooler_request) para el clasificador. Solo se
# consulta con un proveedor externo; con regex no se llama.
classifier.registrar_cargador_contexto(review.cargador(db))

async def processMail(data):
    
    duckConn = DuckEngine.get()
    # result_parse = False
    client = getClient()

    if client is None:
        raise HTTPException(
            status_code=500,
            detail="No se pudo conectar con Microsoft Graph."
        )

    user_id = str(data["resourceData"]["@odata.id"]).split("/")[1]
    mail_id = data["resourceData"]["id"]

    query_params = MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(
        select=[
            "subject",
            "uniqueBody",
            "toRecipients",
            "replyTo",
            "receivedDateTime",
            "webLink",
            "conversationId",
            "sender",
            "internetMessageId",
            "hasAttachments",
            "from",
            "isDraft",
            "isRead",
            "parentFolderId",
            "lastModifiedDateTime",
            "changeKey",
            "ccRecipients",
            "categories"
    ],
    )
    request_config = RequestConfiguration(query_parameters=query_params)
    request_config.headers.add("Prefer", 'outlook.body-content-type="text"')

    try:
        email = await (
            client.users
            .by_user_id(user_id)
            .messages
            .by_message_id(mail_id)
            .get(request_configuration=request_config)
            # .get()
        )

        if DEBUG:
            with open("email.json", "w", encoding="utf-8") as f:
                json.dump(email.__dict__, f, indent=4, ensure_ascii=False, default=str)
        
    except Exception as e:
        print(f"[ERROR] Microsoft Graph - {str(e)}")
        return None

    # validacionde correo prueba

    valid_list = validator.validate_email(email)

    if  not DEBUG:
        print(f"{email.subject} --- {email.from_.email_address} --- {data}")
        print("\n")
        print(json.dumps(data, indent = 1, ensure_ascii=False))
        print("\n")

    allowed_email = valid_list[0]
    type_email = valid_list[1]

    if allowed_email:
        print("Correo válido:", allowed_email)

        try : 
            customer = validator.detect_customer(email)
            print("primer intento de deteccion de cliente:", customer)

            if customer == None:
                return None

            if customer == 'test':
                customer = resolve_test_customer(email.subject)
                print("segundo intento de deteccion de cliente:", customer)

                if customer is None:
                    # print(
                    #     "[Error] El asunto de prueba debe indicar el cliente "
                    #     "entre corchetes, por ejemplo: [danone]"
                    # )
                    return None

                try:
                    customer_email = get_customer_email('test')
                    if customer_email == None:
                        return None
                    
                except Exception as e:
                    print(f"[Error] Cliente no permitido: {e}")
                    return None
            else:
                try:
                    customer_email = get_customer_email(customer)
                    if customer_email == None:
                        return None
                    
                except Exception as e:
                    print(f"[Error] Cliente no permitido: {e}")
                    return None

        except Exception as e:
            print(f"[Error] Cliente no permitido: {e}") 
            return None


        
        print(f"[CUSTOMER] {customer} - {customer_email}")

        # Solo el primer mensaje de una conversación puede iniciar una
        # solicitud. Un correo posterior, aunque no tenga el prefijo "Re:",
        # actualiza el folio ya asociado al hilo.

        if type_email != "reply" and db.conversation_exists(email.conversation_id) and not DEBUG:
            # print(
            #     "[INIT][INFO] Conversación existente;")
            type_email = "reply"


        if type_email == 'reply':

            flujo = '[REPLY]'

            if (validator.is_duplicate_email(email)) and (not DEBUG):
                # print("[INFO] Segunda notificación detectada. Se ignora.")
                duckConn.close()
                return "EMAIL_DUPLICADO"
              
            
            detected = validator.detect_direccion(email)
            if detected is None:
                print(
                    "[Error] No se pudo determinar la dirección del correo "
                    "(remitente/destinatarios fuera de los buzones configurados)."
                )
                duckConn.close()
                return None
            customer, direccion = detected
            if customer == "test":
                customer = resolve_test_customer(email.subject)
                if customer is None:
                    print(
                        "[Error] El asunto de prueba debe indicar el cliente "
                        "entre corchetes, por ejemplo: [danone]"
                    )
                    return None

            # print(f"{flujo}CUSTOMER: {customer}")
            # print(f"{flujo}DIRECCIO: {direccion}")

            # Todo mensaje de hilo pasa por el gate (agrega, cambia o cancela filas).
            # La decisión viaja por la llamada (no por estado global).
            continuar, decision, thread_ctx = classifier_evaluar(email, customer, ETAPA_REPLY, direccion)
            if not continuar:
                duckConn.close()
                return None

            parser = PARSERS_REPLY[customer](duckConn)
            # La decisión viaja con el procesamiento de este correo.
            parser.classifier_decision = decision

            try :
                # Solo con CLASSIFIER_EXTRACT distinto de regex: cambios de
                # filas pedidos en el texto (PENDING se aplica, el resto va a
                # revisión de REPARE en el mismo hilo).
                if review.debe_atender(decision, thread_ctx, email):

                    async def enviar_a_repare(mensaje_revision):
                        await reply_mail_onl_text(
                            host_email = customer_email,
                            client=client,
                            user_id=user_id,
                            mail_id=email.id,
                            mensaje=mensaje_revision,
                        )

                    result = await review.atender(decision, thread_ctx, db, enviar_a_repare)
                else:
                    result = await parser.parse(
                        client,
                        user_id,
                        mail_id,
                        email,
                        direccion,
                        customer,
                        customer_email
                    )

                if result is None:
                    return
            except Exception as e:
                print(f"[ERROR] ->{e}")
                return
            

            mensaje = result.get("mensaje")
            attachments = result.get("attachments")


            if attachments or result.get("temporary_files"):

                await reply_with_attachments(
                    host_email = customer_email,
                    client=client,
                    user_id=user_id,
                    mail_id=email.id,
                    mensaje=mensaje,
                    attachments=attachments,
                    temporary_files=result.get("temporary_files"),
                )

            elif mensaje:

                await reply_mail_onl_text(
                    host_email = customer_email,
                    client=client,
                    user_id=user_id,
                    mail_id=email.id,
                    mensaje=mensaje,
                )


                  
        else:



            flujo = '[INIT]'
            
            if (validator.is_duplicate_email(email)) and (not DEBUG):
                            print(f"{flujo}[INFO] Segunda notificación detectada. Se ignora.")
                            duckConn.close()
                            return "EMAIL_DUPLICADO"

            decision = None
            if customer not in GATE_EN_PARSER_INIT:
                continuar, decision = classifier_gate(email, customer, ETAPA_INIT)
                if not continuar:
                    duckConn.close()
                    return None

            parser = PARSERS_INIT[customer](duckConn)
            parser.classifier_decision = decision

            try:
                result = await parser.parse(
                    client,
                    user_id,
                    mail_id, 
                    email,
                    customer,
                )


                if result is None:
                    if DEBUG:
                        export_csv(duckConn)
                    return


            except Exception as e:
                print(f"[ERROR] Problema en parseo->:{e}") 
                return None



            mensaje = result.get("mensaje")
            attachments = result.get("attachments")

            if attachments or result.get("temporary_files"):

                await reply_with_attachments(
                    host_email = customer_email,
                    client=client,
                    user_id=user_id,
                    mail_id=email.id,
                    mensaje=mensaje,
                    attachments=attachments,
                    temporary_files=result.get("temporary_files"),
                )

            elif mensaje:

                await reply_mail_onl_text(
                    host_email = customer_email,
                    client=client,
                    user_id=user_id,
                    mail_id=email.id,
                    mensaje=mensaje,
                )
    else:
        # print(f"[INFO] Tipo de correo no permitido")
        return "EMAIL_NO_VALIDO"

    if DEBUG:
        # print(f"[{flujo}] Exportando tablas a CSV para depuración")
        export_csv(duckConn)

    print_email_summary(
        email=email,
        tipo_correo=(
            "Respuesta"
            if type_email == "reply"
            else "Inicial"
        ),
        cliente=customer,
    )

    duckConn.close()

    return "recibido"


def print_email_summary(
    email,
    tipo_correo: str,
    cliente: str | None = None,
):

    mexico_tz = ZoneInfo("America/Mexico_City")

    received_at = getattr(email, "received_date_time", None)

    if received_at:

        try:

            if isinstance(received_at, str):
                received_at = datetime.fromisoformat(
                    received_at.replace("Z", "+00:00")
                )

            fecha_llegada = received_at.astimezone(
                mexico_tz
            ).strftime("%d/%m/%Y %H:%M:%S")

        except Exception:

            fecha_llegada = str(received_at)

    else:

        fecha_llegada = "No disponible"

    remitente = "No disponible"

    sender = getattr(email, "sender", None)

    if sender and sender.email_address:

        nombre = sender.email_address.name
        direccion = sender.email_address.address

        if nombre and direccion:
            remitente = f"{nombre} <{direccion}>"

        elif direccion:
            remitente = direccion

        elif nombre:
            remitente = nombre

    destinatarios = []

    to_recipients = getattr(email, "to_recipients", None)

    if to_recipients:

        for recipient in to_recipients:

            if recipient.email_address:

                address = recipient.email_address.address

                if address:
                    destinatarios.append(address)

    destinatarios_texto = ", ".join(destinatarios)

    if not destinatarios_texto:
        destinatarios_texto = "No disponible"

    asunto = getattr(email, "subject", None)

    if not asunto:
        asunto = "Sin asunto"

    texto = "Sin contenido"

    body = getattr(email, "unique_body", None)

    if body and getattr(body, "content", None):

        texto = body.content.strip()

    # Evitar logs gigantes
    if len(texto) > 1000:

        texto = texto[:1000] + "..."

    has_attachments = getattr(
        email,
        "has_attachments",
        False
    )

    print()
    print("=" * 90)
    print(f"CORREO:{tipo_correo.upper()}")
    print("=" * 90)

    print(f"Fecha llegada   : {fecha_llegada}")
    print(f"Cliente         : {cliente or 'No identificado'}")
    print(f"Remitente       : {remitente}")
    print(f"Destinatarios   : {destinatarios_texto}")
    print(f"Asunto          : {asunto}")
    print(
        f"Adjuntos        : "
        f"{'SI' if has_attachments else 'NO'}"
    )

    print("-" * 90)


def export_csv(duck_conn, output_dir="debug"):

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    tables = duck_conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name
    """).fetchall()

    for (table_name,) in tables:

        output_file = Path(output_dir) / f"{table_name}.csv"

        duck_conn.execute(f"""
            COPY "{table_name}"
            TO '{output_file.as_posix()}'
            (HEADER, DELIMITER ',');
        """)



def get_customer_email(customer: str) -> str | None:
    customer = customer.lower().strip()

    if customer.startswith("test_"):
        customer = "test"

    for email, customer_name in CUSTOMER_INDEX.items():
        if customer_name.lower().strip() == customer:
            return email

    return None


def resolve_test_customer(subject: str) -> str | None:
    """Resuelve el parser de prueba indicado entre corchetes en el asunto."""

    match = re.search(r"\[\s*([^\]]+?)\s*\]", subject or "")

    if not match:
        return None

    requested_customer = match.group(1).lower().strip()

    candidates = (
        requested_customer,
        f"test_{requested_customer}",
    )

    for candidate in candidates:
        if candidate in PARSERS_INIT and candidate in PARSERS_REPLY:
            return candidate

    return None
