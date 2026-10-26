"""Pre-sábanas de Imbera/Torrey sobre los templates generales: ruta
(sabana_ruta) e instalación (sabana_movimiento). Primero las filas
válidas y después las rechazadas, con el MOTIVO al inicio de
Observaciones (igual que Holanda)."""

from __future__ import annotations

from pathlib import Path

from parsers.imbera_parse.business import TABLA_RECHAZADAS, TABLA_VALIDAS

SQL_SABANA_RUTA = Path("config/config_general/querys/generic_sabana_ruta.sql")
SQL_SABANA_MOVIMIENTO = Path("config/config_general/querys/generic_sabana_movimientos.sql")


def _v(columna: str) -> str:
    return f"""NULLIF(TRIM(CAST("{columna}" AS VARCHAR)), '')"""


def _observaciones(rechazada: bool) -> str:
    partes = [_v("MOTIVO")] if rechazada else []
    partes += [
        f"'Falla: ' || {_v('FALLA')}",
        "CASE WHEN \"GARANTIA\" = 'SI' THEN 'Garantía: SI (' || \"SENALES_GARANTIA\" || ')' END",
        f"'Sub-cliente: ' || {_v('SUBCLIENTE')}",
        f"'Plaza: ' || {_v('PLAZA')}",
        f"'Fecha factura: ' || {_v('FECHA FACTURA')}",
        f"'Cliente OS: ' || {_v('CLIENTE_OS')}",
    ]
    return f"NULLIF(CONCAT_WS(' | ', {', '.join(partes)}), '')"


def _mapeo_comun(rechazada: bool) -> dict[str, str]:
    return {
        "Distribuidora": _v("NUM DISTRIBUIDOR"),
        "Modelo": _v("MODELO"),
        "Serie": _v("SERIE"),
        "Canal": _v("CANAL"),
        "Observaciones": _observaciones(rechazada),
        "Numero_Cliente": _v("NUM CLIENTE"),
        "Calle": _v("CALLE"),
        "Numero": _v("NUMERO"),
        "Colonia": _v("COLONIA"),
        "Municipio": _v("MUNICIPIO"),
        "Codigo_Postal": _v("CP"),
        "Latitud": _v("LATITUD"),
        "Longitud": _v("LONGITUD"),
        "Nombre_Contacto_PDV": _v("CONTACTO NOMBRE"),
    }


def _insert(tabla_destino: str, mapeo: dict[str, str], origen: str, where: str) -> str:
    return f"""
        INSERT INTO {tabla_destino} ({", ".join(mapeo)})
        SELECT {", ".join(mapeo.values())}
        FROM "{origen}"
        WHERE {where}
        ORDER BY rowid
    """


class LAYOUT_SABANA:

    def __init__(self, duckConn):
        self.duckConn = duckConn

    def fill_sabana_ruta(self):
        self.duckConn.execute("DROP TABLE IF EXISTS sabana_ruta")
        self.duckConn.execute(SQL_SABANA_RUTA.read_text(encoding="utf-8"))
        for origen, rechazada in ((TABLA_VALIDAS, False), (TABLA_RECHAZADAS, True)):
            mapeo = {
                **_mapeo_comun(rechazada),
                "Folio": _v("FOLIO"),
                "Ticket_Solicitud": _v("TICKET"),
                "Telefono_Fax_1": _v("CONTACTO TELEFONO"),
                "Correo_Electronico_1": _v("CONTACTO CORREO"),
            }
            self.duckConn.execute(_insert("sabana_ruta", mapeo, origen, "\"TIPO_SERVICIO\" = 'RUTA'"))
        return "sabana_ruta"

    def fill_sabana_movimiento(self):
        self.duckConn.execute("DROP TABLE IF EXISTS sabana_movimiento")
        self.duckConn.execute(SQL_SABANA_MOVIMIENTO.read_text(encoding="utf-8"))
        for origen, rechazada in ((TABLA_VALIDAS, False), (TABLA_RECHAZADAS, True)):
            mapeo = {
                **_mapeo_comun(rechazada),
                "Tipo_Servicio": _v("TIPO_SERVICIO"),
                "Id_Servicio": _v("FOLIO"),
                "Telefono_Fax": _v("CONTACTO TELEFONO"),
                "Correo_Electronico": _v("CONTACTO CORREO"),
            }
            self.duckConn.execute(_insert("sabana_movimiento", mapeo, origen, "\"TIPO_SERVICIO\" <> 'RUTA'"))
        return "sabana_movimiento"
