"""Reglas de negocio de la etapa 1 (Imbera y Torrey). Separa las filas en
válidas y rechazadas (con MOTIVO) y agrega a cada fila lo que se derivó
del correo: tipo de servicio, cliente de la OS, sub-cliente, folio y la
MARCA de garantía (no se valida: es la etapa 2)."""

from __future__ import annotations

import pandas as pd

from config.customers.imbera import reglas_imbera as R
from config.customers.imbera.columns_names import COL_ARCHIVO, COL_FILA_EXCEL, COLUMNAS
from parsers.imbera_parse.clasificacion import Clasificacion
from parsers.imbera_parse.lector import normalizar
from parsers.imbera_parse.perfil import PerfilLayout

# Columnas que agrega aplicar_reglas.
DERIVADAS = [
    "TIPO_SERVICIO", "CLIENTE_OS", "SUBCLIENTE", "PLAZA", "FOLIO",
    "TICKET", "VARIANTE_RUTA", "GARANTIA", "SENALES_GARANTIA", "MOTIVO",
]
TABLA_VALIDAS = "imbera_validas"
TABLA_RECHAZADAS = "solicitudes_rechazadas"

M_SERIE = "[RECHAZADO] Serie vacía"
M_MODELO = "[RECHAZADO] Modelo vacío"
M_SERIE_DUPLICADA = "[RECHAZADO] Serie repetida en la solicitud"
M_MOVIMIENTO = "[RECHAZADO] Movimiento no atendido: solo instalación (no hay retiros ni traslados)"
M_NO_INSTITUCIONAL = "[RECHAZADO] Instalación solo para clientes institucionales"


def _movimiento(fila: dict, clasificacion: Clasificacion) -> str:
    return normalizar(fila.get("TIPO DE MOVIMIENTO")) or normalizar(clasificacion.movimiento)


def _motivo(fila: dict, clasificacion: Clasificacion, series_vistas: set) -> str | None:
    serie = normalizar(fila.get("SERIE"))
    if not serie:
        return M_SERIE
    if not normalizar(fila.get("MODELO")):
        return M_MODELO
    if serie in series_vistas:
        return M_SERIE_DUPLICADA

    movimiento = _movimiento(fila, clasificacion)
    if movimiento in R.MOVIMIENTOS_NO_ATENDIDOS:
        return M_MOVIMIENTO
    if (
        movimiento == R.MOVIMIENTO_INSTALACION
        and R.CLIENTES_INSTITUCIONALES
        and clasificacion.subcliente not in R.CLIENTES_INSTITUCIONALES
    ):
        return M_NO_INSTITUCIONAL
    return None


def _senales_fila(fila: dict, clasificacion: Clasificacion, perfil: PerfilLayout) -> list[str]:
    senales = list(clasificacion.senales_garantia)
    if R.PATRON_EQUIPO_NUEVO_DANADO.search(normalizar(fila.get("FALLA"))) and "equipo_nuevo_danado" not in senales:
        senales.append("equipo_nuevo_danado")
    if perfil.siempre_garantia and "buzon_cliente" not in senales:
        senales.append("buzon_cliente")
    return senales


def aplicar_reglas(duck_conn, table: str, clasificacion: Clasificacion, perfil: PerfilLayout) -> tuple[int, int]:
    """Crea TABLA_VALIDAS y TABLA_RECHAZADAS (mismas columnas) y regresa
    (válidas, rechazadas). El orden de las filas es el del archivo."""
    df = duck_conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchdf()

    filas = []
    series_vistas: set[str] = set()
    for fila in df.to_dict("records"):
        fila = {k: ("" if v is None or (isinstance(v, float) and pd.isna(v)) else v) for k, v in fila.items()}
        motivo = _motivo(fila, clasificacion, series_vistas)
        if motivo is None:
            series_vistas.add(normalizar(fila.get("SERIE")))

        movimiento = _movimiento(fila, clasificacion)
        senales = _senales_fila(fila, clasificacion, perfil)
        cliente_fila = perfil.cliente_os_fila(fila) if perfil.cliente_os_fila else None

        fila.update({
            # RUTA o el movimiento (INSTALACION, o RETIRO/TRASLADO rechazados).
            "TIPO_SERVICIO": movimiento if movimiento in R.MOVIMIENTOS else "RUTA",
            "CLIENTE_OS": cliente_fila or perfil.cliente_os,
            "SUBCLIENTE": clasificacion.subcliente or "",
            "PLAZA": clasificacion.plaza or "",
            "FOLIO": clasificacion.folio or clasificacion.folio_app or "",
            "TICKET": clasificacion.os_asunto or "",
            "VARIANTE_RUTA": "" if movimiento in R.MOVIMIENTOS else (clasificacion.variante_ruta or ""),
            "GARANTIA": "SI" if senales else "NO",
            "SENALES_GARANTIA": ",".join(senales),
            "MOTIVO": motivo or "",
        })
        filas.append(fila)

    columnas = COLUMNAS + [COL_ARCHIVO, COL_FILA_EXCEL] + DERIVADAS
    todas = pd.DataFrame(filas, columns=columnas, dtype="object").fillna("")
    validas = todas[todas["MOTIVO"] == ""]
    rechazadas = todas[todas["MOTIVO"] != ""]

    for nombre, datos in ((TABLA_VALIDAS, validas), (TABLA_RECHAZADAS, rechazadas)):
        # VARCHAR explícito: un DataFrame vacío no trae tipos.
        duck_conn.execute(
            f'CREATE OR REPLACE TABLE "{nombre}" ('
            + ", ".join(f'"{c}" VARCHAR' for c in columnas)
            + ")"
        )
        if len(datos):
            duck_conn.register("tmp_df", datos.astype(str))
            duck_conn.execute(f'INSERT INTO "{nombre}" SELECT * FROM tmp_df')
            duck_conn.unregister("tmp_df")

    return len(validas), len(rechazadas)
