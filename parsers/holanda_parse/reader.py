from config.customers.holanda.columns_names import (
    NAMES_COLUMNS,
    FALLBACK_POSICIONAL,
    SABANA_COLUMNS,
    SUFIJO_ORIGEN,
    COL_ARCHIVO,
    COL_FILA_EXCEL,
)
from pathlib import Path
from io import BytesIO
import pandas as pd
import unicodedata
import base64
import re


class HOLANDA_READER:
    NAMES_COLUMNS = NAMES_COLUMNS
    EXCEL_EXTENSIONS = (".xlsx", ".xls")

    @staticmethod
    async def get_adjuntos(
        client,
        user_id,
        mail_id,
        duck_conn,
        debug=False,
        output_dir="Documentos_Adjuntos",
    ):
        """Descarga los adjuntos del correo y los registra como tablas de
        DuckDB. Igual que el de Danone, más la normalización propia de
        Holanda: fallback posicional, Origen, Fecha/Telefono y Serie."""

        debug_path = Path(output_dir)

        attachments = await (
            client.users
            .by_user_id(user_id)
            .messages
            .by_message_id(mail_id)
            .attachments
            .get()
        )

        if not attachments.value:
            print(" [INFO] El correo no contiene adjuntos.")
            return []

        tables = []

        for index, attachment in enumerate(attachments.value, start=1):

            if not hasattr(attachment, "content_bytes"):
                continue

            if attachment.name.startswith("~$"):
                continue

            extension = Path(attachment.name).suffix.lower()
            if extension not in HOLANDA_READER.EXCEL_EXTENSIONS:
                continue

            content = attachment.content_bytes

            if content.startswith(b"UEs"):
                content = base64.b64decode(content)

            if debug:
                debug_path.mkdir(parents=True, exist_ok=True)
                with open(debug_path / attachment.name, "wb") as file:
                    file.write(content)

            df = pd.read_excel(BytesIO(content), dtype=str)

            df = HOLANDA_READER.normalize_columns(df)
            df = HOLANDA_READER.inferir_origen(df)
            df = HOLANDA_READER.normalize_por_origen(df)
            df = HOLANDA_READER.split_serie(df)

            table_name = f"excel_{index}"

            # Origen de cada fila (archivo + renglón de Excel, con el
            # encabezado en la fila 1) para poder pintar las rechazadas en
            # el archivo original que se regresa en la respuesta.
            df[COL_ARCHIVO] = table_name
            df[COL_FILA_EXCEL] = (df.index + 2).astype(str)

            duck_conn.register("tmp_df", df)
            duck_conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT * FROM tmp_df
            """)
            duck_conn.unregister("tmp_df")

            tables.append({
                "name": attachment.name,
                "type": "excel",
                "table": table_name,
                # Bytes originales: el inbound responde con el mismo
                # archivo de solicitud recibido (observación de Julio).
                "content": content,
            })

        return tables

    @staticmethod
    def normalize(text: str) -> str:
        text = str(text).strip().upper()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        return " ".join(text.split())

    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Alias -> nombre canónico (igual que Danone), con fallback
        posicional para encabezados vacíos de OS/MERMA."""

        normalized_catalog = {
            HOLANDA_READER.normalize(k): v
            for k, v in NAMES_COLUMNS.items()
        }

        columns = {}
        for position, column in enumerate(df.columns):

            if column is None or str(column).strip() == "" or str(column).lower().startswith("unnamed"):
                # Encabezado vacío -- ¿coincide con una posición conocida?
                canonical = FALLBACK_POSICIONAL.get(position)
                if canonical:
                    columns[column] = canonical
                    continue

            normalized = HOLANDA_READER.normalize(column)
            columns[column] = normalized_catalog.get(normalized, normalized)

        df = df.rename(columns=columns)

        # Esquema estable: SABANA_COLUMNS + OS/MERMA (OS hace falta para
        # leer la respuesta outbound del operador).
        columnas_finales = SABANA_COLUMNS + ["OS", "MERMA"]
        valid_columns = set(columnas_finales)
        df = df[[col for col in df.columns if col in valid_columns]]

        for col in columnas_finales:
            if col not in df.columns:
                # Se siembra con "" y no con None: DuckDB infiere una
                # columna de puros None como INTEGER y luego falla al
                # escribir texto (p. ej. MARCA_DUPLICADO).
                df[col] = pd.Series([""] * len(df), dtype="object")

        return df[columnas_finales]

    @staticmethod
    def inferir_origen(df: pd.DataFrame) -> pd.DataFrame:
        """ORIGEN vacío o ausente -> se infiere del sufijo de CASO2
        (SUFIJO_ORIGEN). Un ORIGEN que sí viene no se sobrescribe; si el
        sufijo no se reconoce, queda vacío y la fila se rechaza. Corre
        antes de normalize_por_origen."""

        if df.empty or "ORIGEN" not in df.columns or "CASO2" not in df.columns:
            return df

        def _origen(row):
            actual = row.get("ORIGEN")
            if isinstance(actual, str) and actual.strip():
                return actual
            caso2 = str(row.get("CASO2") or "").strip().upper()
            return SUFIJO_ORIGEN.get(caso2[-1:], "") if caso2 else ""

        df["ORIGEN"] = df.apply(_origen, axis=1)
        return df

    @staticmethod
    def normalize_por_origen(df: pd.DataFrame) -> pd.DataFrame:
        """HELADIO y GDR mandan Fecha y Telefono en formatos distintos
        dentro del mismo archivo:
          - HELADIO: Fecha real (llega como "AAAA-MM-DD ..." porque el
            Excel se lee como texto); Telefono de 13 dígitos ("521" + 10).
          - GDR: Fecha como texto "DD/MM/AAAA"; Telefono de 10 dígitos."""

        if "ORIGEN" not in df.columns:
            return df

        def _normaliza_fecha(row):
            valor = row.get("FECHA")
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                return valor
            if isinstance(valor, str):
                texto = valor.strip()
                try:
                    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", texto):
                        return pd.to_datetime(texto, format="%d/%m/%Y")
                    if re.match(r"\d{4}-\d{2}-\d{2}", texto):
                        return pd.to_datetime(texto, format="ISO8601")
                    return valor
                except Exception:
                    return valor
            return valor

        def _normaliza_telefono(row):
            valor = row.get("TELEFONO")
            if valor is None:
                return valor
            digitos = "".join(c for c in str(valor) if c.isdigit())
            origen = str(row.get("ORIGEN") or "").strip().upper()
            if origen == "HELADIO" and len(digitos) == 13 and digitos.startswith("521"):
                return digitos[3:]
            return digitos

        if "FECHA" in df.columns:
            df["FECHA"] = df.apply(_normaliza_fecha, axis=1)

        if "TELEFONO" in df.columns:
            df["TELEFONO"] = df.apply(_normaliza_telefono, axis=1)

        return df

    @staticmethod
    def split_serie(df: pd.DataFrame) -> pd.DataFrame:
        """Serie con el Congelador pegado ("2868653/548769"): se quita la
        parte que repite al Congelador. Si no se puede decidir, se deja
        tal cual."""

        if "SERIE" not in df.columns or "CONGELADOR" not in df.columns:
            return df

        def _limpia(row):
            serie = row.get("SERIE")
            if not isinstance(serie, str) or "/" not in serie:
                return serie

            partes = [p.strip() for p in serie.split("/") if p.strip()]
            congelador = str(row.get("CONGELADOR") or "").strip()

            partes_sin_duplicado = [p for p in partes if p != congelador]

            if len(partes_sin_duplicado) == 1:
                return partes_sin_duplicado[0]

            return serie

        df["SERIE"] = df.apply(_limpia, axis=1)
        return df
