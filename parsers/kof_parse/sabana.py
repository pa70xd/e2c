"""Sábanas de KOF (movimiento y ruta) en DuckDB, con las plantillas
genéricas, para que ``Excel_Ingestion.get_excelv2_attachment`` las adjunte."""

from pathlib import Path

import pandas as pd

from config.customers.kof import columns_names as col
from config.customers.kof import reglas_kof as reglas
from parsers.kof_parse.business import MOVIMIENTO_ORIGINAL, SABANA, TIPO

SQL_SABANA = {
    reglas.SABANA_MOVIMIENTO: ("sabana_movimiento", Path("config/config_general/querys/generic_sabana_movimientos.sql")),
    reglas.SABANA_RUTA: ("sabana_ruta", Path("config/config_general/querys/generic_sabana_ruta.sql")),
}


def _t(registro, columna):
    valor = registro.get(columna)
    return "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor)


def distribuidora(registro) -> str:
    """ID DISTRIBUIDOR | CEDIS (KOF no trae CP para buscarla en el catálogo)."""
    return " | ".join(p for p in (_t(registro, col.ID_DISTRIBUIDOR), _t(registro, col.CEDIS)) if p)


def observaciones(registro) -> str:
    partes = [
        ("Tipo", registro.get(TIPO)),
        ("Movimiento KOF", registro.get(MOVIMIENTO_ORIGINAL)),
        ("Folio", registro.get(col.FOLIO)),
        ("Falla", registro.get(col.FALLA)),
        ("Solicitud", registro.get(col.SOLICITUD)),
        ("Obs", registro.get(col.OBSERVACIONES)),
    ]
    if registro.get(TIPO) == reglas.PROYECTO_ESPECIAL:
        # La sábana de ruta no tiene Id_Servicio: va en observaciones.
        partes.insert(1, ("Id servicio", reglas.ID_SERVICIO_AREAS_GENERALES))
    return " | ".join(f"{etiqueta}: {valor}" for etiqueta, valor in partes if valor)


def _comunes(r) -> dict:
    return {
        "Distribuidora": distribuidora(r),
        "Categoria": "",
        "Linea": "",
        "Modelo": _t(r, col.MODELO),
        "Numero_Activo": _t(r, col.ACTIVO),
        "Serie": _t(r, col.SERIE),
        "Canal": "Sin Canal",
        "Hora_Atencion": "",
        "Observaciones": observaciones(r),
        "Numero_Cliente": _t(r, col.ID_CLIENTE),
        "Nombre_PDV": _t(r, col.RAZON_SOCIAL),
        "Calle": _t(r, col.DIRECCION),
        "Numero": "",
        "Entre_Calle1": "",
        "Entre_Calle2": "",
        "Colonia": _t(r, col.COLONIA),
        "Municipio": _t(r, col.CIUDAD),
        "Codigo_Postal": _t(r, col.CP),
        "Latitud": "",
        "Longitud": "",
        "Nombre_Contacto_PDV": "",
    }


def fila_movimiento(r) -> dict:
    fila = _comunes(r)
    fila.update({
        "Numero_Puertas": "",
        "Imagen": "",
        "Tipo_Servicio": r[TIPO],
        "Id_Servicio": "",
        "Tipo_Actividad": "",
        "Actividad": "",
        "Datos_Prospeccion": "NA",
        "Tipo_Orden": "",
        "Telefono_Fax": _t(r, col.TELEFONO),
        "Correo_Electronico": "",
        "Distribuidora_Puesto_Trabajo": distribuidora(r),
    })
    return fila


def fila_ruta(r) -> dict:
    fila = _comunes(r)
    fila.update({
        "Prioridad": "",
        "Folio": _t(r, col.FOLIO),
        "Ticket_Solicitud": "",
        "Correo_Electronico_1": "",
        "Telefono_Fax_1": _t(r, col.TELEFONO),
        "Telefono_Fax_2": "",
        "Correo_Electronico_2": "",
    })
    return fila


class KOF_SABANA:

    def __init__(self, duckConn):
        self.duckConn = duckConn

    def fill(self, aceptados: list[dict]) -> list[str]:
        """Crea y llena las sábanas que apliquen. Regresa sus nombres."""
        tablas = []
        for sabana, armar in ((reglas.SABANA_MOVIMIENTO, fila_movimiento), (reglas.SABANA_RUTA, fila_ruta)):
            registros = [r for r in aceptados if r[SABANA] == sabana]
            if not registros:
                continue
            tabla, sql = SQL_SABANA[sabana]
            self.duckConn.execute(f'DROP TABLE IF EXISTS "{tabla}"')
            self.duckConn.execute(sql.read_text(encoding="utf-8"))
            columnas = [c[0].strip() for c in self.duckConn.execute(f'DESCRIBE "{tabla}"').fetchall()]
            df = pd.DataFrame([armar(r) for r in registros]).reindex(columns=columnas).fillna("")
            self.duckConn.register("kof_tmp_sabana", df)
            try:
                self.duckConn.execute(f'INSERT INTO "{tabla}" SELECT * FROM kof_tmp_sabana')
            finally:
                self.duckConn.unregister("kof_tmp_sabana")
            tablas.append(tabla)
        return tablas
