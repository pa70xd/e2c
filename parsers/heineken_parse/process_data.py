from zoneinfo import ZoneInfo

from config.customers.heineken.columns_names import COL_FILA_EXCEL
from config.customers.heineken.reglas_heineken import CUSTOMER, FLUJO_D2D
from parsers.danone_parse.process_data import DANONE_PROCESS

ZONA_MX = ZoneInfo("America/Mexico_City")
ACTIVO_RELLENO = "123456789"


def _c(nombre: str) -> str:
    return f'"{nombre}"'


def _etiquetas(partes: list[tuple[str, str]]) -> str:
    """Etiqueta: valor | ... (omite vacíos)."""
    piezas = ", ".join(f"'{etiqueta}: ' || {expr}" for etiqueta, expr in partes)
    return f"NULLIF(CONCAT_WS(' | ', {piezas}), '')"


_ENTRE_CALLES = f"NULLIF(CONCAT_WS(' y ', {_c('ENTRE CALLE')}, {_c('Y CALLE')}), '')"

# Columnas de cooler_request (parámetros de los SQL de repository/heineken).
_CAMPOS_D2D = {
    "id_cliente": _c("CLIENTE DETALLISTA"),
    "modelo": _c("MODELO"),
    "serie_fabricante": _c("SERIE"),
    "serie_dnn_bnf": f"NULLIF({_c('ACTIVO')}, '{ACTIVO_RELLENO}')",
    "tipo_servicio": _c("FALLA"),
    # Solo cuando la columna trae el texto de canal y no el código del puesto.
    "canal": f"CASE WHEN UPPER(TRIM({_c('DISTRIBUIDORA')})) <> {_c('PUESTO')} THEN {_c('DISTRIBUIDORA')} END",
    "region": "NULL",
    "plaza": _c("SUCURSAL"),
    "razon_social": _c("RAZON SOCIAL"),
    "direccion": _c("CALLE Y NUMERO"),
    "cp": _c("CP"),
    "ciudad": _c("MUNICIPIO"),
    "colonia": _c("COLONIA"),
    "latitud": "NULL",
    "longitud": "NULL",
    "telefono_1": _c("TELEFONO"),
    "comentarios": _c("OBSERVACIONES"),
    "cbu": _c("PUESTO"),
    "os": _c("OS"),
    "folio": "NULL",
    "ticket_solicitud": "NULL",
    "gestion_observaciones": _etiquetas([
        ("Responsable", _c("RESPONSABLE")), ("Horario", _c("HORARIO")),
        ("Entre calles", _ENTRE_CALLES), ("Tecnico", _c("TECNICO")),
        ("Reporte imagen", _c("REPORTE IMAGEN")),
    ]),
}

_CAMPOS_RUTA = {
    "id_cliente": _c("NUMERO CLIENTE"),
    "modelo": _c("MODELO"),
    "serie_fabricante": _c("SERIE"),
    "serie_dnn_bnf": "NULL",
    "tipo_servicio": _c("TIPO DE MOVIMIENTO"),
    "canal": _c("CANAL"),
    "region": _c("REGION"),
    "plaza": "NULL",
    "razon_social": _c("NOMBRE PDV"),
    "direccion": f"NULLIF(CONCAT_WS(' ', {_c('CALLE')}, {_c('NUMERO')}), '')",
    "cp": _c("CP"),
    "ciudad": _c("MUNICIPIO"),
    "colonia": _c("COLONIA"),
    "latitud": _c("LATITUD"),
    "longitud": _c("LONGITUD"),
    "telefono_1": _c("TELEFONO"),
    "comentarios": _c("FALLA"),
    "cbu": "NULL",
    "os": _c("OS"),
    "folio": _c("ORDEN"),
    "ticket_solicitud": _c("AVISO"),
    "gestion_observaciones": _etiquetas([
        ("Contacto", _c("CONTACTO")), ("Horario", _c("HORARIO")),
        ("Entre calles", _ENTRE_CALLES), ("Notas", _c("SUCURSAL")),
        ("Cliente", _c("CLIENTE")), ("Caso", _c("NUMERO CASO")),
        ("Fecha venta/factura", _c("FECHA VENTA")),
    ]),
}


def estatus_os(os_valor: str | None) -> tuple[str, str | None]:
    """(status, motivo) de una OS de la respuesta: 403... aceptada, texto pendiente, vacía rechazada."""
    if not os_valor:
        return "REJECTED", None
    limpio = os_valor.strip().lstrip("0")
    if limpio.isdigit() and limpio.startswith("403"):
        return "ACCEPTED", None
    return "PENDING", os_valor.strip()


class HEINEKEN_PROCESS:

    def __init__(self, duckConn):
        self.duckConn = duckConn
        self._danone_process = DANONE_PROCESS(duckConn)

    def fill_email_model(self, email):
        return self._danone_process.fill_email_model(email, customer=CUSTOMER)

    process_email_request_global = staticmethod(DANONE_PROCESS.process_email_request_global)

    def prepare_data_request(self, request_code: str, tabla: str) -> dict:
        total = self.duckConn.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
        return {
            "request_code": request_code,
            "customer": CUSTOMER,
            "status": "IN_PROGRESS",
            "priority": "MEDIUM",
            "total_coolers": total,
            "pending_coolers": total,
            "completed_coolers": 0,
            "failed_coolers": 0,
            "assigned_to": "NA",
        }

    def prepare_data_coolers(self, tabla: str, flujo: str, mail) -> list[dict]:
        """Filas válidas para DB_HEINEKEN.guardar_casos, en el orden del archivo."""
        campos = _CAMPOS_D2D if flujo == FLUJO_D2D else _CAMPOS_RUTA
        cursor = self.duckConn.execute(f"""
            SELECT {", ".join(f"{expr} AS {nombre}" for nombre, expr in campos.items())}
            FROM "{tabla}"
            ORDER BY CAST("{COL_FILA_EXCEL}" AS INTEGER)
        """)
        columnas = [d[0] for d in cursor.description]
        fecha = mail.received_date_time.astimezone(ZONA_MX) if mail.received_date_time else None
        return [
            {**dict(zip(columnas, fila)), "fecha_solicitud": fecha}
            for fila in cursor.fetchall()
        ]

    def leer_respuesta(self, tabla: str, flujo: str) -> list[dict]:
        """Filas de la respuesta del operador con su OS, listas para DB_HEINEKEN.conciliar."""
        if flujo == FLUJO_D2D:
            extra = (f'{_c("CLIENTE DETALLISTA")} AS cliente, '
                     f"NULLIF({_c('ACTIVO')}, '{ACTIVO_RELLENO}') AS activo, "
                     f'{_c("FALLA")} AS falla, NULL AS orden')
        else:
            extra = f'NULL AS cliente, NULL AS activo, NULL AS falla, {_c("ORDEN")} AS orden'

        cursor = self.duckConn.execute(f"""
            SELECT {_c("SERIE")} AS serie, {_c("OS")} AS os, {extra}
            FROM "{tabla}"
            WHERE ({_c("SERIE")} IS NOT NULL OR {_c("OS")} IS NOT NULL)
              AND COALESCE({_c("OS")}, '') NOT LIKE '[RECHAZADO]%'
            ORDER BY CAST("{COL_FILA_EXCEL}" AS INTEGER)
        """)
        columnas = [d[0] for d in cursor.description]
        filas = []
        for valores in cursor.fetchall():
            fila = dict(zip(columnas, valores))
            fila["status"], fila["motivo"] = estatus_os(fila["os"])
            filas.append(fila)
        return filas
