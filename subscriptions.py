# Code snippets are only available for the latest version. Current version is 1.x
import asyncio
import os

from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.subscription import Subscription
import msal
from dateutil import parser
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
TENANT_ID = os.getenv("TENANT_ID", "")

# print("CLIENT_ID:", CLIENT_ID)
# print("TENANT_ID:", TENANT_ID)
# print("CLIENT_SECRET:", "OK" if CLIENT_SECRET else "VACIO")


AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]

emails = [
    "cliente.danone@repare.com.mx",
    #"cliente.hnk@repare.com.mx",
    "cliente.holanda@repare.com.mx",
    #"cliente.kof@repare.com.mx",
    #"cliente.imbera@repare.com.mx",
    "cliente.kdrp@repare.com.mx",
    #"cliente.torrey@repare.com.mx"
]

# Buzón de pruebas opcional (mismo que usa src/email_type.py).
_test_mailbox = os.getenv("E2C_TEST_MAILBOX", "").strip()
if _test_mailbox:
    emails.append(_test_mailbox)

def getToken():
    # Get OAuth Token
    app = msal.ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY)
    token_result = app.acquire_token_for_client(scopes=SCOPES)

    if "access_token" in token_result:
        return token_result["access_token"]
    else:
        print("Failed to authenticate:", token_result.get("error_description"))
        return None

def getClient():
    try:
        credentials = ClientSecretCredential(tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        client = GraphServiceClient(credentials=credentials, scopes=SCOPES)
        return client
    except Exception as ex:
        print(f"{str(ex)}")
        return None

async def test():
    try:
        client = getClient()
        token = getToken()
        headers = {'Authorization': f'Bearer {token}'}

        # ===== PRUEBA SI EL USUARIO EXISTE =====
        # response = requests.get(
        #     "https://graph.microsoft.com/v1.0/users/cliente.holanda@repare.com.mx",
        #     headers=headers,
        # )

        # print("Status:", response.status_code)
        # print(response.text)


        url = f'https://graph.microsoft.com/v1.0/subscriptions'

        body = {
            "changeType": "created",
            "notificationUrl": "https://prod---repare-email-parser-b7agk5thba-uc.a.run.app/receive_mail",
            "lifecycleNotificationUrl": "https://prod---repare-email-parser-b7agk5thba-uc.a.run.app/lifecyclenotif",
            "resource": "users/cliente.kdrp@repare.com.mx/messages",
            "expirationDateTime": f"{(datetime.now() + timedelta(days=5)).isoformat()}Z",
        }

        # print(body)

        if client is not None:
            subs = await client.subscriptions.get()

            if subs and subs.value:
                resources = [sub.resource.split("/")[1] if sub.resource else "" for sub in subs.value]
                for email in emails:
                    if email not in resources:
                        body = {
                            "changeType": "created",
                            "notificationUrl": "https://repare-email-parser-545989770214.us-central1.run.app/receive_mail",
                            "lifecycleNotificationUrl": "https://repare-email-parser-545989770214.us-central1.run.app/lifecyclenotif",
                            "resource": f"users/{email}/messages",
                            "expirationDateTime": f"{(datetime.now() + timedelta(hours=10)).isoformat()}Z",
                        }

                        print(body)
                        response = requests.post(url, headers=headers, json=body)

                        if response.status_code == 201:
                            print("subscription created")
                        else:
                            print(response.text)
    except Exception as ex:
        print(ex)



async def list_subscriptions():
    """
    Lista todas las suscripciones registradas en Microsoft Graph.
    """

    client = getClient()

    if client is None:
        print("No fue posible crear el cliente de Graph.")
        return

    try:
        result = await client.subscriptions.get()

        if not result or not result.value:
            print("No existen suscripciones registradas.")
            return

        print(f"\nSe encontraron {len(result.value)} suscripciones:\n")

        for sub in result.value:
            print("=" * 80)
            print(f"ID              : {sub.id}")
            print(f"Resource        : {sub.resource}")
            print(f"Change Type     : {sub.change_type}")
            print(f"Notification URL: {sub.notification_url}")
            print(f"Lifecycle URL   : {sub.lifecycle_notification_url}")
            print(f"Expiration      : {sub.expiration_date_time}")
            print(f"Client State    : {sub.client_state}")
            print("=" * 80)

    except Exception as e:
        print(e)

async def delete_all_subscriptions():
    """
    Elimina todas las suscripciones registradas en Microsoft Graph.
    """

    client = getClient()

    if client is None:
        print("No fue posible crear el cliente de Graph.")
        return

    try:
        result = await client.subscriptions.get()

        if not result or not result.value:
            print("No existen suscripciones.")
            return

        print(f"Se encontraron {len(result.value)} suscripciones.\n")

        for sub in result.value:
            try:
                print(f"Eliminando {sub.id}...")
                await client.subscriptions.by_subscription_id(sub.id).delete()
                print("   ✓ Eliminada")
            except Exception as ex:
                print(f"   ✗ Error: {ex}")

        print("\nProceso terminado.")

    except Exception as ex:
        print(ex)


async def delete_subscription(subscription_id: str):
    """
    Elimina una suscripción específica de Microsoft Graph.
    """

    client = getClient()

    if client is None:
        print("No fue posible crear el cliente de Graph.")
        return

    try:
        print(f"Eliminando suscripción: {subscription_id}")

        await client.subscriptions.by_subscription_id(
            subscription_id
        ).delete()

        print("✓ Suscripción eliminada correctamente.")

    except Exception as ex:
        print(f"✗ Error eliminando suscripción: {ex}")


if __name__ == "__main__":
    #---------subscribe
    asyncio.run(test())
    #---------lista subscripciones
    asyncio.run(list_subscriptions())
    


    #----------Elimina todas las subcripciones
    # asyncio.run(delete_all_subscriptions())
    # elimina una subscripcion
    # asyncio.run(
    #     delete_subscription(
    #         "35a2341f-f1cb-4d41-9b78-00254a14c65b"
    #     )
    # )