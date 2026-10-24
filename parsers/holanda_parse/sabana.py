from pathlib import Path

from config.customers.holanda.reglas_holanda import CANAL_HOLANDA, SUFIJO_MERMA

# DDL compartido del template general (template_rutas.xlsx, vía
# excel_ingestion.get_excelv2_attachment) -- el mismo para todos los
# clientes, por eso no se copia.
SQL_SABANA_RUTA = Path("config/config_general/querys/generic_sabana_ruta.sql")

# Columnas que agregan GEOCODING.calcula_coordenadas y
# HOLANDA_CATALOG.calcula_distribuidora antes de armar la pre-sábana.
COLUMNAS_GENERADAS = ("CP_GEN", "COLONIA_GEN", "CIUDAD_GEN", "ESTADO_GEN", "PAIS_GEN", "DISTRIBUIDORA_GEN")


class HOLANDA_SABANA:
    """Pre-sábana de Holanda sobre el template general. Holanda es "solo
    ruta" (no hay pre-sábana de movimiento). Categoria/Linea quedan vacías
    (Danone tampoco las tiene implementadas)."""

    # Número (con o sin una letra pegada: "208", "5 A") o el literal "SN"
    # al final del texto.
    _PATRON_NUMERO = r'(?i)(\d+\s*[a-z]?|sn)\s*$'

    def __init__(self, duckConn):
        self.duckConn = duckConn

    def fill_template(self, table_name):
        """`holanda_sabana`: la tabla de trabajo completa, que es la que se
        registra en cooler_request (process_data.prepare_data_coolers)."""
        self.duckConn.execute(f"""
            CREATE OR REPLACE TABLE holanda_sabana AS
            SELECT * FROM "{table_name}"
        """)
        return "holanda_sabana"

    # ------------------------------------------------------------------
    # Expresiones SQL reutilizables
    # ------------------------------------------------------------------

    @staticmethod
    def _sql_valor(columna: str) -> str:
        """Texto limpio o NULL (el reader siembra "" en columnas que no
        venían en el archivo)."""
        return f"NULLIF(TRIM(CAST({columna} AS VARCHAR)), '')"

    @staticmethod
    def _sql_calle(columna: str) -> str:
        return (
            f"NULLIF(TRIM(regexp_replace({columna}, "
            f"'{HOLANDA_SABANA._PATRON_NUMERO}', '')), '')"
        )

    @staticmethod
    def _sql_numero(columna: str) -> str:
        return (
            f"NULLIF(regexp_extract({columna}, "
            f"'{HOLANDA_SABANA._PATRON_NUMERO}', 1), '')"
        )

    @staticmethod
    def _sql_observaciones(col, motivo: str | None = None) -> str:
        """[MOTIVO |] Tipo de queja: X | Clasificador: Y. CONCAT_WS omite
        los NULL; si todo está vacío queda NULL."""
        v = HOLANDA_SABANA._sql_valor
        partes = [v(motivo)] if motivo else []
        partes.append(f"'Tipo de queja: ' || {v(col('TIPO DE QUEJA'))}")
        partes.append(f"'Clasificador: ' || {v(col('CLASIFICADOR DE CASO'))}")
        return f"NULLIF(CONCAT_WS(' | ', {', '.join(partes)}), '')"

    def _select(self, tabla: str, rechazada: bool = False, sufijo_serie: str = "") -> str:
        """SELECT con el mapeo layout -> template. Mismo mapeo para filas
        válidas, espejos de merma (sufijo_serie) y rechazadas; las
        rechazadas no pasaron por el enriquecimiento (columnas generadas en
        NULL) y llevan el MOTIVO al inicio de Observaciones."""

        def col(nombre):
            return f'"{nombre}"'

        v = self._sql_valor
        generada = (lambda nombre: "NULL") if rechazada else col
        serie = f"{col('SERIE')} || '{sufijo_serie}'" if sufijo_serie else col("SERIE")

        mapeo = {
            "Ticket_Solicitud": v(col("CASO2")),
            "Folio": v(col("CASO2")),
            "Numero_Cliente": v(col("SAP")),
            "Nombre_Contacto_PDV": v(col("NOMBRE DEL CLIENTE")),
            "Modelo": col("MODELO"),
            "Serie": serie,
            "Canal": f"'{CANAL_HOLANDA}'",
            "Nombre_PDV": col("NOMBRE NEGOCIO"),
            "Calle": self._sql_calle(col("CALLE Y NUMERO")),
            "Numero": self._sql_numero(col("CALLE Y NUMERO")),
            "Colonia": col("COLONIA"),
            "Municipio": col("MUNICIPIO"),
            "Codigo_Postal": col("CP"),
            "Latitud": col("LATITUD"),
            "Longitud": col("LONGITUD"),
            "Telefono_Fax_1": col("TELEFONO"),
            "Cp_Generado": generada("CP_GEN"),
            "Colonia_Generado": generada("COLONIA_GEN"),
            "Ciudad_Generado": generada("CIUDAD_GEN"),
            "Estado_Generado": generada("ESTADO_GEN"),
            "Pais_Generado": generada("PAIS_GEN"),
            "Distribuidora": generada("DISTRIBUIDORA_GEN"),
            "Observaciones": self._sql_observaciones(
                col, motivo=col("MOTIVO") if rechazada else None
            ),
        }

        return f"""
            INSERT INTO sabana_ruta ({", ".join(mapeo)})
            SELECT {", ".join(mapeo.values())}
            FROM "{tabla}"
            ORDER BY rowid
        """

    def fill_sabana_ruta(self, table_name):
        """Arma `sabana_ruta` (único adjunto de Holanda). Mapeo en _select;
        reglas fijas en reglas_holanda.py:
          - Folio y Ticket_Solicitud = CASO2; Canal = CANAL_HOLANDA;
            Numero_Activo siempre vacío.
          - CALLE Y NUMERO se parte en Calle/Numero (_PATRON_NUMERO); si no
            calza, Numero queda vacío y Calle conserva el texto completo.
          - ESPEJO DE MERMA: cada solicitud válida se repite con
            SUFIJO_MERMA pegado a la Serie; las rechazadas no llevan espejo.
          - Orden: solicitudes, luego sus espejos, al final las rechazadas
            (con el MOTIVO en Observaciones, igual que Danone las fusiona
            en su tabla `solicitud`).
          - Sin columna en el template (quedan solo en cooler_request):
            ORIGEN, FECHA, ESTADO, SEGMENTO, AGRUPADOR, REGION, AGENCIA,
            RUTA, AGENCIA SATELITE, OXXO, SIN SAP/SIN CONGELADOR,
            PROVEEDOR, TE, CONGELADOR, CANAL."""

        self.duckConn.execute(SQL_SABANA_RUTA.read_text(encoding="utf-8"))

        # Si el enriquecimiento no corrió (p. ej. sin LATITUD/LONGITUD),
        # las columnas generadas no existen: se agregan vacías.
        for columna in COLUMNAS_GENERADAS:
            self.duckConn.execute(
                f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{columna}" VARCHAR'
            )

        # INSERT separados (no UNION ALL) para garantizar el orden.
        self.duckConn.execute(self._select(table_name))
        self.duckConn.execute(self._select(table_name, sufijo_serie=SUFIJO_MERMA))
        self.duckConn.execute(self._select("solicitudes_rechazadas", rechazada=True))

        return "sabana_ruta"
