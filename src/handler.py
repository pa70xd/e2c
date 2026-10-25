import base64
import json
import time
import httpx
from dateutil import parser
from fastapi.responses import HTMLResponse, PlainTextResponse
from typing import Any
from fastapi import APIRouter, status, Body, Response, BackgroundTasks
import msal
from datetime import datetime, timedelta
import os
import hmac
import requests
from google.cloud import pubsub_v1
from src.service import processMail
from typing import Any
from fastapi import Body, HTTPException
from src.service import processMail
import time

handler = APIRouter()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')
MAIL = os.getenv('MAIL', "solkos@imberacooling.com")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]
PROJECT_ID = os.getenv('PROJECT_ID')
NOTIFICATIONS_TOPIC_ID = os.getenv('NOTIFICATIONS_TOPIC_ID', default='graph-api-testing')
# Opcional: si está definida, /receive_mail solo procesa notificaciones cuyo clientState coincida.
GRAPH_CLIENT_STATE = os.getenv('GRAPH_CLIENT_STATE')


def _client_state_valid(mail) -> bool:
    received = mail.get("clientState") if isinstance(mail, dict) else None
    if not isinstance(received, str):
        return False
    return hmac.compare_digest(received.encode(), GRAPH_CLIENT_STATE.encode())


@handler.post(
    "/lifecyclenotif",
    response_class=PlainTextResponse
)
async def lifecyclenotif(validationToken: Any = None, payload: Any = Body(None), response: Response = None):
    if validationToken is not None and validationToken != '':
        print(f"validationToken: {validationToken}")
        response.status_code = status.HTTP_200_OK
        return validationToken

    print(f"lifecyclenotif received: {payload}")

    for message in payload['value']:
        if message['lifecycleEvent'] == 'reauthorizationRequired':
            await ReuthorizeWebhook(message)

            response.status_code = status.HTTP_202_ACCEPTED
    return 'success'


async def ReuthorizeWebhook(message):
    # print('reauthorizing...')
    expDate = parser.parse(message['subscriptionExpirationDateTime'])

    # print(f"reauthorizationRequired notif received with {((expDate.replace(tzinfo=None) - datetime.utc now().replace(tzinfo=None)).total_seconds() / 60)} minutes remaining")

    app = msal.ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY)
    token_result = app.acquire_token_for_client(scopes=SCOPES)

    if "access_token" in token_result:
        token = token_result["access_token"]
        url = f'https://graph.microsoft.com/v1.0/subscriptions/{message["subscriptionId"]}'

        # 1. Formatear la fecha como string ISO 8601 (Graph lo requiere)
        new_expiration = (expDate + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')

        headers = {'Authorization': f'Bearer {token}'}
        body = {"expirationDateTime": new_expiration}

        start = time.time()
        # 2. Usar httpx.AsyncClient para una llamada no bloqueante
        async with httpx.AsyncClient() as client:
            authresponse = await client.patch(url=url, headers=headers, json=body)
        end = time.time()
        print(f"({end - start}s) - {authresponse.json()}")
    else:
        print("Failed to authenticate:", token_result.get("error_description"))
        return None

async def procesar_mail_background(mail):
    try:
        await processMail(mail)
    except Exception as e:
        print(f"[BACKGROUND][ERROR] Falló el procesamiento en background: {e}")
        import traceback
        traceback.print_exc()


@handler.post(
    "/receive_mail",
    response_class=PlainTextResponse
)
async def recieve_mail(
    validationToken: Any = None,
    payload: Any = Body(None),
    background_tasks: BackgroundTasks = None,
):

    # Validación inicial de Microsoft Graph
    if validationToken:
            return validationToken

    for mail in payload["value"]:
        if GRAPH_CLIENT_STATE and not _client_state_valid(mail):
            print("[SEGURIDAD] Notificación descartada: clientState no coincide.")
            continue
        background_tasks.add_task(procesar_mail_background, mail)

    return "Correo recibido, procesando en background."
