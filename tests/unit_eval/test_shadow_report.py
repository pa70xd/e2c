"""Reporte del modo sombra a partir de logs exportados."""

import json

import pytest

from classifier import shadow
from eval import shadow_report as sr


def reg(h, customer="danone", etapa="reply", real=("modificar_filas", True), sombra=("modificar_filas", True),
        lat=100, motivo=None):
    comparable = sombra is not None
    s_tipo, s_os = sombra if comparable else (None, None)
    return {
        "message_id_hash": h,
        "customer": customer,
        "etapa": etapa,
        "direccion": "inbound",
        "real": {"proveedor": "regex", "es_os": real[1], "tipo_evento": real[0], "confidence": 1.0},
        "sombra": {"proveedor": "haiku", "es_os": s_os, "tipo_evento": s_tipo, "confidence": 0.9 if comparable else None,
                   "motivo_caida": motivo},
        "coinciden": (s_tipo == real[0] and s_os == real[1]) if comparable else None,
        "latencia_ms": lat,
        "prompt_version": "gate-v1",
    }


REGISTROS = [
    reg("a"),
    reg("b", sombra=("no_os", False), lat=200),
    reg("c", customer="holanda", etapa="init", real=("nueva_solicitud", True), sombra=("nueva_solicitud", True), lat=300),
    reg("d", sombra=None, lat=10000, motivo="shadow_timeout"),
    reg("e", sombra=("estatus", True), lat=400),
]


def _linea(r):
    return f"{shadow.PREFIJO} {json.dumps(r, ensure_ascii=False)}"


def test_parsea_texto_con_prefijo_e_ignora_el_resto():
    texto = "\n".join([
        "[CLASSIFIER] etapa=reply ...",
        "2026-10-26T10:00:00Z " + _linea(REGISTROS[0]),
        f"{shadow.PREFIJO}[ERROR] RuntimeError",
        f"{shadow.PREFIJO} {{json roto",
        _linea(REGISTROS[1]),
        "",
    ])
    assert sr.parsear(texto) == REGISTROS[:2]


def test_parsea_export_json_de_cloud_logging():
    entradas = [{"textPayload": _linea(r), "severity": "DEFAULT"} for r in REGISTROS]
    entradas.append({"textPayload": "otra cosa"})
    assert sr.parsear(json.dumps(entradas)) == REGISTROS


def test_parsea_jsonl_de_entradas_y_de_registros():
    lineas = [json.dumps({"textPayload": _linea(REGISTROS[0])}),
              json.dumps(REGISTROS[1]),
              json.dumps({"jsonPayload": {"message": _linea(REGISTROS[2])}}),
              json.dumps({"jsonPayload": REGISTROS[3]}),
              json.dumps({"otro": 1})]
    assert sr.parsear("\n".join(lineas)) == REGISTROS[:4]


def test_formato_real_de_shadow_py_se_lee():
    # La línea que escribe classifier/shadow.py (sort_keys) se parsea igual.
    linea = f"{shadow.PREFIJO} {json.dumps(REGISTROS[0], ensure_ascii=False, sort_keys=True)}"
    assert sr.parsear(linea) == [REGISTROS[0]]


def test_deduplica_por_hash_y_etapa():
    regs = [reg("a"), reg("a"), reg("a", etapa="init"), reg(None), reg(None)]
    salida, repetidos = sr.deduplicar(regs)
    assert repetidos == 1 and len(salida) == 4


def test_reporte_global_y_por_grupo():
    rep = sr.reporte(REGISTROS)
    g = rep["global"]
    assert (g["correos"], g["comparables"], g["sin_sombra"]) == (5, 4, 1)
    assert g["acuerdo"] == pytest.approx(2 / 4)
    assert g["acuerdo_es_os"] == pytest.approx(3 / 4)

    assert rep["por_cliente"]["danone"]["comparables"] == 3
    assert rep["por_cliente"]["danone"]["acuerdo"] == pytest.approx(1 / 3)
    assert rep["por_cliente"]["holanda"]["acuerdo"] == 1.0
    assert rep["por_etapa"]["init"]["correos"] == 1
    assert rep["por_etapa"]["reply"]["sin_sombra"] == 1
    assert rep["por_tipo_evento"]["modificar_filas"]["correos"] == 4


def test_matriz_latencia_y_motivos():
    rep = sr.reporte(REGISTROS)
    assert rep["matriz"]["modificar_filas"] == {
        "(caída)": 1, "estatus": 1, "modificar_filas": 1, "no_os": 1,
    }
    assert rep["matriz"]["nueva_solicitud"] == {"nueva_solicitud": 1}
    assert rep["latencia_ms"] == {"p50": 300, "p95": 10000, "n": 5}
    assert rep["motivos_caida"] == {"shadow_timeout": 1}
    assert rep["proveedores"] == {"regex->haiku": 5}


def test_sin_comparables_no_divide_por_cero():
    rep = sr.reporte([reg("x", sombra=None, motivo="haiku_sin_api_key")])
    assert rep["global"]["acuerdo"] is None
    assert "  -  " in sr.formatear(rep)


def test_formatear_texto():
    texto = sr.formatear(sr.reporte(REGISTROS), repetidos=2)
    assert "acuerdo (es_os y tipo_evento): 50.0%" in texto
    assert "p50 300 ms, p95 10000 ms" in texto
    assert "repetidos descartados: 2" in texto
    assert "Por cliente" in texto and "holanda" in texto
    assert "Matriz real" in texto and "shadow_timeout" in texto


def test_main(tmp_path, capsys):
    archivo = tmp_path / "shadow.log"
    archivo.write_text("\n".join(_linea(r) for r in REGISTROS + [REGISTROS[0]]), encoding="utf-8")
    assert sr.main([str(archivo)]) == 0
    assert "repetidos descartados: 1" in capsys.readouterr().out

    assert sr.main([str(archivo), "--json"]) == 0
    datos = json.loads(capsys.readouterr().out)
    assert datos["global"]["correos"] == 5 and datos["repetidos"] == 1

    assert sr.main([str(archivo), "--json", "--sin-dedup"]) == 0
    assert json.loads(capsys.readouterr().out)["global"]["correos"] == 6


def test_main_errores(tmp_path, capsys):
    assert sr.main([str(tmp_path / "no_existe")]) == 2
    vacio = tmp_path / "vacio.log"
    vacio.write_text("[CLASSIFIER] nada\n", encoding="utf-8")
    assert sr.main([str(vacio)]) == 1
