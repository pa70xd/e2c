import json
from pathlib import Path
import base64
import re
import time
import hashlib
import os

# Variable de entorno opcional con el buzón de pruebas (cliente "test").
# Sin ella no hay buzón de pruebas.
TEST_MAILBOX_ENV = "E2C_TEST_MAILBOX"


def with_test_mailbox(mailboxes: dict) -> dict:
    """Agrega E2C_TEST_MAILBOX (si está definida) como cliente "test"."""
    address = os.getenv(TEST_MAILBOX_ENV, "").strip().lower()
    if address:
        mailboxes = {**mailboxes, address: "test"}
    return mailboxes


# Variable de entorno opcional con los clientes habilitados, separados por
# comas. Sin ella valen SOLO los clientes de siempre. Con ella se suman los que
# indique (los de siempre no se pueden apagar por aquí). Un cliente del índice
# que no esté habilitado se registra en el log y se ignora (sin respuesta).
CLIENTES_HABILITADOS_ENV = "E2C_CLIENTES_HABILITADOS"
CLIENTES_BASE = ("danone", "holanda", "penafiel", "heineken")
ALIAS_CLIENTES = {"kdrp": "penafiel", "hnk": "heineken"}


def clientes_habilitados() -> set[str]:
    """Clientes que el servicio atiende (se lee en cada llamada)."""
    habilitados = set(CLIENTES_BASE)
    for item in os.getenv(CLIENTES_HABILITADOS_ENV, "").split(","):
        item = item.strip().lower()
        if item:
            habilitados.add(ALIAS_CLIENTES.get(item, item))
    return habilitados


def cliente_habilitado(cliente: str) -> bool:
    # El buzón de pruebas ("test") lo gobierna E2C_TEST_MAILBOX, no este flag.
    return cliente == "test" or cliente in clientes_habilitados()


class EMAIL_TYPE:

    def __init__(self, config_path: str = "config/email_index.json"):
        self.mailboxes = self._load_mailboxes(config_path)
        self.processed_emails = {}


    def _load_mailboxes(self, config_path: str) -> dict:
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo de configuración: {config_path}"
            )

        with path.open("r", encoding="utf-8") as file:
            return with_test_mailbox({
                key.lower(): value
                for key, value in json.load(file).items()
            })

    def validate_email(self, email):

        # print(" [INFO] Validando naturaleza de email ")

        if email.is_draft:
            return False, "DRAFT"

        if not email.subject or not email.subject.strip():
            return False, "EMPTY_SUBJECT"

        if self._is_auto_submitted(email):
            return False, "AUTO_SUBMITTED"

        if not email.unique_body:
            return False, "EMPTY_BODY"

        if email.received_date_time is None:
            return False, "MISSING_RECEIVED_DATE"

        if getattr(email, "odata_type", None) == "#microsoft.graph.eventMessageRequest":
            return False, "EVENT_MESSAGE"

        sender = (
            email.sender.email_address.address.lower()
            if email.sender and email.sender.email_address
            else ""
        )

        ignored_senders = (
            "errorreportingnotifications-noreply@google.com",
        )

        if sender in ignored_senders:
            print(f"[INFO] Remitente ignorado: {sender}")
            return False, "IGNORED_SENDER"

        if not self._is_initial_message(email):
            REPLY_MESSAGE = True
            # print("Deteccion de correo respueta")
        else:
            REPLY_MESSAGE = False
        #customer = self._detect_customer(email)

        #if customer is None:
         #   return False, "UNSUPPORTED_MAILBOX"

        subject = email.subject.lower()

        auto_reply = (
            "automatic reply",
            "respuesta automática",
            "out of office",
            "fuera de la oficina",
            "autoreply",
            "auto reply",
        )

        delivery_failure = (
            "delivery status notification",
            "undeliverable",
            "mail delivery failed",
            "failure notice",
        )

        read_receipt = (
            "read:",
            "read receipt",
            "confirmación de lectura",
        )

        if any(text in subject for text in auto_reply):
            return False, "AUTO_REPLY"

        if any(text in subject for text in delivery_failure):
            return False, "DELIVERY_FAILURE"

        if any(text in subject for text in read_receipt):
            return False, "READ_RECEIPT"

        if REPLY_MESSAGE:
            print("[INFO] Detección de correo tipo respuesta")
            return [True,"reply"]
        else:
            print("[INFO] Detección de correo tipo inicial")
            return [True,"no-reply"]
            
    def _is_initial_message(self, email) -> bool:

        subject = (email.subject or "").strip().lower()

        # Respuestas/Reenvíos más comunes
        prefixes = (
            "re:",
            "rv:",
            "fw:",
            "fwd:",
        )

        if subject.startswith(prefixes):
            return False

        # Buscar headers si los pediste en Graph
        headers = getattr(email, "internet_message_headers", None)

        if headers:
            for h in headers:
                name = (h.name or "").lower()
                if name in ("in-reply-to", "references"):
                    return False

        return True

    def detect_customer(self, email):

        # Primero intenta identificar por destinatario
        recipients = email.to_recipients or []
        recipients_cc = email.cc_recipients or []
        
        recipients = recipients + recipients_cc

        for recipient in recipients:

            address = recipient.email_address.address.lower().strip()

            if address in self.mailboxes:
                if self._habilitado(self.mailboxes[address]):
                    return self.mailboxes[address]

        # Si no lo encuentra, intenta identificar por remitente
        sender = email.from_

        if sender and sender.email_address:

            address = sender.email_address.address.lower().strip()

            if address in self.mailboxes:
                if self._habilitado(self.mailboxes[address]):
                    return self.mailboxes[address]

        return None

    def _habilitado(self, cliente: str) -> bool:
        if cliente_habilitado(cliente):
            return True
        print(
            f"[INFO] Cliente '{cliente}' no habilitado "
            f"({CLIENTES_HABILITADOS_ENV}); correo ignorado"
        )
        return False

    def _buzones_habilitados(self) -> dict:
        return {
            address: cliente
            for address, cliente in self.mailboxes.items()
            if cliente_habilitado(cliente)
        }

    def detect_direccion(self, email):

        recipients = email.to_recipients or []
        sender = email.sender


        sender_address = ""
        if sender and sender.email_address:
            sender_address = (sender.email_address.address or "").lower()

        recipient_addresses = [
            (r.email_address.address or "").lower()
            for r in recipients
            if r.email_address and r.email_address.address
        ]

        body = (email.unique_body.content or "").lower()
        body = re.sub(r"\s+", " ", body)

        buzones = self._buzones_habilitados()
        if len(buzones) < len(self.mailboxes):
            for address in [sender_address, *recipient_addresses]:
                if address in self.mailboxes and address not in buzones:
                    self._habilitado(self.mailboxes[address])

        sender_is_repare = sender_address in buzones
        recipient_is_repare = any(
            addr in buzones
            for addr in recipient_addresses
        )

        # REPARE -> REPARE generado por el bot
        if (
            sender_is_repare
            and recipient_is_repare
            and "estimado usuario repare" in body
        ):
            return buzones[sender_address], "bot"

        # REPARE -> REPARE, respuesta a un correo del bot
        elif sender_is_repare and recipient_is_repare:
            return buzones[sender_address], "reply_to_bot"

        # Cliente -> REPARE
        for address in recipient_addresses:
            if address in buzones:
                return buzones[address], "inbound"

        # REPARE -> Cliente
        if sender_is_repare:
            return buzones[sender_address], "outbound"

        return None

    def _is_auto_submitted(self, email) -> bool: 
        headers = getattr(email, "internet_message_headers", None)

    def _is_auto_submitted(self, email) -> bool:
        headers = getattr(email, "internet_message_headers", None)

        if not headers:
            return False

        for h in headers:
            name = (h.name or "").lower()
            value = (h.value or "").lower()

            if name == "auto-submitted" and value not in ("no", ""):
                return True

            if name == "x-auto-response-suppress":
                return True

        return False


    def is_duplicate_email(self, email):

        internet_message_id = getattr(
            email,
            "internet_message_id",
            None
        )

        if not internet_message_id:
            return False

        key = internet_message_id.strip().lower()
        now = time.time()

        last_processed = self.processed_emails.get(key)

        if last_processed and now - last_processed < 120:
            print(
                f"[INFO] Correo duplicado ignorado: "
                f"{internet_message_id}"
            )
            return True

        self.processed_emails[key] = now

        # Limpiar registros antiguos
        expired = [
            k
            for k, timestamp in self.processed_emails.items()
            if now - timestamp >= 120
        ]

        for k in expired:
            del self.processed_emails[k]

        return False