"""Reglas de negocio de KOF: cada fila del archivo se vuelve uno o más
registros (Cambio de Equipo = instalación + retiro) con su sábana (ruta o
movimiento), o se rechaza con motivo."""

import re

import pandas as pd

from config.customers.kof import columns_names as col
from config.customers.kof import reglas_kof as reglas
from parsers.kof_parse.reader import TEXTO_PLANO, HOJA, normalizar

TIPO = "TIPO DE SERVICIO"
SABANA = "SABANA"
MOVIMIENTO_ORIGINAL = "MOVIMIENTO ORIGINAL"
MOTIVO = "MOTIVO"


def _v(fila, columna):
    valor = fila.get(columna)
    return None if valor is None or (isinstance(valor, float) and pd.isna(valor)) else valor


def es_venta_material(fila) -> bool:
    texto = " ".join(normalizar(_v(fila, c)) for c in (col.FALLA, col.SOLICITUD) if _v(fila, c))
    return bool(re.search(reglas.VENTA_MATERIAL_REGEX, texto))


def _registro(fila, tipo, sabana, **cambios):
    registro = dict(fila)
    registro.update(cambios)
    registro[TIPO] = tipo
    registro[SABANA] = sabana
    registro[MOVIMIENTO_ORIGINAL] = _v(fila, col.TIPO_MOVIMIENTO)
    return registro


def _rechazo(fila, motivo, tipo=None):
    registro = dict(fila)
    registro[TIPO] = tipo
    registro[SABANA] = None
    registro[MOVIMIENTO_ORIGINAL] = _v(fila, col.TIPO_MOVIMIENTO)
    registro[MOTIVO] = motivo
    return registro


def _retiro(fila):
    """Equipo a retirar de un Cambio de Equipo, en las columnas del equipo."""
    return {
        col.SERIE: _v(fila, col.SERIE_RETIRO),
        col.MODELO: _v(fila, col.MODELO_RETIRO),
        col.ACTIVO: _v(fila, col.ACTIVO_RETIRO),
    }


def expandir(fila) -> list[dict]:
    """Registros de una fila (sin validar), o un rechazo."""
    movimiento = _v(fila, col.TIPO_MOVIMIENTO)

    if fila.get(HOJA) == TEXTO_PLANO:
        return [_registro(fila, reglas.PROYECTO_ESPECIAL, reglas.SABANA_RUTA)]

    if movimiento:
        tipos = reglas.MOVIMIENTOS.get(normalizar(movimiento))
        if tipos is None:
            return [_rechazo(fila, reglas.MOTIVO_MOVIMIENTO)]
        registros = []
        for tipo in tipos:
            if tipo == reglas.RETIRO and normalizar(movimiento).startswith(reglas.CAMBIO_DE_EQUIPO):
                registros.append(_registro(fila, tipo, reglas.SABANA_MOVIMIENTO, **_retiro(fila)))
            elif tipo == reglas.RETIRO and not _v(fila, col.SERIE):
                # Retiro suelto (o la respuesta de REPARE ya desdoblada):
                # la serie puede venir en las columnas del equipo a retirar.
                registros.append(_registro(fila, tipo, reglas.SABANA_MOVIMIENTO, **_retiro(fila)))
            else:
                registros.append(_registro(fila, tipo, reglas.SABANA_MOVIMIENTO))
        return registros

    # Venta de material antes que falla: nunca se reporta como falla.
    if es_venta_material(fila):
        return [_registro(fila, reglas.VENTA_MATERIAL, reglas.SABANA_RUTA)]

    if _v(fila, col.FALLA):
        return [_registro(fila, reglas.SERVICIO_DISTRIBUIDOR, reglas.SABANA_RUTA)]

    return [_rechazo(fila, reglas.MOTIVO_SIN_TIPO)]


def validar(registro) -> str | None:
    """Motivo de rechazo del registro, o None si es válido."""
    if registro[TIPO] != reglas.PROYECTO_ESPECIAL and not _v(registro, col.SERIE):
        if registro[TIPO] == reglas.RETIRO and normalizar(registro.get(MOVIMIENTO_ORIGINAL) or "").startswith(reglas.CAMBIO_DE_EQUIPO):
            return reglas.MOTIVO_SIN_SERIE_RETIRO
        return reglas.MOTIVO_SIN_SERIE
    if registro[TIPO] != reglas.PROYECTO_ESPECIAL and not _v(registro, col.ID_CLIENTE):
        return reglas.MOTIVO_SIN_DETALLISTA
    return None


class KOF_BUSINESS:

    @staticmethod
    def aplicar(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
        """(aceptados, rechazados). Una serie repetida con el mismo tipo dentro
        del archivo se rechaza: la primera aparición gana."""
        aceptados, rechazados = [], []
        vistas = set()
        for fila in df.to_dict("records"):
            for registro in expandir(fila):
                if registro.get(MOTIVO):
                    rechazados.append(registro)
                    continue
                motivo = validar(registro)
                llave = (registro[TIPO], normalizar(_v(registro, col.SERIE) or ""))
                if motivo is None and llave[1] and llave in vistas:
                    motivo = reglas.MOTIVO_DUPLICADA
                if motivo:
                    registro[MOTIVO] = motivo
                    rechazados.append(registro)
                    continue
                vistas.add(llave)
                aceptados.append(registro)
        return aceptados, rechazados
