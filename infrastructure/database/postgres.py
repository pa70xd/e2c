from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from google.cloud import secretmanager
import numpy as np
import pandas as pd
import psycopg2
import json
import os


load_dotenv()

def get_connection():

    try:
        secret_name = os.getenv("SECRET_PG_ACC")
        db_host = os.getenv("DB_HOST")
        db_name = os.getenv("DB_NAME")
        db_port = int(os.getenv("DB_PORT", 5432))

        client = secretmanager.SecretManagerServiceClient()

        response = client.access_secret_version(
            request={"name": secret_name}
        )

        credentials = json.loads(
            response.payload.data.decode("UTF-8")
        )

        return psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=credentials["DB_USER"],
            password=credentials["DB_PASSWORD"],
            cursor_factory=RealDictCursor
        )

    except Exception as e:
        raise Exception(f"Error creando conexión a PostgreSQL: {e}")


def _sin_nan(valor):
    """float NaN, pd.NA y NaT -> None (PostgreSQL guardaría 'NaN' o fallaría).

    Red de seguridad central: con pandas 3, iterrows y similares vuelven NaN los
    faltantes de un DataFrame. Recorre tuplas, listas y dicts de parámetros; lo
    demás (str, bytes, Json, fechas) pasa intacto.
    """
    if valor is None or isinstance(valor, (str, bytes)):
        return valor
    if isinstance(valor, tuple):
        return tuple(_sin_nan(v) for v in valor)
    if isinstance(valor, list):
        return [_sin_nan(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _sin_nan(v) for k, v in valor.items()}
    if valor is pd.NA or valor is pd.NaT:
        return None
    if isinstance(valor, (float, np.floating)) and valor != valor:
        return None
    return valor


def execute_query(query: str, params: tuple = ()):
    params = _sin_nan(params)
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)

            # Si la consulta devuelve filas (SELECT o RETURNING)
            if cursor.description is not None:
                result = cursor.fetchall()
            else:
                result = None

            conn.commit()

            return result

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()