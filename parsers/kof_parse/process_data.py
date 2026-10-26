"""Datos que KOF manda al repositorio (repository/core vía repository.gen) y
el Excel de resultado (aceptadas y rechazadas)."""

from io import BytesIO

import pandas as pd
from openpyxl import Workbook

from config.customers.kof import columns_names as col
from config.customers.kof import reglas_kof as reglas
from parsers.gen_parse.process_data import GEN_PROCESS
from parsers.kof_parse.business import MOTIVO, MOVIMIENTO_ORIGINAL, TIPO, expandir
from parsers.kof_parse.reader import ARCHIVO, FILA, HOJA
from parsers.kof_parse.sabana import distribuidora, observaciones

ACEPTADA = "ACEPTADA"
RECHAZADA = "RECHAZADA"
COLUMNAS_RESULTADO = (
    "Estado", "Motivo", "Archivo", "Hoja", "Fila", "Folio", "Tipo de servicio",
    "Movimiento KOF", "Serie", "Modelo", "Activo/SAP", "ID detallista",
)


def _v(registro, columna):
    valor = registro.get(columna)
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    return valor


def estatus_os(os_valor) -> str:
    """Misma regla que Danone/Penafiel/Heineken: vacía -> REJECTED; con
    [RECHAZADO] o sin prefijo 403 -> PENDING; resto -> ACCEPTED."""
    texto = "" if os_valor is None else str(os_valor).strip()
    if not texto:
        return "REJECTED"
    if "[RECHAZADO]" in texto.upper():
        return "PENDING"
    if not texto.lstrip("0").startswith("403"):
        return "PENDING"
    return "ACCEPTED"


class KOF_PROCESS:

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self._gen = GEN_PROCESS(duckConn)

    def fill_email_model(self, mail, customer=reglas.CUSTOMER):
        return self._gen.fill_email_model(mail, customer)

    @staticmethod
    def process_email_request_global(rows):
        return GEN_PROCESS.process_email_request_global(rows)

    @staticmethod
    def prepare_data_request(request_code, aceptados, customer=reglas.CUSTOMER) -> dict:
        total = len(aceptados)
        return {
            "request_code": request_code,
            "customer": customer,
            "status": "IN_PROGRESS",
            "priority": reglas.PRIORIDAD,
            "total_coolers": total,
            "pending_coolers": total,
            "completed_coolers": 0,
            "failed_coolers": 0,
            "assigned_to": "NA",
        }

    @staticmethod
    def prepare_data_cooler(request_code, aceptados, primera_fila=1) -> list[dict]:
        coolers = []
        for i, r in enumerate(aceptados):
            origen = " | ".join(
                f"{etiqueta}: {valor}" for etiqueta, valor in (
                    ("Archivo", _v(r, ARCHIVO)), ("Hoja", _v(r, HOJA)), ("Fila", _v(r, FILA)),
                    ("Distribuidora", distribuidora(r) or None),
                ) if valor is not None
            )
            coolers.append({
                "request_code": request_code,
                "row_number": primera_fila + i,

                "status": "PENDING",
                "rejection_reason": None,
                "prioridad": None,
                "folio": _v(r, col.FOLIO),
                "ticket_solicitud": None,
                "assigned_to": None,
                "gestion_observaciones": origen or None,
                "fecha_asignacion": None,
                "fecha_atencion": None,
                "fecha_completado": None,

                "id_cliente": _v(r, col.ID_CLIENTE),
                "fecha_solicitud": _v(r, col.FECHA),
                "modelo": _v(r, col.MODELO),
                "serie_fabricante": _v(r, col.SERIE),
                "serie_dnn_bnf": _v(r, col.ACTIVO),
                "tipo_servicio": r[TIPO],
                "canal": None,
                "region": None,
                "plaza": _v(r, col.CEDIS) or _v(r, col.PLAZA),
                "razon_social": _v(r, col.RAZON_SOCIAL),
                "direccion": _v(r, col.DIRECCION),
                "cp": _v(r, col.CP),
                "ciudad": _v(r, col.CIUDAD),
                "colonia": _v(r, col.COLONIA),
                "latitud": None,
                "longitud": None,
                "ruta": None,
                "telefono_1": _v(r, col.TELEFONO),
                "telefono_2": None,
                "comentarios": observaciones(r) or None,
                "cbu": reglas.CBU,
                "cliente": _v(r, col.CLIENTE_CONCATENADO),
                "os": _v(r, col.OS),
            })
        return coolers

    @staticmethod
    def prepare_cooler_update(df: pd.DataFrame) -> pd.DataFrame:
        """Conciliación outbound por la columna OS. Se aplica el mismo
        desdoble que al entrar (un Cambio de Equipo con una OS concilia la
        instalación y el retiro); filas sin serie no se concilian."""
        filas = []
        registros = [r for fila in df.to_dict("records") for r in expandir(fila)]
        for registro in registros:
            serie = _v(registro, col.SERIE)
            if registro.get(MOTIVO) or not serie:
                continue
            os_valor = _v(registro, col.OS)
            filas.append({
                "serial_number": str(serie),
                "serial_dnn": str(_v(registro, col.ACTIVO) or ""),
                "os": "" if os_valor is None else str(os_valor).strip(),
                "status": estatus_os(os_valor),
            })
        return pd.DataFrame(filas, columns=["serial_number", "serial_dnn", "os", "status"])

    @staticmethod
    def resultado_xlsx(request_code, aceptados, rechazados) -> tuple[str, bytes]:
        """Excel de respuesta con cada registro aceptado y rechazado."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Resultado"
        ws.append(list(COLUMNAS_RESULTADO))
        for estado, registros in ((ACEPTADA, aceptados), (RECHAZADA, rechazados)):
            for r in registros:
                ws.append([
                    estado, _v(r, MOTIVO), _v(r, ARCHIVO), _v(r, HOJA), _v(r, FILA),
                    _v(r, col.FOLIO), r.get(TIPO), _v(r, MOVIMIENTO_ORIGINAL),
                    _v(r, col.SERIE), _v(r, col.MODELO), _v(r, col.ACTIVO), _v(r, col.ID_CLIENTE),
                ])
        salida = BytesIO()
        wb.save(salida)
        nombre = f"RESULTADO_KOF_{request_code}.xlsx" if request_code else "RESULTADO_KOF.xlsx"
        return nombre, salida.getvalue()
