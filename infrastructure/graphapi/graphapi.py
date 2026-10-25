
import msal
from azure.identity.aio import ClientSecretCredential
from dotenv import load_dotenv
from msgraph import GraphServiceClient
import os

from msgraph.generated.models.item_attachment import ItemAttachment

from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.users.item.messages.item.create_reply.create_reply_post_request_body import (
    CreateReplyPostRequestBody,
)
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.users.item.messages.item.create_reply.create_reply_post_request_body import (
    CreateReplyPostRequestBody,
)
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType

from msgraph.generated.models.internet_message_header import InternetMessageHeader
from msgraph.generated.users.item.messages.item.reply.reply_post_request_body import ReplyPostRequestBody
from kiota_abstractions.api_error import APIError
import base64


from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.users.item.messages.item.create_reply.create_reply_post_request_body import CreateReplyPostRequestBody


load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
TENANT_ID = os.getenv("TENANT_ID", "")
NOTIFY_ERROR_MAILS = os.getenv("NOTIFY_ERROR_MAILS", "").split("|")
EMAIL_SENDER = 'solkos@imberacooling.com'
SECRET_ID = os.getenv('SECRET_ID', "")
FILE_ID = os.getenv('FILE_ID', "")
DRIVE_ID = os.getenv('DRIVE_ID', "")

URL = f"https://graph.microsoft.com/v1.0"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]

def getToken():
    # Get OAuth Token
    app = msal.ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY)
    token_result = app.acquire_token_for_client(scopes=SCOPES)

    if "access_token" in token_result:
        return token_result["access_token"]
    else:
        print("Failed to authenticate:", token_result.get("error_description"))
        return None


# config\customers\email_index.json
def getClient():
    try:
        credentials = ClientSecretCredential(tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        client = GraphServiceClient(credentials=credentials, scopes=SCOPES)
        return client
    except Exception as ex:
        print(f"{str(ex)}")
        return None

async def sendMail(
    client: GraphServiceClient,
    to: list[str],
    message: str,
    subject: str,
    attachment: Message | bytes | None = None,
    filename: str | None = None,
):
    user = client.users.by_user_id(EMAIL_SENDER)

    mail_body = Message(
        subject=subject,
        body=ItemBody(
            content_type=BodyType.Text,
            content=message,
        ),
        to_recipients=[
            Recipient(
                email_address=EmailAddress(address=address)
            )
            for address in to
        ],
        attachments=[],
    )

    if isinstance(attachment, Message):
        mail_body.attachments.append(
            ItemAttachment(
                odata_type="#microsoft.graph.itemAttachment",
                name=attachment.subject,
                item=attachment,
            )
        )

    elif isinstance(attachment, bytes):
        mail_body.attachments.append(
            FileAttachment(
                odata_type="#microsoft.graph.fileAttachment",
                name=filename,
                content_bytes=attachment,
            )
        )

    result = await user.messages.post(mail_body)
    await user.messages.by_message_id(result.id).send.post()


async def getTemplate(client: GraphServiceClient, files) -> bytes | None:
    client = getClient()
    token = getToken()

    if client is None:
        return None

    try:
        file_url = f"{URL}/drives/{DRIVE_ID}/items/{FILE_ID}/content"

        file_bytes = await client.drives.by_drive_id(DRIVE_ID).items.by_drive_item_id(
            FILE_ID
        ).content.get()

        return file_bytes
    except Exception as ex:
        print(f"ERROR - : {str(ex)}")
        return None
    


async def send_mail_file(
    host_email: str,
    client: GraphServiceClient,
    email: str | list[str],
    mensaje: str,
    asunto: str,
    attachments: list[tuple[str, bytes]] | None = None,
):

    # EMAIL_REPARE = "yael.hurtado@imberacooling.com"
    EMAIL_REPARE = host_email
    
    user = client.users.by_user_id(EMAIL_SENDER)

    mail = Message(
        subject=asunto,
        body=ItemBody(
            content_type=BodyType.Text,
            content=mensaje,
        ),
        to_recipients=[
            Recipient(
                email_address=EmailAddress(
                    address=EMAIL_REPARE
                )
            ),
            # Recipient(
            #     email_address=EmailAddress(
            #         address=EMAIL_DANONE
            #     )
            # ),
        ],
        attachments=[],
    )

    if attachments:
        for filename, content in attachments:
            mail.attachments.append(
                FileAttachment(
                    odata_type="#microsoft.graph.fileAttachment",
                    name=filename,
                    content_bytes=content,
                )
            )

    draft = await user.messages.post(mail)

    await (
        user.messages
        .by_message_id(draft.id)
        .send
        .post()
    )




async def reply_mail_onl_text(
    host_email: str,
    client: GraphServiceClient,
    user_id: str,
    mail_id: str,
    mensaje: str,
):
    
    # EMAIL_REPARE = "yael.hurtado@imberacooling.com"
    EMAIL_REPARE = host_email

    user = client.users.by_user_id(user_id)

    draft = await (
        user.messages
        .by_message_id(mail_id)
        .create_reply
        .post(CreateReplyPostRequestBody())
    )

    body = Message(
        body=ItemBody(
            content_type=BodyType.Html,
            content=mensaje,
        ),
        to_recipients=[
            Recipient(
                email_address=EmailAddress(
                    address=EMAIL_REPARE
                )
            ),
            # Recipient(
            #     email_address=EmailAddress(
            #         address=EMAIL_DANONE
            #     )
            # ),
        ],
    )

    await (
        user.messages
        .by_message_id(draft.id)
        .patch(body)
    )

    await (
        user.messages
        .by_message_id(draft.id)
        .send
        .post()
    )

    print("Respuesta enviada.")



async def reply_mail_init_files(
    host_email: str,
    client: GraphServiceClient,
    user_id: str,
    mail_id: str,
    mensaje: str,
    attachments: list[tuple[str, bytes]] | None = None,
):
    # EMAIL_REPARE = "yael.hurtado@imberacooling.com"
    EMAIL_REPARE = host_email

    user = client.users.by_user_id(user_id)

    draft = await (
        user.messages
        .by_message_id(mail_id)
        .create_reply
        .post(CreateReplyPostRequestBody())
    )

    draft.to_recipients = [
        Recipient(
            email_address=EmailAddress(
                address=EMAIL_REPARE
            )
        )
    ]

    draft.cc_recipients = []
    draft.bcc_recipients = []

    draft.body = ItemBody(
        content_type=BodyType.Html,
        content=mensaje,
    )

    await (
        user.messages
        .by_message_id(draft.id)
        .patch(draft)
    )

    # Agregar adjuntos
    if attachments:
        for filename, content in attachments:
            attachment = FileAttachment(
                odata_type="#microsoft.graph.fileAttachment",
                name=filename,
                content_type=(
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet"
                ),
                content_bytes=content,
            )

            await (
                user.messages
                .by_message_id(draft.id)
                .attachments
                .post(attachment)
            )

    # original_mail = Message()
    # original_mail.is_read = False

    # Enviar
    await (
        user.messages
        .by_message_id(draft.id)
        .send
        .post()
    )

    print(f"Respuesta enviada únicamente a {EMAIL_REPARE}")
