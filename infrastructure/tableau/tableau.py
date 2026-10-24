import os
import json
import time
from datetime import datetime
import xml.etree.ElementTree as ET
import pandas as pd
import requests


PROJECT_ID = os.getenv("PROJECT_ID", "imberalink-238816")
TABLEAU_TOKEN_NAME = os.getenv("TOKEN_NAME", "")
TABLEAU_TOKEN_SECRET = os.getenv("TOKEN_SECRET", "")
URL_BASE = "https://tableau.imberacooling.com"
READ_METADATA_URL = f"{URL_BASE}/api/v1/vizql-data-service/read-metadata"
QUERY_URL = f"{URL_BASE}/api/v1/vizql-data-service/query-datasource"
LOGIN_URL = f"{URL_BASE}/api/3.25/auth/signin"

DATA_LOGIN = f"""<?xml version="1.0" encoding="UTF-8"?><tsRequest><credentials personalAccessTokenName="{TABLEAU_TOKEN_NAME}" personalAccessTokenSecret="{TABLEAU_TOKEN_SECRET}"><site contentUrl="" /></credentials></tsRequest>"""

def getToken():
    try:
        headers = {
            "Content-Type": "application/xml"
        }

        response = requests.post(LOGIN_URL, headers=headers, data=DATA_LOGIN)
        data = response.text

        if data is not None:
            data_root = ET.fromstring(data)
        else:
            raise

        if data_root.find("{http://tableau.com/api}credentials") is not None:
            global TOKEN
            token_node = data_root.find("{http://tableau.com/api}credentials")
            if token_node is not None:
                token = token_node.attrib["token"]
                return token
            else:
                print("login error")
        # else:
        #     print(data)
    except Exception as e:
        print(f"[TABLEAU] Error occurred in login: {e}")

def getPtoVentaData(id_pto: list[str]):
    data = None

    query_data = {
        "datasource": {
            "datasourceLuid": "84c40d33-04f9-4b89-a495-f0a952fca30d"
        },
        "query": {
            "fields": [{'fieldCaption': 'ID_PTO_VENTA'}, {'fieldCaption': 'ID_DISTRIBUIDORA'}, {'fieldCaption': 'DISTRIBUIDORA'}, {'fieldCaption': 'CATEGORIA'}, {'fieldCaption': 'CLIENTE'}],
            "filters": [
                {
                    "field": {
                        "fieldCaption": "ID_PTO_VENTA"
                    },
                    "filterType": "SET",
                    "values": id_pto,
                    "exclude": False
                }
            ]
        }
    }

    token = getToken()

    if token is None:
        raise

    headers = {
        "X-Tableau-auth": token,
        "Content-Type": "application/json"
    }

    response = requests.post(QUERY_URL, headers=headers, json=query_data)

    if response is not None:
        data = json.loads(response.text)
        seen = {}
        for row in data["data"]:
            seen.setdefault(row["ID_PTO_VENTA"], row)
        return list(seen.values())
    else:
        return None


def getModelo(serie_activo: list[str]):
    data = None

    query_data = {
        "datasource": {
            "datasourceLuid": "84c40d33-04f9-4b89-a495-f0a952fca30d"
        },
        "query": {
            "fields": [{'fieldCaption': 'ACTIVO'}, {'fieldCaption': 'SERIE'}, {'fieldCaption': 'MODELO'}],
            "filters": [
                {
                    "field": {
                        "fieldCaption": "ACTIVO"
                    },
                    "filterType": "SET",
                    "values": serie_activo,
                    "exclude": False
                }
            ]
        }
    }

    token = getToken()

    if token is None:
        raise

    headers = {
        "X-Tableau-auth": token,
        "Content-Type": "application/json"
    }

    response = requests.post(QUERY_URL, headers=headers, json=query_data)

    if response is not None:
        data = json.loads(response.text)
        seen = {}
        for row in data["data"]:
            seen.setdefault(row["ACTIVO"], row)
        return list(seen.values())
    else:
        return None

def get_modelo_act_ser(field: str, values: list[str]):
    # print(f" [INFO] Consultando field:{field}")
    query_data = {
        "datasource": {
            "datasourceLuid": "84c40d33-04f9-4b89-a495-f0a952fca30d"
        },
        "query": {
            "fields": [
                {"fieldCaption": "ACTIVO"},
                {"fieldCaption": "SERIE"},
                {"fieldCaption": "MODELO"}
            ],
            "filters": [
                {
                    "field": {"fieldCaption": field},
                    "filterType": "SET",
                    "values": values,
                    "exclude": False
                }
            ]
        }
    }

    token = getToken()

    if token is None:
        raise Exception("No se pudo obtener el token de Tableau.")

    headers = {
        "X-Tableau-auth": token,
        "Content-Type": "application/json"
    }

    response = requests.post(QUERY_URL, headers=headers, json=query_data)

    if not response.ok:
        return []

    data = response.json()

    seen = {}
    for row in data["data"]:
        key = row[field]
        seen.setdefault(key, row)

    # print("[INFO] Lista de resultados: ",seen)

    return list(seen.values())