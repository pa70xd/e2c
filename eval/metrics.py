"""Cálculo de métricas del evaluador. Funciones puras, sin red ni proveedores."""

from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence

CLAVES_SERIE = ("serie_fabricante", "serie_dnn_bnf")


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


def prf(tp: int, fp: int, fn: int) -> dict:
    """Precisión, recall y F1. Un denominador en cero da 0.0."""
    precision = _div(tp, tp + fp)
    recall = _div(tp, tp + fn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": _div(2 * precision * recall, precision + recall),
    }


def gate_es_os(pares: Iterable[tuple[bool, bool]]) -> dict:
    """``pares`` = (es_os esperado, es_os predicho). Positivo = es_os True."""
    tp = fp = fn = tn = 0
    for esperado, predicho in pares:
        if predicho and esperado:
            tp += 1
        elif predicho:
            fp += 1
        elif esperado:
            fn += 1
        else:
            tn += 1
    return {**prf(tp, fp, fn), "tn": tn}


def matriz_confusion(pares: Iterable[tuple[str, str]], tipos: Sequence[str]) -> dict[str, dict[str, int]]:
    """matriz[esperado][predicho] = cantidad. Incluye todos los ``tipos``."""
    matriz = {e: {p: 0 for p in tipos} for e in tipos}
    for esperado, predicho in pares:
        matriz.setdefault(esperado, {p: 0 for p in tipos})
        matriz[esperado][predicho] = matriz[esperado].get(predicho, 0) + 1
    return matriz


def _norm(valor) -> Optional[str]:
    if valor is None:
        return None
    texto = str(valor).strip().casefold()
    return texto or None


def _campo(fila, nombre):
    if isinstance(fila, dict):
        return fila.get(nombre)
    return getattr(fila, nombre, None)


def fila_coincide(esperada: dict, predicha) -> bool:
    """Acción y row_number exactos. Las series se comparan solo si la etiqueta
    trae la clave (aunque sea null); sin clave, no se evalúan."""
    if _campo(predicha, "accion") != esperada.get("accion"):
        return False
    if _campo(predicha, "row_number") != esperada.get("row_number"):
        return False
    for clave in CLAVES_SERIE:
        if clave in esperada and _norm(esperada[clave]) != _norm(_campo(predicha, clave)):
            return False
    return True


def comparar_filas(esperadas: Sequence[dict], predichas: Sequence) -> tuple[int, int, int]:
    """(tp, fp, fn) con emparejamiento uno a uno entre filas."""
    libres = list(range(len(predichas)))
    tp = 0
    for esperada in esperadas:
        for i in libres:
            if fila_coincide(esperada, predichas[i]):
                libres.remove(i)
                tp += 1
                break
    return tp, len(predichas) - tp, len(esperadas) - tp


def extract_filas(resultados: Iterable[tuple[Sequence[dict], Sequence]]) -> dict:
    """Agrega ``comparar_filas`` de todos los casos.

    ``exactitud`` = filas esperadas bien extraídas / filas esperadas (igual al
    recall). ``casos_exactos`` = casos con las filas idénticas a la etiqueta
    (también cuentan los casos sin filas esperadas ni predichas)."""
    tp = fp = fn = exactos = total = 0
    for esperadas, predichas in resultados:
        a, b, c = comparar_filas(esperadas, predichas)
        tp, fp, fn = tp + a, fp + b, fn + c
        total += 1
        exactos += (b == 0 and c == 0)
    m = prf(tp, fp, fn)
    m["exactitud"] = m["recall"]
    m["casos"] = total
    m["casos_exactos"] = exactos
    return m


def percentil(valores: Sequence[float], p: float) -> float:
    """Percentil por rango más cercano. Lista vacía = 0.0."""
    if not valores:
        return 0.0
    orden = sorted(valores)
    k = max(0, min(len(orden) - 1, math.ceil(p / 100 * len(orden)) - 1))
    return orden[k]


def tasa(cuantos: int, de: int) -> Optional[float]:
    """Proporción, o None si no hay base."""
    return cuantos / de if de else None


def veredicto(precision: float, umbral: float) -> bool:
    return precision >= umbral


def costo_usd(tokens_in: float, tokens_out: float, precio_in: float, precio_out: float) -> float:
    """Precios en USD por millón de tokens."""
    return (tokens_in * precio_in + tokens_out * precio_out) / 1_000_000


def agrupar_caidas(caidas: Iterable[dict]) -> dict[str, int]:
    """Cuenta caídas por ``etapa:motivo`` (cada código de error por separado)."""
    cuenta: dict[str, int] = {}
    for c in caidas:
        for motivo in c["motivos"]:
            clave = f"{c['etapa']}:{motivo}"
            cuenta[clave] = cuenta.get(clave, 0) + 1
    return dict(sorted(cuenta.items(), key=lambda kv: (-kv[1], kv[0])))
