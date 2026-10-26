"""Armado de lo que se guarda: cabecera del correo, solicitud y filas de
``cooler_request``. Mapeo de plantilla/Excel a columnas en
``repository/oxxo/consultas_postgre.py``."""

from __future__ import annotations

from parsers.danone_parse.process_data import DANONE_PROCESS
from parsers.oxxo_parse.plantillas import Mantenimiento, Seguimiento, normalizar_telefono, parsear_fecha
from config.customers.oxxo.reglas_oxxo import (
    CLIENTE_COOLER_GARANTIAS,
    CLIENTE_COOLER_MANTENIMIENTO,
    PRIORIDAD_COOLER,
    TIPO_SERVICIO_GARANTIA,
)


def _observaciones(*pares) -> str | None:
    texto = " | ".join(f"{etiqueta}: {valor}" for etiqueta, valor in pares if valor)
    return texto or None


def _fila_base() -> dict:
    return {
        "id_cliente": None, "fecha_solicitud": None, "modelo": None, "serie_fabricante": None,
        "tipo_servicio": None, "region": None, "plaza": None, "razon_social": None,
        "direccion": None, "cp": None, "ciudad": None, "colonia": None, "telefono_1": None,
        "comentarios": None, "prioridad": PRIORIDAD_COOLER, "folio": None,
        "ticket_solicitud": None, "gestion_observaciones": None,
    }


class OXXO_PROCESS:

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self._danone_process = DANONE_PROCESS(duckConn)

    # Genéricos de DANONE_PROCESS, reusados tal cual (como Holanda).
    def fill_email_model(self, email, customer):
        return self._danone_process.fill_email_model(email, customer=customer)

    process_email_request_global = staticmethod(DANONE_PROCESS.process_email_request_global)

    @staticmethod
    def prepare_data_request(request_code, customer, total):
        return {
            "request_code": request_code,
            "customer": customer,
            "status": "IN_PROGRESS",
            "priority": "MEDIUM",
            "total_coolers": total,
            "pending_coolers": total,
            "completed_coolers": 0,
            "failed_coolers": 0,
            "assigned_to": "NA",
        }

    @staticmethod
    def fila_mantenimiento(d: Mantenimiento) -> dict:
        """Folio = ticket; sin serie ni modelo. La plantilla no separa plaza
        y nombre de tienda: van juntos en razon_social."""
        fila = _fila_base()
        fila.update(
            cliente=CLIENTE_COOLER_MANTENIMIENTO,
            folio=d.ticket,
            id_cliente=d.cr,
            razon_social=d.tienda,
            direccion=d.direccion,
            region=d.region,
            tipo_servicio=d.categoria,
            comentarios=d.falla,
            gestion_observaciones=_observaciones(
                ("Motivo", d.motivo),
                ("Representante propietario", d.propietario),
                ("Prioridad", d.prioridad),
            ),
        )
        return fila

    @staticmethod
    def fila_garantia(d: Seguimiento) -> dict:
        """OS nueva de garantía desde 'Seguimiento a Folio' que no existía."""
        fila = _fila_base()
        fila.update(
            cliente=CLIENTE_COOLER_GARANTIAS,
            folio=d.folio,
            ticket_solicitud=d.folio_mantenimiento,
            id_cliente=d.cr,
            fecha_solicitud=d.fecha,
            plaza=d.plaza,
            modelo=d.modelo,
            serie_fabricante=d.serie,
            tipo_servicio=TIPO_SERVICIO_GARANTIA,
            telefono_1=d.telefono,
            direccion=d.direccion_envio,
            comentarios=d.diagnostico,
            gestion_observaciones=_observaciones(
                ("Reporta", d.reporta),
                ("Equipo", d.equipo),
                ("Marca", d.marca),
                ("Seguimiento", d.mensaje),
            ),
        )
        return fila

    @staticmethod
    def fila_excel(d: dict) -> dict:
        """Una fila del Lay Out Repare (llaves canónicas de columns_names)."""
        fila = _fila_base()
        fila.update(
            cliente=CLIENTE_COOLER_GARANTIAS,
            folio=(d.get("FOLIO") or "").upper() or None,
            id_cliente=d.get("ID CLIENTE"),
            modelo=d.get("MODELO"),
            serie_fabricante=d.get("SERIE"),
            tipo_servicio=d.get("TIPO DE SERVICIO") or TIPO_SERVICIO_GARANTIA,
            region=d.get("REGION"),
            plaza=d.get("PLAZA"),
            razon_social=d.get("RAZON SOCIAL"),
            direccion=d.get("DIRECCION"),
            cp=d.get("CP"),
            ciudad=d.get("MUNICIPIO"),
            colonia=d.get("COLONIA"),
            telefono_1=normalizar_telefono(d.get("TELEFONO")),
            fecha_solicitud=parsear_fecha(d.get("FECHA")),
            comentarios=d.get("FALLA"),
        )
        return fila
