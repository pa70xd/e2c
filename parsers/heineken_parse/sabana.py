from pathlib import Path

from config.customers.heineken.reglas_heineken import (
    FLUJO_D2D, CANAL_SIN_CANAL, DISTRIBUIDORA_RUTA,
)

SQL_SABANA_MOVIMIENTO = Path("config/config_general/querys/generic_sabana_movimientos.sql")
SQL_SABANA_RUTA = Path("config/config_general/querys/generic_sabana_ruta.sql")

ACTIVO_RELLENO = "123456789"
COLUMNAS_GENERADAS = ("CP_GEN", "COLONIA_GEN", "CIUDAD_GEN", "ESTADO_GEN", "PAIS_GEN")


def _col(nombre: str) -> str:
    return f'"{nombre}"'


def _lit(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def _observaciones(partes: list[tuple[str, str]], rechazada: bool) -> str:
    """[MOTIVO |] Etiqueta: valor | ... (omite vacíos)."""
    piezas = [_col("MOTIVO")] if rechazada else []
    piezas += [f"{_lit(etiqueta + ': ')} || {_col(columna)}" for etiqueta, columna in partes]
    return f"NULLIF(CONCAT_WS(' | ', {', '.join(piezas)}), '')"


class HEINEKEN_SABANA:

    def __init__(self, duckConn):
        self.duckConn = duckConn

    def _mapeo_movimiento(self, rechazada: bool) -> dict:
        calle_numero = _col("CALLE Y NUMERO")
        return {
            "Distribuidora": _col("DISTRIBUIDORA_CAT"),
            "Categoria": _col("CATEGORIA"),
            "Linea": _col("LINEA"),
            "Modelo": _col("MODELO"),
            "Numero_Activo": f"NULLIF({_col('ACTIVO')}, {_lit(ACTIVO_RELLENO)})",
            "Serie": _col("SERIE"),
            "Canal": _lit(CANAL_SIN_CANAL),
            "Hora_Atencion": _col("HORARIO"),
            "Observaciones": _observaciones([
                ("Falla", "FALLA"), ("Obs", "OBSERVACIONES"),
                ("Tecnico", "TECNICO"), ("Reporte imagen", "REPORTE IMAGEN"),
            ], rechazada),
            "Tipo_Servicio": _col("TIPO_SERVICIO"),
            "Id_Servicio": _col("ID_SERVICIO"),
            "Tipo_Actividad": _col("TIPO_ACTIVIDAD"),
            "Actividad": _col("ACTIVIDAD"),
            "Datos_Prospeccion": "'NA'",
            "Numero_Cliente": _col("CLIENTE DETALLISTA"),
            "Nombre_PDV": _col("RAZON SOCIAL"),
            # En D2D "CALLE Y NUMERO" solo trae el nombre de la calle ("Sur 24", "Calle 13").
            "Calle": calle_numero,
            "Numero": "'SN'",
            "Entre_Calle1": _col("ENTRE CALLE"),
            "Entre_Calle2": _col("Y CALLE"),
            "Colonia": _col("COLONIA"),
            "Municipio": _col("MUNICIPIO"),
            "Codigo_Postal": _col("CP"),
            "Telefono_Fax": _col("TELEFONO"),
            "Nombre_Contacto_PDV": _col("RESPONSABLE"),
            "Distribuidora_Puesto_Trabajo": _col("PUESTO"),
        }

    def _mapeo_ruta(self, rechazada: bool) -> dict:
        generada = (lambda c: "NULL") if rechazada else _col
        return {
            "Distribuidora": _lit(DISTRIBUIDORA_RUTA),
            "Modelo": _col("MODELO"),
            "Serie": _col("SERIE"),
            "Observaciones": _observaciones([
                ("Falla", "FALLA"), ("Notas", "SUCURSAL"), ("Region", "REGION"),
                ("Fecha venta/factura", "FECHA VENTA"), ("Caso", "NUMERO CASO"),
            ], rechazada),
            "Hora_Atencion": _col("HORARIO"),
            "Folio": _col("ORDEN"),
            "Ticket_Solicitud": _col("AVISO"),
            "Canal": _lit(CANAL_SIN_CANAL),
            "Numero_Cliente": _col("NUMERO CLIENTE"),
            "Nombre_PDV": _col("NOMBRE PDV"),
            "Calle": _col("CALLE"),
            "Numero": _col("NUMERO"),
            "Entre_Calle1": _col("ENTRE CALLE"),
            "Entre_Calle2": _col("Y CALLE"),
            "Colonia": _col("COLONIA"),
            "Municipio": _col("MUNICIPIO"),
            "Codigo_Postal": _col("CP"),
            "Latitud": _col("LATITUD"),
            "Longitud": _col("LONGITUD"),
            "Telefono_Fax_1": _col("TELEFONO"),
            "Nombre_Contacto_PDV": _col("CONTACTO"),
            "Cp_Generado": generada("CP_GEN"),
            "Colonia_Generado": generada("COLONIA_GEN"),
            "Ciudad_Generado": generada("CIUDAD_GEN"),
            "Estado_Generado": generada("ESTADO_GEN"),
            "Pais_Generado": generada("PAIS_GEN"),
        }

    def _insertar(self, destino: str, mapeo: dict, origen: str):
        self.duckConn.execute(f"""
            INSERT INTO {destino} ({", ".join(mapeo)})
            SELECT {", ".join(mapeo.values())}
            FROM "{origen}"
            ORDER BY CAST("_FILA_EXCEL" AS INTEGER)
        """)

    def fill_sabana(self, tabla: str, flujo: str) -> str:
        """Pre-sábana del flujo: válidas en el orden del archivo y rechazadas al final."""
        if flujo == FLUJO_D2D:
            destino, ddl, mapeo = "sabana_movimiento", SQL_SABANA_MOVIMIENTO, self._mapeo_movimiento
        else:
            destino, ddl, mapeo = "sabana_ruta", SQL_SABANA_RUTA, self._mapeo_ruta
            for columna in COLUMNAS_GENERADAS:
                self.duckConn.execute(f'ALTER TABLE "{tabla}" ADD COLUMN IF NOT EXISTS "{columna}" VARCHAR')

        self.duckConn.execute(f"DROP TABLE IF EXISTS {destino}")
        self.duckConn.execute(ddl.read_text(encoding="utf-8"))
        self._insertar(destino, mapeo(False), tabla)
        self._insertar(destino, mapeo(True), "solicitudes_rechazadas")
        return destino
