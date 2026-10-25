"""Cálculo de métricas del evaluador."""

import pytest

from eval import metrics


def test_prf_basico():
    m = metrics.prf(tp=8, fp=2, fn=4)
    assert m["precision"] == pytest.approx(0.8)
    assert m["recall"] == pytest.approx(8 / 12)
    assert m["f1"] == pytest.approx(2 * 0.8 * (8 / 12) / (0.8 + 8 / 12))


def test_prf_denominadores_en_cero():
    m = metrics.prf(0, 0, 0)
    assert (m["precision"], m["recall"], m["f1"]) == (0.0, 0.0, 0.0)


def test_gate_es_os_cuenta_cuadrantes():
    pares = [(True, True), (True, True), (False, True), (True, False), (False, False)]
    m = metrics.gate_es_os(pares)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (2, 1, 1, 1)
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["recall"] == pytest.approx(2 / 3)


def test_gate_sin_positivos_predichos_tiene_precision_cero():
    assert metrics.gate_es_os([(True, False), (False, False)])["precision"] == 0.0


def test_matriz_confusion():
    tipos = ("a", "b", "c")
    matriz = metrics.matriz_confusion([("a", "a"), ("a", "b"), ("b", "b"), ("c", "a")], tipos)
    assert matriz["a"] == {"a": 1, "b": 1, "c": 0}
    assert matriz["b"]["b"] == 1
    assert matriz["c"]["a"] == 1
    assert sum(sum(f.values()) for f in matriz.values()) == 4


def test_fila_coincide_ignora_series_sin_clave_en_la_etiqueta():
    pred = {"accion": "cancelar", "row_number": 2, "serie_fabricante": "SF-1"}
    assert metrics.fila_coincide({"accion": "cancelar", "row_number": 2}, pred)


def test_fila_coincide_compara_series_si_la_etiqueta_las_trae():
    esperada = {"accion": "agregar", "row_number": None, "serie_fabricante": "SF-1"}
    assert metrics.fila_coincide(esperada, {"accion": "agregar", "row_number": None, "serie_fabricante": " sf-1 "})
    assert not metrics.fila_coincide(esperada, {"accion": "agregar", "row_number": None, "serie_fabricante": "SF-2"})
    # null explícito: se exige que no haya serie
    esperada_nula = {"accion": "agregar", "row_number": None, "serie_dnn_bnf": None}
    assert not metrics.fila_coincide(esperada_nula, {"accion": "agregar", "row_number": None, "serie_dnn_bnf": "X"})


def test_fila_coincide_exige_accion_y_row_number():
    esperada = {"accion": "modificar", "row_number": 2}
    assert not metrics.fila_coincide(esperada, {"accion": "cancelar", "row_number": 2})
    assert not metrics.fila_coincide(esperada, {"accion": "modificar", "row_number": 3})


def test_comparar_filas_empareja_uno_a_uno():
    esperadas = [{"accion": "cancelar", "row_number": 1}, {"accion": "cancelar", "row_number": 1}]
    predichas = [{"accion": "cancelar", "row_number": 1}]
    assert metrics.comparar_filas(esperadas, predichas) == (1, 0, 1)


def test_comparar_filas_sobrantes_y_faltantes():
    esperadas = [{"accion": "cancelar", "row_number": 1}]
    predichas = [{"accion": "cancelar", "row_number": 2}, {"accion": "cancelar", "row_number": 1}]
    assert metrics.comparar_filas(esperadas, predichas) == (1, 1, 0)


def test_extract_filas_agrega_casos():
    m = metrics.extract_filas([
        ([{"accion": "cancelar", "row_number": 1}], [{"accion": "cancelar", "row_number": 1}]),
        ([{"accion": "cancelar", "row_number": 2}], []),
        ([], []),
        ([], [{"accion": "agregar", "row_number": None}]),
    ])
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 1)
    assert m["exactitud"] == pytest.approx(0.5)
    assert (m["casos"], m["casos_exactos"]) == (4, 2)


def test_percentil_rango_mas_cercano():
    datos = [10, 20, 30, 40]
    assert metrics.percentil(datos, 50) == 20
    assert metrics.percentil(datos, 95) == 40
    assert metrics.percentil([], 50) == 0.0


def test_tasa_sin_base_es_none():
    assert metrics.tasa(1, 0) is None
    assert metrics.tasa(1, 4) == 0.25


def test_veredicto_incluye_el_umbral():
    assert metrics.veredicto(0.95, 0.95)
    assert not metrics.veredicto(0.9499, 0.95)


def test_costo_usd():
    assert metrics.costo_usd(1_000_000, 1_000_000, 0.10, 0.50) == pytest.approx(0.60)
