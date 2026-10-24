from io import BytesIO
from pathlib import Path
import base64
import re
import unicodedata

import pandas as pd

from config.customers.heineken.columns_names import (
    NAMES_D2D, NAMES_RUTA, COLUMNAS_D2D, COLUMNAS_RUTA,
    MARCADORES_ENCABEZADO, COL_ARCHIVO, COL_FILA_EXCEL,
)
from config.customers.heineken.reglas_heineken import FLUJO_D2D, VALORES_VACIOS

EXCEL_EXTENSIONS = (".xlsx", ".xlsm")
FILAS_BUSQUEDA_ENCABEZADO = 10


class HEINEKEN_READER:

    @staticmethod
    def layout(flujo):
        """(alias de encabezados, columnas canónicas) del flujo."""
        if flujo == FLUJO_D2D:
            return NAMES_D2D, COLUMNAS_D2D
        return NAMES_RUTA, COLUMNAS_RUTA

    @staticmethod
    def normalizar_encabezado(texto) -> str:
        texto = unicodedata.normalize("NFKD", str(texto))
        texto = "".join(c for c in texto if not unicodedata.combining(c)).upper()
        texto = re.sub(r"\s+", " ", texto)
        texto = re.sub(r"\s*/\s*", "/", texto)
        return texto.strip(" /")

    @staticmethod
    def leer(content: bytes, flujo: str, vaciar_os: bool = True) -> pd.DataFrame:
        """Lee la primera hoja, ubica la fila de encabezados y regresa las columnas
        canónicas del flujo, más el renglón de Excel de cada fila."""

        nombres, columnas = HEINEKEN_READER.layout(flujo)
        crudo = pd.read_excel(BytesIO(content), header=None, dtype=str, sheet_name=0)

        fila_encabezado = None
        for i in range(min(FILAS_BUSQUEDA_ENCABEZADO, len(crudo))):
            canonicos = {
                nombres.get(HEINEKEN_READER.normalizar_encabezado(v))
                for v in crudo.iloc[i] if pd.notna(v)
            }
            if MARCADORES_ENCABEZADO <= canonicos:
                fila_encabezado = i
                break

        if fila_encabezado is None:
            vacio = pd.DataFrame(columns=columnas + [COL_FILA_EXCEL])
            vacio.attrs["presentes"] = set()
            return vacio

        datos = crudo.iloc[fila_encabezado + 1:].copy()
        nuevos = [nombres.get(HEINEKEN_READER.normalizar_encabezado(v)) if pd.notna(v) else None
                  for v in crudo.iloc[fila_encabezado]]
        datos.columns = range(len(nuevos))
        conservar = {}
        for posicion, nombre in enumerate(nuevos):
            if nombre and nombre not in conservar.values():
                conservar[posicion] = nombre
        datos = datos[list(conservar)].rename(columns=conservar)
        presentes = set(conservar.values())
        col_serie = next((p + 1 for p, n in conservar.items() if n == "SERIE"), None)

        # El índice de pandas es 0-based; el renglón de Excel es índice + 1.
        datos[COL_FILA_EXCEL] = (datos.index + 1).astype(str)

        for columna in columnas:
            if columna not in datos.columns:
                datos[columna] = None

        datos = datos[columnas + [COL_FILA_EXCEL]]
        datos = HEINEKEN_READER.limpiar(datos, vaciar_os)

        vacias = datos[columnas].isna().all(axis=1)
        datos = datos[~vacias].reset_index(drop=True)
        datos.attrs["presentes"] = presentes
        datos.attrs["col_serie"] = col_serie
        datos.attrs["fila_encabezado"] = fila_encabezado + 1
        return datos

    @staticmethod
    def limpiar(df: pd.DataFrame, vaciar_os: bool) -> pd.DataFrame:
        def texto(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            v = str(v).strip()
            return None if not v or v.upper() in VALORES_VACIOS else v

        def digitos(v):
            v = texto(v)
            if v is None:
                return None
            return re.sub(r"\D", "", re.sub(r"\.0+$", "", v)) or None

        def cp(v):
            d = digitos(v)
            return d.zfill(5) if d and len(d) <= 5 else d

        for columna in df.columns:
            if columna != COL_FILA_EXCEL:
                df[columna] = df[columna].map(texto)

        if "CP" in df.columns:
            df["CP"] = df["CP"].map(cp)
        if "TELEFONO" in df.columns:
            df["TELEFONO"] = df["TELEFONO"].map(digitos)
        if vaciar_os and "OS" in df.columns:
            df["OS"] = None

        return df

    @staticmethod
    def registrar(duck_conn, df: pd.DataFrame, nombre: str) -> str:
        """Crea la tabla DuckDB con todas las columnas como VARCHAR."""
        duck_conn.register("tmp_df", df)
        columnas = ", ".join(f'CAST("{c}" AS VARCHAR) AS "{c}"' for c in df.columns)
        duck_conn.execute(f'CREATE OR REPLACE TABLE "{nombre}" AS SELECT {columnas} FROM tmp_df')
        duck_conn.unregister("tmp_df")
        return nombre

    @staticmethod
    async def get_adjuntos(client, user_id, mail_id, duck_conn, flujo, vaciar_os=True):
        """Descarga los Excel del correo y registra una tabla por archivo."""

        attachments = await (
            client.users.by_user_id(user_id)
            .messages.by_message_id(mail_id)
            .attachments.get()
        )

        archivos = []
        for index, attachment in enumerate(attachments.value or [], start=1):
            nombre = attachment.name or ""
            if (not hasattr(attachment, "content_bytes") or nombre.startswith("~$")
                    or Path(nombre).suffix.lower() not in EXCEL_EXTENSIONS):
                continue

            content = attachment.content_bytes
            if content.startswith(b"UEs"):
                content = base64.b64decode(content)

            tabla = f"excel_{index}"
            df = HEINEKEN_READER.leer(content, flujo, vaciar_os)
            presentes = df.attrs.get("presentes", set())
            col_serie = df.attrs.get("col_serie")
            fila_encabezado = df.attrs.get("fila_encabezado", 1)
            df[COL_ARCHIVO] = tabla
            HEINEKEN_READER.registrar(duck_conn, df, tabla)

            archivos.append({
                "name": nombre, "type": "excel", "table": tabla, "content": content,
                "presentes": presentes, "col_serie": col_serie, "fila_encabezado": fila_encabezado,
            })

        return archivos
