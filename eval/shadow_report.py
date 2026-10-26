"""Reporte del modo sombra (``classifier/shadow.py``) a partir de logs exportados.

    python eval/shadow_report.py shadow.json
    python eval/shadow_report.py shadow.json --json

Lee un archivo de logs exportados y reporta la tasa de acuerdo (es_os y
tipo_evento) global, por cliente, por etapa y por tipo_evento real, la matriz
real vs sombra (tipo_evento), los motivos de caída de la sombra y la latencia
p50/p95 de la sombra. Sin tablas: solo el archivo.

Formatos aceptados (se detectan solos):

* El JSON que exporta ``gcloud logging read --format=json`` (lista de
  entradas con ``textPayload``).
* JSONL: una entrada de Cloud Logging por línea, o un registro por línea.
* Texto: cualquier línea con el prefijo ``[CLASSIFIER_SHADOW]`` seguido del
  JSON (la salida cruda de stdout).

Cómo exportar los logs (Cloud Run), filtrando por el prefijo::

    gcloud logging read \\
      'resource.type="cloud_run_revision" AND textPayload:"[CLASSIFIER_SHADOW]"' \\
      --project=<proyecto> --freshness=7d --limit=100000 --format=json > shadow.json

En la consola de Logs Explorer sirve la misma consulta; "Descargar" en JSON
da un archivo que este script también lee. Las líneas ``[CLASSIFIER_SHADOW][ERROR]``
no son registros y se ignoran.

Los registros repetidos (mismo ``message_id_hash`` y etapa, p. ej. una
notificación duplicada de Graph) cuentan una vez; ``--sin-dedup`` los deja.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Iterable, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eval import metrics  # noqa: E402

PREFIJO = "[CLASSIFIER_SHADOW]"
SIN_SOMBRA = "(caída)"


# ------------------------------------------------------------------ lectura
def _de_texto(texto: str) -> Optional[dict]:
    i = texto.find(PREFIJO + " ")
    if i < 0:
        return None
    try:
        registro = json.loads(texto[i + len(PREFIJO) + 1:].strip())
    except ValueError:
        return None
    return registro if _es_registro(registro) else None


def _es_registro(obj) -> bool:
    return isinstance(obj, dict) and isinstance(obj.get("real"), dict) and isinstance(obj.get("sombra"), dict)


def _de_objeto(obj) -> Optional[dict]:
    """Una entrada de Cloud Logging o un registro ya decodificado."""
    if _es_registro(obj):
        return obj
    if not isinstance(obj, dict):
        return None
    if isinstance(obj.get("textPayload"), str):
        return _de_texto(obj["textPayload"])
    payload = obj.get("jsonPayload")
    if isinstance(payload, dict):
        if _es_registro(payload):
            return payload
        if isinstance(payload.get("message"), str):
            return _de_texto(payload["message"])
    return None


def parsear(texto: str) -> list[dict]:
    """Registros de la sombra en el orden del archivo."""
    contenido = texto.strip()
    if contenido.startswith("["):
        try:
            datos = json.loads(contenido)
        except ValueError:
            datos = None
        if isinstance(datos, list):
            return [r for r in (_de_objeto(o) for o in datos) if r is not None]

    registros = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        registro = None
        if linea.startswith("{"):
            try:
                registro = _de_objeto(json.loads(linea))
            except ValueError:
                registro = None
        if registro is None:
            registro = _de_texto(linea)
        if registro is not None:
            registros.append(registro)
    return registros


def leer(ruta: str) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return parsear(f.read())


def deduplicar(registros: Iterable[dict]) -> tuple[list[dict], int]:
    vistos, salida, repetidos = set(), [], 0
    for r in registros:
        clave = (r.get("message_id_hash"), r.get("etapa"))
        if clave[0] is not None and clave in vistos:
            repetidos += 1
            continue
        vistos.add(clave)
        salida.append(r)
    return salida, repetidos


# ------------------------------------------------------------------ métricas
def _acuerdo(registros: list[dict]) -> dict:
    comparables = [r for r in registros if r.get("coinciden") is not None]
    coinciden = sum(1 for r in comparables if r["coinciden"])
    es_os = sum(1 for r in comparables if r["real"].get("es_os") == r["sombra"].get("es_os"))
    return {
        "correos": len(registros),
        "comparables": len(comparables),
        "sin_sombra": len(registros) - len(comparables),
        "acuerdo": metrics.tasa(coinciden, len(comparables)),
        "acuerdo_es_os": metrics.tasa(es_os, len(comparables)),
    }


def _por(registros: list[dict], clave) -> dict:
    grupos = defaultdict(list)
    for r in registros:
        grupos[str(clave(r))].append(r)
    return {k: _acuerdo(v) for k, v in sorted(grupos.items())}


def reporte(registros: list[dict]) -> dict:
    matriz: dict = defaultdict(Counter)
    for r in registros:
        sombra = r["sombra"].get("tipo_evento") if r.get("coinciden") is not None else None
        matriz[str(r["real"].get("tipo_evento"))][sombra or SIN_SOMBRA] += 1

    latencias = [r["latencia_ms"] for r in registros if isinstance(r.get("latencia_ms"), (int, float))]
    motivos = Counter(r["sombra"].get("motivo_caida") for r in registros if r["sombra"].get("motivo_caida"))
    proveedores = Counter(f"{r['real'].get('proveedor')}->{r['sombra'].get('proveedor')}" for r in registros)

    return {
        "global": _acuerdo(registros),
        "por_cliente": _por(registros, lambda r: r.get("customer")),
        "por_etapa": _por(registros, lambda r: r.get("etapa")),
        "por_tipo_evento": _por(registros, lambda r: r["real"].get("tipo_evento")),
        "matriz": {real: dict(sorted(fila.items())) for real, fila in sorted(matriz.items())},
        "motivos_caida": dict(motivos.most_common()),
        "proveedores": dict(proveedores.most_common()),
        "prompt_version": dict(Counter(str(r.get("prompt_version")) for r in registros).most_common()),
        "latencia_ms": {
            "p50": metrics.percentil(latencias, 50),
            "p95": metrics.percentil(latencias, 95),
            "n": len(latencias),
        },
    }


# ------------------------------------------------------------------ salida
def _pct(valor) -> str:
    return "  -  " if valor is None else f"{valor:.1%}"


def _tabla_acuerdo(titulo: str, grupos: dict) -> list[str]:
    lineas = [f"\n{titulo}", f"  {'':<22}{'correos':>8}{'comp.':>7}{'acuerdo':>9}{'es_os':>8}"]
    for nombre, a in grupos.items():
        lineas.append(
            f"  {nombre:<22}{a['correos']:>8}{a['comparables']:>7}"
            f"{_pct(a['acuerdo']):>9}{_pct(a['acuerdo_es_os']):>8}"
        )
    return lineas


def formatear(rep: dict, repetidos: int = 0) -> str:
    g = rep["global"]
    lineas = [
        "Modo sombra: real vs sombra",
        f"  correos: {g['correos']}  comparables: {g['comparables']}  sin sombra: {g['sin_sombra']}"
        + (f"  repetidos descartados: {repetidos}" if repetidos else ""),
        f"  acuerdo (es_os y tipo_evento): {_pct(g['acuerdo'])}   acuerdo es_os: {_pct(g['acuerdo_es_os'])}",
        f"  latencia sombra: p50 {rep['latencia_ms']['p50']:.0f} ms, p95 {rep['latencia_ms']['p95']:.0f} ms",
        f"  proveedores (real->sombra): {rep['proveedores']}",
        f"  versión de prompt: {rep['prompt_version']}",
    ]
    lineas += _tabla_acuerdo("Por cliente", rep["por_cliente"])
    lineas += _tabla_acuerdo("Por etapa", rep["por_etapa"])
    lineas += _tabla_acuerdo("Por tipo_evento (real)", rep["por_tipo_evento"])

    columnas = sorted({c for fila in rep["matriz"].values() for c in fila})
    lineas.append("\nMatriz real (filas) vs sombra (columnas)")
    lineas.append("  " + f"{'':<20}" + "".join(f"{c[:18]:>20}" for c in columnas))
    for real, fila in rep["matriz"].items():
        lineas.append("  " + f"{real:<20}" + "".join(f"{fila.get(c, 0):>20}" for c in columnas))

    if rep["motivos_caida"]:
        lineas.append("\nMotivos de caída de la sombra")
        for motivo, n in rep["motivos_caida"].items():
            lineas.append(f"  {n:>6}  {motivo}")
    return "\n".join(lineas)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("archivo", help="logs exportados (JSON, JSONL o texto)")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--sin-dedup", action="store_true", help="no descartar registros repetidos")
    args = ap.parse_args(argv)

    try:
        registros = leer(args.archivo)
    except OSError as e:
        print(f"No se pudo leer {args.archivo}: {type(e).__name__}", file=sys.stderr)
        return 2
    repetidos = 0
    if not args.sin_dedup:
        registros, repetidos = deduplicar(registros)
    if not registros:
        print("Sin registros [CLASSIFIER_SHADOW] en el archivo.", file=sys.stderr)
        return 1

    rep = reporte(registros)
    if args.json:
        print(json.dumps({**rep, "repetidos": repetidos}, ensure_ascii=False, indent=2))
    else:
        print(formatear(rep, repetidos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
