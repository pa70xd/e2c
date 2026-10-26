"""El evaluador corre con regex sobre el set sintético, sin red."""

import json
import os
import pathlib

import pytest

from classifier.contracts import TIPOS_EVENTO
from eval import run_eval

REPO = pathlib.Path(__file__).resolve().parents[2]
SINTETICO = REPO / "eval" / "sets" / "sintetico.jsonl"


@pytest.fixture(scope="module")
def casos():
    return run_eval.cargar_set(str(SINTETICO))


def test_set_sintetico_cubre_todos_los_tipos_y_es_inventado(casos):
    assert 55 <= len(casos) <= 80
    assert {c["esperado"]["tipo_evento"] for c in casos} == set(TIPOS_EVENTO)
    assert {c["fuente"] for c in casos} == {"sintetico"}
    assert {c["etapa"] for c in casos} == {"init", "reply"}
    texto = SINTETICO.read_text(encoding="utf-8")
    assert "@" not in texto.replace("[CORREO]", "")


def test_main_regex_corre_y_reporta(capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    codigo = run_eval.main(["--provider", "regex", "--set", str(SINTETICO)])
    salida = capsys.readouterr().out
    assert "precisión" in salida and "Matriz de confusión" in salida
    assert "Falsos positivos" in salida and "exactitud por fila" in salida
    # El código de salida lo decide el veredicto contra el umbral.
    assert codigo == (0 if "NO CUMPLE" not in salida else 1)


def test_umbral_permisivo_da_codigo_cero(capsys):
    assert run_eval.main(["--provider", "regex", "--set", str(SINTETICO), "--umbral", "0.0"]) == 0
    assert "CUMPLE" in capsys.readouterr().out


def test_umbral_alto_da_codigo_distinto_de_cero(capsys):
    assert run_eval.main(["--provider", "regex", "--set", str(SINTETICO), "--umbral", "1.0"]) == 1


def test_haiku_sin_key_sale_sin_error_y_sin_llamar(capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def no_debe_correr(*a, **k):
        raise AssertionError("no debe correr ningún caso")

    monkeypatch.setattr(run_eval, "correr_caso", no_debe_correr)
    assert run_eval.main(["--provider", "haiku", "--set", str(SINTETICO)]) == 0
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().out


def test_set_inexistente_o_invalido_da_codigo_2(tmp_path, capsys):
    assert run_eval.main(["--provider", "regex", "--set", str(tmp_path / "no_existe.jsonl")]) == 2
    malo = tmp_path / "malo.jsonl"
    malo.write_text('{"id": "x"}\n', encoding="utf-8")
    assert run_eval.main(["--provider", "regex", "--set", str(malo)]) == 2


def test_cada_caso_pasa_por_redact(monkeypatch):
    llamadas = []
    from classifier import registry

    real = registry.get_redactor()

    def espia(texto, conservar=()):
        llamadas.append((texto, tuple(conservar)))
        return real(texto, conservar=conservar)

    monkeypatch.setattr(registry, "get_redactor", lambda: espia)
    caso = {
        "id": "t", "fuente": "sintetico", "etapa": "reply", "cliente": "danone",
        "asunto": "Re: x", "cuerpo": "Escríbanme a persona@example.com",
        "thread_ctx": {"filas": [{"row_number": 1, "serie_fabricante": "SF-1", "status": "PENDING"}]},
        "esperado": {"es_os": True, "tipo_evento": "modificar_filas", "filas": []},
    }
    res = run_eval.correr_caso(caso, "regex")
    textos = [t for t, _ in llamadas]
    assert textos == ["Re: x", "Escríbanme a persona@example.com"]
    assert all(c == ("SF-1",) for _, c in llamadas)
    assert res["decision"].proveedor_gate == "regex"


def test_resumen_regex_es_determinista_y_no_toca_el_entorno(casos, monkeypatch):
    monkeypatch.delenv("CLASSIFIER_GATE", raising=False)
    r1 = run_eval.resumir([run_eval.correr_caso(c, "regex") for c in casos], [], "regex", 0.95)
    r2 = run_eval.resumir([run_eval.correr_caso(c, "regex") for c in casos], [], "regex", 0.95)
    assert r1["gate"] == r2["gate"] and r1["extract"] == r2["extract"]
    assert r1["gate"]["tp"] + r1["gate"]["fp"] + r1["gate"]["fn"] + r1["gate"]["tn"] == len(casos)
    # regex siempre devuelve extract vacío y no tiene a qué caer
    assert r1["extract"]["fp"] == 0 and r1["extract"]["tp"] == 0
    assert r1["caida_regex_gate"] is None and "costo" not in r1
    assert r1["cumple"] == (r1["gate"]["precision"] >= 0.95)


def test_resumen_json(tmp_path):
    salida = tmp_path / "r.json"
    run_eval.main(["--provider", "regex", "--set", str(SINTETICO), "--json", str(salida)])
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["proveedor"] == "regex" and "confusion" in datos


def test_precios_solo_de_variables_de_entorno(monkeypatch):
    monkeypatch.delenv("EVAL_PRICE_IN", raising=False)
    monkeypatch.delenv("EVAL_PRICE_OUT", raising=False)
    assert run_eval.precios_configurados() is None
    monkeypatch.setenv("EVAL_PRICE_IN", "1.5")
    assert run_eval.precios_configurados() is None  # falta la de salida
    monkeypatch.setenv("EVAL_PRICE_OUT", "x")
    assert run_eval.precios_configurados() is None  # no es número
    monkeypatch.setenv("EVAL_PRICE_OUT", "7")
    assert run_eval.precios_configurados() == (1.5, 7.0)


def test_reporte_de_costo_no_configurado(capsys):
    from classifier.contracts import GateResult  # noqa: F401  (el import valida el entorno)

    resumen = {
        "proveedor": "haiku", "casos": 0, "errores": [], "umbral": 0.95, "cumple": True,
        "gate": {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0, "tn": 0},
        "confusion": {"no_os": {"no_os": 0}}, "falsos_positivos": [],
        "extract": {"exactitud": 0.0, "tp": 0, "fn": 0, "precision": 0.0, "fp": 0, "casos_exactos": 0, "casos": 0},
        "caida_regex_gate": 0.0, "caida_regex_extract": 0.0,
        "latencia_ms": {"media": 0.0, "p50": 0.0, "p95": 0.0},
        "costo": {"tokens_in": 100.0, "tokens_out": 10.0, "usd": None},
    }
    run_eval.imprimir(resumen, "x.jsonl")
    assert "costo: no configurado" in capsys.readouterr().out


# ------------------------------------------------------------------ diagnóstico
class _G:
    def __init__(self, es_os):
        self.es_os = es_os


class _D:
    def __init__(self, es_os, tipo, fallbacks=()):
        self.es_os, self.tipo_evento, self.fallbacks = es_os, tipo, tuple(fallbacks)
        self.gate = _G(es_os)
        self.rows = ()
        self.proveedor_gate = "haiku"


def _res(id_, esp_os, esp_tipo, pred_os, pred_tipo, fb=(), ambiguo=False):
    caso = {"id": id_, "esperado": {"es_os": esp_os, "tipo_evento": esp_tipo, "filas": []}}
    if ambiguo:
        caso["ambiguo"] = True
    return {"caso": caso, "decision": _D(pred_os, pred_tipo, fb), "latencia": 0.0, "tokens": (0, 0)}


def test_resumen_diagnostico_haiku():
    rs = [
        _res("ok", True, "estatus", True, "estatus"),
        _res("fn1", True, "estatus", False, "no_os", ["gate:haiku:haiku_filas_no_cargadas"]),
        _res("fp1", False, "no_os", True, "estatus", ["extract:haiku:a,b"]),
        _res("amb", True, "estatus", False, "no_os", ambiguo=True),
        _res("tipo", True, "cancelar_filas", True, "modificar_filas"),
    ]
    r = run_eval.resumir(rs, [], "haiku", 0.95)
    assert [x["id"] for x in r["falsos_negativos"]] == ["fn1", "amb"]
    assert [x["id"] for x in r["falsos_positivos"]] == ["fp1"]
    assert {x["id"] for x in r["errores_tipo_evento"]} == {"fn1", "fp1", "amb", "tipo"} - {"x"}
    assert r["caidas_regex"][0] == {
        "id": "fn1", "etapa": "gate", "proveedor": "haiku",
        "motivo": "haiku_filas_no_cargadas", "motivos": ["haiku_filas_no_cargadas"],
    }
    assert r["caidas_por_motivo"] == {
        "extract:a": 1, "extract:b": 1, "gate:haiku_filas_no_cargadas": 1,
    }
    # solo proveedor: sin fn1 (cayó en gate)
    assert r["gate_solo_proveedor"]["casos"] == 4 and r["gate_solo_proveedor"]["fn"] == 1
    assert r["gate"]["fn"] == 2
    assert r["gate_sin_ambiguos"]["casos"] == 4 and r["gate_sin_ambiguos"]["fn"] == 1


def test_resumen_regex_no_inventa_caidas():
    r = run_eval.resumir([_res("a", True, "estatus", True, "estatus")], [], "regex", 0.95)
    assert r["caidas_regex"] == [] and r["gate_solo_proveedor"] is None


def test_imprimir_muestra_diagnostico(capsys):
    rs = [_res("fn1", True, "estatus", False, "no_os", ["gate:haiku:haiku_filas_no_cargadas"])]
    run_eval.imprimir(run_eval.resumir(rs, [], "haiku", 0.95), "x.jsonl")
    out = capsys.readouterr().out
    assert "Falsos negativos (1)" in out and "fn1" in out
    assert "Errores de tipo_evento (1)" in out
    assert "fn1: gate · haiku_filas_no_cargadas" in out
