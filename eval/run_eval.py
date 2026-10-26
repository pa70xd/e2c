"""Evaluador reproducible de gate y extract por proveedor.

    python eval/run_eval.py --provider regex --set eval/sets/sintetico.jsonl
    ANTHROPIC_API_KEY=... python eval/run_eval.py --provider haiku --set <ruta>

Formato del set en ``eval/schema.md``. Cada caso pasa SIEMPRE por
``classifier.redact`` (asunto y cuerpo, con las series del hilo conservadas),
aunque el set ya venga redactado, y luego por ``classifier.decidir`` con el
proveedor elegido (misma ruta que producción: validación y caída a regex).

Código de salida: 0 si la precisión del gate alcanza el umbral
(``--umbral``, default 0.95) o si haiku no corre por falta de
ANTHROPIC_API_KEY; 1 si no alcanza; 2 si el set no se puede leer.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eval import metrics  # noqa: E402

UMBRAL_PRECISION_GATE = 0.95
PROVEEDORES = ("regex", "haiku")
# Precios en USD por millón de tokens, de variables opcionales. Sin ellas no
# se estima costo (no hay precios fijos en el código).
ENV_PRECIO_IN = "EVAL_PRICE_IN"
ENV_PRECIO_OUT = "EVAL_PRICE_OUT"
CHARS_POR_TOKEN = 3.5
# Salida típica de haiku, solo para la estimación de costo.
TOKENS_OUT_GATE = 60
TOKENS_OUT_FILA = 70


class SetInvalido(ValueError):
    pass


# ------------------------------------------------------------------ carga
def cargar_set(ruta: str) -> list[dict]:
    casos, ids = [], set()
    with open(ruta, encoding="utf-8") as fh:
        for n, linea in enumerate(fh, 1):
            if not linea.strip():
                continue
            try:
                caso = json.loads(linea)
            except ValueError as e:
                raise SetInvalido(f"línea {n}: JSON inválido ({e})") from None
            validar_caso(caso, n)
            if caso["id"] in ids:
                raise SetInvalido(f"línea {n}: id repetido {caso['id']!r}")
            ids.add(caso["id"])
            casos.append(caso)
    if not casos:
        raise SetInvalido("el set no tiene casos")
    return casos


def validar_caso(caso: dict, n: int = 0) -> None:
    from classifier.contracts import ACCIONES, ETAPAS, TIPOS_EVENTO, TIPOS_SIN_OS

    def falla(msg):
        raise SetInvalido(f"línea {n}: {caso.get('id', '?')}: {msg}")

    if not isinstance(caso, dict):
        falla("el caso no es un objeto")
    for campo in ("id", "etapa", "cuerpo", "esperado", "fuente"):
        if campo not in caso:
            falla(f"falta {campo}")
    if caso["etapa"] not in ETAPAS:
        falla("etapa inválida")
    if caso["fuente"] not in ("sintetico", "real"):
        falla("fuente inválida")
    esp = caso["esperado"]
    if esp.get("tipo_evento") not in TIPOS_EVENTO:
        falla("tipo_evento inválido")
    if esp.get("es_os") != (esp["tipo_evento"] not in TIPOS_SIN_OS):
        falla("es_os incoherente con tipo_evento")
    for fila in esp.get("filas", []):
        if fila.get("accion") not in ACCIONES:
            falla("acción de fila inválida")
        if "row_number" not in fila:
            falla("fila sin row_number (usa null para agregar)")


def armar_ctx(caso: dict):
    from classifier.contracts import DecisionPrevia, FilaGuardada, ThreadCtx

    tc = caso.get("thread_ctx") or {}
    filas = tc.get("filas")
    if filas is not None:
        filas = tuple(
            FilaGuardada(
                row_number=f["row_number"],
                status=f["status"],
                serie_fabricante=f.get("serie_fabricante"),
                serie_dnn_bnf=f.get("serie_dnn_bnf"),
            )
            for f in filas
        )
    decisiones = tuple(
        DecisionPrevia(d["tipo_evento"], d["es_os"], d.get("proveedor", "regex"))
        for d in tc.get("decisiones", [])
    )
    return ThreadCtx(
        etapa=caso["etapa"],
        customer=caso.get("cliente"),
        direccion=caso.get("direccion"),
        decisiones=decisiones,
        filas=filas,
    )


# ------------------------------------------------------------------ ejecución
def redactar(caso: dict, ctx):
    """Asunto y cuerpo redactados. Siempre, aunque el set venga redactado."""
    from classifier import registry

    redact = registry.get_redactor()
    conservar = ctx.series()
    asunto = caso.get("asunto")
    return (
        redact(asunto, conservar=conservar) if asunto else asunto,
        redact(caso["cuerpo"] or "", conservar=conservar),
    )


def estimar_tokens(texto: str) -> float:
    return len(texto) / CHARS_POR_TOKEN


def tokens_haiku(ctx, asunto, cuerpo, decision) -> tuple[float, float]:
    """(entrada, salida) estimadas de las llamadas que haiku hizo en el caso.
    Aproximación por caracteres: no hay conteo real de tokens sin la API."""
    from classifier.providers import haiku

    t_in = t_out = 0.0
    if not any(f.startswith("gate:") for f in decision.fallbacks):
        t_in += estimar_tokens(haiku._prompt("gate")[0] + haiku._mensaje(ctx, cuerpo, asunto))
        t_out += TOKENS_OUT_GATE
    if decision.gate.es_os and decision.proveedor_gate == "haiku":
        t_in += estimar_tokens(haiku._prompt("extract")[0] + haiku._mensaje(ctx, cuerpo, gate=decision.gate))
        t_out += TOKENS_OUT_FILA * max(1, len(decision.rows))
    return t_in, t_out


def precios_configurados() -> tuple[float, float] | None:
    """(entrada, salida) por millón de tokens, o None si falta alguno o no es un número."""
    try:
        p_in = float(os.environ[ENV_PRECIO_IN])
        p_out = float(os.environ[ENV_PRECIO_OUT])
    except (KeyError, ValueError):
        return None
    return p_in, p_out


def correr_caso(caso: dict, proveedor: str) -> dict:
    import classifier

    ctx = armar_ctx(caso)
    asunto, cuerpo = redactar(caso, ctx)
    os.environ["CLASSIFIER_GATE"] = proveedor
    os.environ["CLASSIFIER_EXTRACT"] = proveedor
    t0 = time.monotonic()
    with contextlib.redirect_stdout(io.StringIO()):  # los parsers y logs imprimen
        decision = classifier.decidir(asunto, cuerpo, ctx)
    latencia = time.monotonic() - t0
    res = {"caso": caso, "decision": decision, "latencia": latencia}
    if proveedor == "haiku":
        res["tokens"] = tokens_haiku(ctx, asunto, cuerpo, decision)
    return res


# ------------------------------------------------------------------ resumen
def _cayo(decision, etapa: str) -> bool:
    return any(f.startswith(f"{etapa}:") for f in decision.fallbacks)


def listar_caidas(resultados: list[dict]) -> list[dict]:
    """Caídas a regex: id, etapa y motivos. Los fallbacks del registry traen
    ``etapa:proveedor:codigos`` (códigos de error, nunca texto del correo)."""
    caidas = []
    for r in resultados:
        for f in r["decision"].fallbacks:
            etapa, _, resto = f.partition(":")
            proveedor, _, motivo = resto.partition(":")
            caidas.append(
                {
                    "id": r["caso"]["id"],
                    "etapa": etapa,
                    "proveedor": proveedor,
                    "motivo": motivo,
                    "motivos": [m for m in motivo.split(",") if m] or ["desconocido"],
                }
            )
    return caidas


def _gate_de(resultados: list[dict]) -> dict:
    return metrics.gate_es_os(
        (r["caso"]["esperado"]["es_os"], r["decision"].es_os) for r in resultados
    )


def resumir(resultados: list[dict], errores: list[tuple[str, str]], proveedor: str, umbral: float) -> dict:
    from classifier.contracts import TIPOS_EVENTO

    pares_os = [
        (r["caso"]["esperado"]["es_os"], r["decision"].es_os) for r in resultados
    ]
    pares_tipo = [
        (r["caso"]["esperado"]["tipo_evento"], r["decision"].tipo_evento) for r in resultados
    ]
    gate = metrics.gate_es_os(pares_os)
    falsos_positivos = [
        {
            "id": r["caso"]["id"],
            "esperado": r["caso"]["esperado"]["tipo_evento"],
            "predicho": r["decision"].tipo_evento,
        }
        for r in resultados
        if r["decision"].es_os and not r["caso"]["esperado"]["es_os"]
    ]
    falsos_negativos = [
        {
            "id": r["caso"]["id"],
            "esperado": r["caso"]["esperado"]["tipo_evento"],
            "predicho": r["decision"].tipo_evento,
        }
        for r in resultados
        if not r["decision"].es_os and r["caso"]["esperado"]["es_os"]
    ]
    errores_tipo = [
        {
            "id": r["caso"]["id"],
            "esperado": r["caso"]["esperado"]["tipo_evento"],
            "predicho": r["decision"].tipo_evento,
        }
        for r in resultados
        if r["caso"]["esperado"]["tipo_evento"] != r["decision"].tipo_evento
    ]
    caidas = [] if proveedor == "regex" else listar_caidas(resultados)
    sin_ambiguos = [r for r in resultados if not r["caso"].get("ambiguo")]
    solo_proveedor = [r for r in resultados if not _cayo(r["decision"], "gate")]
    extract = metrics.extract_filas(
        (r["caso"]["esperado"].get("filas", []), r["decision"].rows) for r in resultados
    )
    con_extract = [r for r in resultados if r["decision"].gate.es_os]
    caidas_gate = sum(_cayo(r["decision"], "gate") for r in resultados)
    caidas_extract = sum(_cayo(r["decision"], "extract") for r in con_extract)
    lat = [r["latencia"] * 1000 for r in resultados]
    resumen = {
        "proveedor": proveedor,
        "casos": len(resultados),
        "errores": errores,
        "gate": gate,
        "confusion": metrics.matriz_confusion(pares_tipo, TIPOS_EVENTO),
        "falsos_positivos": falsos_positivos,
        "falsos_negativos": falsos_negativos,
        "errores_tipo_evento": errores_tipo,
        "caidas_regex": caidas,
        "caidas_por_motivo": metrics.agrupar_caidas(caidas),
        # Con regex todo lo responde regex: no hay subconjunto "solo proveedor".
        "gate_solo_proveedor": None if proveedor == "regex" else {**_gate_de(solo_proveedor), "casos": len(solo_proveedor)},
        "gate_sin_ambiguos": {**_gate_de(sin_ambiguos), "casos": len(sin_ambiguos)},
        "gate_solo_proveedor_sin_ambiguos": None
        if proveedor == "regex"
        else (lambda xs: {**_gate_de(xs), "casos": len(xs)})([r for r in solo_proveedor if not r["caso"].get("ambiguo")]),
        "extract": extract,
        # Con regex no hay a qué caer: la tasa no aplica.
        "caida_regex_gate": None if proveedor == "regex" else metrics.tasa(caidas_gate, len(resultados)),
        "caida_regex_extract": None if proveedor == "regex" else metrics.tasa(caidas_extract, len(con_extract)),
        "latencia_ms": {
            "media": sum(lat) / len(lat) if lat else 0.0,
            "p50": metrics.percentil(lat, 50),
            "p95": metrics.percentil(lat, 95),
        },
        "umbral": umbral,
        "cumple": metrics.veredicto(gate["precision"], umbral),
    }
    if proveedor == "haiku":
        t_in = sum(r["tokens"][0] for r in resultados)
        t_out = sum(r["tokens"][1] for r in resultados)
        precios = precios_configurados()
        resumen["costo"] = {
            "tokens_in": t_in,
            "tokens_out": t_out,
            "usd": metrics.costo_usd(t_in, t_out, *precios) if precios else None,
        }
    return resumen


def _pct(x) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def imprimir(r: dict, ruta: str) -> None:
    g, e = r["gate"], r["extract"]
    print(f"== Evaluación e2c · proveedor={r['proveedor']} · set={ruta} · casos={r['casos']} ==")
    for cid, motivo in r["errores"]:
        print(f"  ! caso {cid} excluido: {motivo}")
    print("\n-- Gate (positivo = es_os) --")
    print(f"precisión {g['precision']:.4f} · recall {g['recall']:.4f} · F1 {g['f1']:.4f}")
    print(f"TP {g['tp']} · FP {g['fp']} · FN {g['fn']} · TN {g['tn']}")
    print("\nMatriz de confusión por tipo_evento (filas = esperado, columnas = predicho)")
    tipos = list(r["confusion"])
    ancho = max(len(t) for t in tipos)
    print(" " * ancho + " " + " ".join(f"{i:>3}" for i, _ in enumerate(tipos)))
    for esperado, fila in r["confusion"].items():
        print(f"{esperado:<{ancho}} " + " ".join(f"{fila[p]:>3}" for p in tipos) + f"   <- {tipos.index(esperado)}")
    print("columnas: " + ", ".join(f"{i}={t}" for i, t in enumerate(tipos)))
    print(f"\nFalsos positivos ({len(r['falsos_positivos'])}):")
    for fp in r["falsos_positivos"]:
        print(f"  {fp['id']}: esperado {fp['esperado']} -> predicho {fp['predicho']}")
    print(f"\nFalsos negativos ({len(r.get('falsos_negativos', []))}):")
    for fn in r.get("falsos_negativos", []):
        print(f"  {fn['id']}: esperado {fn['esperado']} -> predicho {fn['predicho']}")
    errs = r.get("errores_tipo_evento", [])
    print(f"\nErrores de tipo_evento ({len(errs)}):")
    for t in errs:
        print(f"  {t['id']}: {t['esperado']} -> {t['predicho']}")
    for titulo, clave in (
        ("Gate solo donde respondió el proveedor (sin caídas)", "gate_solo_proveedor"),
        ("Gate sin casos ambiguos", "gate_sin_ambiguos"),
        ("Gate solo proveedor y sin ambiguos", "gate_solo_proveedor_sin_ambiguos"),
    ):
        m = r.get(clave)
        if m:
            print(
                f"\n{titulo} ({m['casos']} casos): precisión {m['precision']:.4f} · recall {m['recall']:.4f} · "
                f"F1 {m['f1']:.4f} · TP {m['tp']} FP {m['fp']} FN {m['fn']} TN {m['tn']}"
            )
    caidas = r.get("caidas_regex", [])
    if r["proveedor"] != "regex":
        print(f"\nCaídas a regex ({len(caidas)}):")
        for c in caidas:
            print(f"  {c['id']}: {c['etapa']} · {c['motivo']}")
        for k, n in r.get("caidas_por_motivo", {}).items():
            print(f"  total {k}: {n}")
    print("\n-- Extract (acción + row_number + series) --")
    print(
        f"exactitud por fila {e['exactitud']:.4f} ({e['tp']} de {e['tp'] + e['fn']} esperadas) · "
        f"precisión {e['precision']:.4f} · filas sobrantes {e['fp']}"
    )
    print(f"casos con filas idénticas a la etiqueta: {e['casos_exactos']} de {e['casos']}")
    print(f"caída a regex: gate {_pct(r['caida_regex_gate'])} · extract {_pct(r['caida_regex_extract'])}")
    lat = r["latencia_ms"]
    print(f"\n-- Latencia por caso --\nmedia {lat['media']:.1f} ms · p50 {lat['p50']:.1f} ms · p95 {lat['p95']:.1f} ms")
    if "costo" in r:
        c = r["costo"]
        usd = "costo: no configurado" if c["usd"] is None else f"~USD {c['usd']:.4f} sin caché"
        print(
            f"\n-- Costo (haiku) --\n~{c['tokens_in']:.0f} tokens de entrada, ~{c['tokens_out']:.0f} de salida "
            f"(estimación por caracteres) · {usd}"
        )
        if c["usd"] is None:
            print(f"   (define {ENV_PRECIO_IN} y {ENV_PRECIO_OUT}, USD por millón de tokens)")
    print("\n-- Veredicto --")
    estado = "CUMPLE" if r["cumple"] else "NO CUMPLE"
    print(f"precisión de gate {g['precision']:.4f} vs umbral {r['umbral']:.2f}: {estado}")


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--provider", required=True, choices=PROVEEDORES)
    ap.add_argument("--set", dest="ruta", required=True, help="JSONL del set")
    ap.add_argument("--umbral", type=float, default=UMBRAL_PRECISION_GATE, help="precisión mínima del gate")
    ap.add_argument("--json", dest="salida_json", help="guarda el resumen en este archivo JSON")
    args = ap.parse_args(argv)

    if args.provider == "haiku" and not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY no está definida: haiku no corre. Sin llamadas, sin evaluación.")
        return 0

    try:
        casos = cargar_set(args.ruta)
    except (OSError, SetInvalido) as e:
        print(f"Set inválido: {e}", file=sys.stderr)
        return 2

    resultados, errores = [], []
    for caso in casos:
        try:
            resultados.append(correr_caso(caso, args.provider))
        except Exception as e:  # un caso roto no tira la corrida; se reporta
            errores.append((caso["id"], type(e).__name__))
    if not resultados:
        print("Ningún caso corrió.", file=sys.stderr)
        return 2

    resumen = resumir(resultados, errores, args.provider, args.umbral)
    imprimir(resumen, args.ruta)
    if args.salida_json:
        with open(args.salida_json, "w", encoding="utf-8") as fh:
            json.dump(resumen, fh, ensure_ascii=False, indent=2, default=str)
    return 0 if resumen["cumple"] else 1


if __name__ == "__main__":
    sys.exit(main())
