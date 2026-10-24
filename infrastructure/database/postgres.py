from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from google.cloud import secretmanager
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


def execute_query(query: str, params: tuple = ()):
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