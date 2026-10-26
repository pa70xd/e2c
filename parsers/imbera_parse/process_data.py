"""Datos para el repositorio (Imbera y Torrey): email_request, filas de
cooler_request y pares serie/OS del outbound."""

from __future__ import annotations

from config.customers.imbera import reglas_imbera as R
from parsers.danone_parse.process_data import DANONE_PROCESS
from parsers.imbera_parse.business import TABLA_RECHAZADAS, TABLA_VALIDAS
from parsers.imbera_parse.lector import normalizar
from parsers.imbera_parse.perfil import PerfilLayout


def _limpio(valor):
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


def _observaciones(fila: dict) -> str | None:
    partes = []
    if fila.get("GARANTIA") == "SI":
        partes.append(f"Garantía: SI ({fila.get('SENALES_GARANTIA')})")
    for etiqueta, columna in (
        ("Variante", "VARIANTE_RUTA"),
        ("Distribuidor", "NUM DISTRIBUIDOR"),
        ("Fecha factura", "FECHA FACTURA"),
        ("Estado", "ESTADO"),
    ):
        if _limpio(fila.get(columna)):
            partes.append(f"{etiqueta}: {_limpio(fila.get(columna))}")
    return " | ".join(partes) or None


def _direccion(fila: dict) -> str | None:
    return _limpio(" ".join(p for p in (_limpio(fila.get("CALLE")), _limpio(fila.get("NUMERO"))) if p))


class LAYOUT_PROCESS:

    def __init__(self, duckConn, perfil: PerfilLayout):
        self.duckConn = duckConn
        self.perfil = perfil
        self._danone_process = DANONE_PROCESS(duckConn)

    process_email_request_global = staticmethod(DANONE_PROCESS.process_email_request_global)

    def fill_email_model(self, email):
        return self._danone_process.fill_email_model(email, customer=self.perfil.customer)

    def _filas(self) -> list[dict]:
        filas = []
        for tabla in (TABLA_VALIDAS, TABLA_RECHAZADAS):
            cursor = self.duckConn.execute(f'SELECT * FROM "{tabla}" ORDER BY rowid')
            columnas = [d[0] for d in cursor.description]
            filas += [dict(zip(columnas, f)) for f in cursor.fetchall()]
        return filas

    def prepare_data_request(self, request_code):
        total = len(self._filas())
        validas = self.duckConn.execute(f'SELECT COUNT(*) FROM "{TABLA_VALIDAS}"').fetchone()[0]
        return {
            "request_code": request_code,
            "customer": self.perfil.customer,
            "status": "IN_PROGRESS",
            "priority": R.PRIORIDAD,
            "total_coolers": total,
            "pending_coolers": validas,
            "completed_coolers": 0,
            "failed_coolers": 0,
            "assigned_to": "NA",
        }

    def prepare_data_coolers(self, request_code) -> list[dict]:
        """Una fila por equipo para send_email_coolers / insert_update_cooler:
        las válidas PENDING y las rechazadas REJECTED con su motivo.

        Mapeo a cooler_request (por analogía, pendiente de revisión):
          NUM CLIENTE -> id_cliente     SERIE -> serie_fabricante
          FALLA -> comentarios          MUNICIPIO -> ciudad
          CANAL -> canal                PLAZA (asunto) -> plaza
          SUBCLIENTE -> cbu             CLIENTE_OS -> cliente
          FOLIO IMB-/REP- -> folio      OS del asunto -> ticket_solicitud
          TIPO_SERVICIO -> tipo_servicio
          VARIANTE_RUTA -> ruta
          CONTACTO TELEFONO -> telefono_1
          gestion_observaciones <- garantía (señales), variante,
              distribuidor, fecha de factura, estado.
        El nombre de quien recibe (PII) solo va en la pre-sábana."""
        filas = []
        for numero, fila in enumerate(self._filas(), start=1):
            motivo = _limpio(fila.get("MOTIVO"))
            filas.append({
                "request_code": request_code,
                "row_number": numero,
                "status": "REJECTED" if motivo else "PENDING",
                "rejection_reason": motivo,
                "prioridad": R.PRIORIDAD,
                "folio": _limpio(fila.get("FOLIO")),
                "ticket_solicitud": _limpio(fila.get("TICKET")),
                "assigned_to": None,
                "gestion_observaciones": _observaciones(fila),
                "fecha_asignacion": None,
                "fecha_atencion": None,
                "fecha_completado": None,
                "id_cliente": _limpio(fila.get("NUM CLIENTE")),
                "fecha_solicitud": None,
                "modelo": _limpio(fila.get("MODELO")),
                "serie_fabricante": _limpio(fila.get("SERIE")),
                "serie_dnn_bnf": None,
                "tipo_servicio": _limpio(fila.get("TIPO_SERVICIO")),
                "canal": _limpio(fila.get("CANAL")),
                "region": None,
                "plaza": _limpio(fila.get("PLAZA")),
                "razon_social": None,
                "direccion": _direccion(fila),
                "cp": _limpio(fila.get("CP")),
                "ciudad": _limpio(fila.get("MUNICIPIO")),
                "colonia": _limpio(fila.get("COLONIA")),
                "latitud": _limpio(fila.get("LATITUD")),
                "longitud": _limpio(fila.get("LONGITUD")),
                "ruta": _limpio(fila.get("VARIANTE_RUTA")),
                "telefono_1": _limpio(fila.get("CONTACTO TELEFONO")),
                "telefono_2": None,
                "comentarios": _limpio(fila.get("FALLA")),
                "cbu": _limpio(fila.get("SUBCLIENTE")),
                "cliente": _limpio(fila.get("CLIENTE_OS")),
                "os": None,
            })
        return filas

    def resumen(self) -> tuple[list[dict], list[dict]]:
        """(aceptadas, rechazadas) para la respuesta: fila de Excel, serie,
        modelo, cliente de la OS, garantía y motivo. Sin PII."""
        aceptadas, rechazadas = [], []
        for fila in self._filas():
            dato = {
                "fila": fila.get("_FILA_EXCEL"),
                "serie": _limpio(fila.get("SERIE")),
                "modelo": _limpio(fila.get("MODELO")),
                "cliente": _limpio(fila.get("CLIENTE_OS")),
                "garantia": fila.get("GARANTIA") == "SI",
                "motivo": _limpio(fila.get("MOTIVO")),
            }
            (rechazadas if dato["motivo"] else aceptadas).append(dato)
        return aceptadas, rechazadas

    def leer_series_y_os(self, table_name) -> list[tuple[str, str]]:
        """Outbound con Excel: pares (serie, OS) con OS no vacía ni
        [RECHAZADO]. Sin columna OS no hay nada que conciliar."""
        filas = self.duckConn.execute(f'SELECT "SERIE", "OS" FROM "{table_name}" ORDER BY rowid').fetchall()
        pares = []
        for serie, os_value in filas:
            serie, os_value = _limpio(serie), _limpio(os_value)
            if serie and os_value and not normalizar(os_value).startswith("[RECHAZADO]"):
                pares.append((serie, os_value))
        return pares
