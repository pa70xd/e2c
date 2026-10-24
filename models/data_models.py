from datetime import datetime
from typing import Optional

from pydantic import BaseModel

class RecipientModel(BaseModel):
    name: Optional[str] = None
    email: str


class EmailModel(BaseModel):
    # Llave primaria
    id: Optional[int] = None

    # Identificador del caso
    request_code: Optional[str] = None

    # Microsoft Graph
    graph_message_id: str
    internet_message_id: Optional[str] = None
    conversation_id: str
    conversation_index: Optional[str] = None
    parent_message_id: Optional[str] = None
    change_key: Optional[str] = None
    link_email: Optional[str] = None

    # Dirección
    direction: str

    # Remitente
    sender_name: Optional[str] = None
    sender_email: str

    # Destinatarios
    recipients_to: list[RecipientModel] = []
    recipients_cc: list[RecipientModel] = []
    recipients_bcc: list[RecipientModel] = []

    # Contenido
    subject: str
    body: Optional[str] = None

    # Adjuntos
    has_attachments: bool = False
    attachment_count: int = 0

    # Estado del procesamiento
    processing_status: str = "RECEIVED"
    processing_message: Optional[str] = None

    # Fechas
    received_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    # Auditoría
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    customer:Optional[str]=None
