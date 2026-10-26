from parsers.core.correo import detectar_tipo_correo as core_detectar_tipo_correo
import tempfile

from config.config_general.palabras_reser import palabras_reservadas
from io import BytesIO
from pathlib import Path
import pandas as pd
import unicodedata
import traceback
import base64
import shutil


class GEN_READER:
    EXCEL_EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".ods")

    @staticmethod
    async def get_adjuntos(
        client,
        user_id,
        mail_id,
        debug=False,
        output_dir="Documentos_Adjuntos",
        copy_ori=False,
    ):

        output_path = Path(output_dir)

        if debug:
            shutil.rmtree(output_path, ignore_errors=True)

        if debug or copy_ori:
            output_path.mkdir(parents=True, exist_ok=True)

        attachments = await (
            client.users
            .by_user_id(user_id)
            .messages
            .by_message_id(mail_id)
            .attachments
            .get()
        )

        if not attachments.value:
            return []

        tables = []

        for attachment in attachments.value:
            name = getattr(attachment, "name", "") or ""

            # Ignorar adjuntos sin contenido
            if not hasattr(attachment, "content_bytes") or not attachment.content_bytes:
                continue

            # Ignorar archivos temporales de Excel
            if name.startswith("~$"):
                continue

            # Solo aceptar archivos Excel
            extension = Path(name).suffix.lower()
            if extension not in GEN_READER.EXCEL_EXTENSIONS:
                continue

            content = attachment.content_bytes

            # Algunos archivos llegan codificados en Base64
            if content.startswith(b"UEs"):
                content = base64.b64decode(content)

            if debug or copy_ori:
                with open(output_path / Path(name).name, "wb") as file:
                    file.write(content)

            # Leer únicamente la primera hoja visible
            excel_file = pd.ExcelFile(BytesIO(content))
            if excel_file.engine == "openpyxl":
                visible_sheets = [
                    sheet.title
                    for sheet in excel_file.book.worksheets
                    if sheet.sheet_state == "visible"
                ]
            elif excel_file.engine == "xlrd":
                visible_sheets = [
                    sheet.name
                    for sheet in excel_file.book.sheets()
                    if sheet.visibility == 0
                ]
            else:
                visible_sheets = excel_file.sheet_names

            if not visible_sheets:
                continue

            df = excel_file.parse(sheet_name=visible_sheets[0], dtype=str)

            tables.append({"name": name, "dataframe": df})

        return tables

    @staticmethod
    def normalize(text: str) -> str:
        text = str(text).strip().upper()

        text = unicodedata.normalize("NFKD", text)
        text = "".join(
            c for c in text
            if not unicodedata.combining(c)
        )

        return " ".join(text.split())

    
    @staticmethod
    async def download_original_files(
        client,
        user_id,
        mail_id,
        prefix="penafiel",
    ):
        output_root = Path("Documentos_Adjuntos")
        output_root.mkdir(parents=True, exist_ok=True)
        output_dir = Path(
            tempfile.mkdtemp(prefix=f"{prefix}_", dir=output_root)
        )

        try:
            files = await GEN_READER.get_adjuntos(
                client,
                user_id,
                mail_id,
                copy_ori=True,
                output_dir=str(output_dir),
            )
        except Exception as e:
            print(f"[ERROR] No se pudieron descargar los Excel originales: {e}")
            GEN_READER._remove_temporary_directory(output_dir)
            raise

        if not files:
            GEN_READER._remove_temporary_directory(output_dir)
            return []

        return [
            (archivo["name"], str(output_dir / Path(archivo["name"]).name))
            for archivo in files
        ]

    @staticmethod
    def cleanup_original_files(temporary_files):
        output_root = Path("Documentos_Adjuntos").resolve()
        directories = {Path(path).parent.resolve() for _, path in temporary_files}

        for directory in directories:
            if (
                directory.parent != output_root
                or not directory.name.startswith(("penafiel_", "danone_"))
            ):
                print(
                    f"[WARN] Se omite la limpieza de directorio temporal "
                    f"fuera del área de descargas: {directory}"
                )
                continue

            GEN_READER._remove_temporary_directory(directory)

    @staticmethod
    def _remove_temporary_directory(directory):
        try:
            shutil.rmtree(directory)
        except FileNotFoundError:
            pass
        except OSError as error:
            print(
                f"[ERROR] No se pudo eliminar el directorio temporal "
                f"{directory}: {error}"
            )

    detectar_tipo_correo = staticmethod(core_detectar_tipo_correo)
