"""Cobertura del catálogo de modelos sobre los modelos históricos de los clientes.

SOLO LECTURA. Reporta, por cliente, el % de modelos por motivo de
``parsers.core.modelos.resolver_modelo`` y el top 30 de modelos no encontrados.

El modelo crudo SÍ se guarda: ``cooler_request.modelo`` (viene del Excel del
cliente). Dos fuentes:

* ``--csv ruta``: CSV exportado con columnas ``cliente,modelo[,n]`` (no toca la base).
* PostgreSQL (default): ``eval/querys/modelos_historicos.sql`` con las mismas
  protecciones de ``eval/backfill.py`` (``SET TRANSACTION READ ONLY``,
  ``validar_select``, rollback al cerrar). ``--tablas prod`` exige
  ``--confirmo-solo-lectura``.

Candado de PII: no se leen correos ni cuerpos, solo el campo modelo. Los modelos
del top 30 se imprimen únicamente si parecen un código (A-Z, 0-9, espacio y
``-./_``, máx. 40 caracteres); cualquier otro texto libre cuenta como
``<texto libre>`` y no se imprime.
"""

import argparse
import collections
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eval.backfill import (  # noqa: E402
    TABLAS,
    ConsultaNoPermitida,
    LectorPG,
    abrir_pg_real,
)
from parsers.core.modelos import MOTIVOS, NO_EN_CATALOGO, indice_defecto  # noqa: E402

_CODIGO = re.compile(r"[A-Z0-9][A-Z0-9 \-./_]{0,39}")
LIBRE = "<texto libre>"
TOP = 30


def leer_csv(ruta: str) -> list[tuple[str, str | None, int]]:
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        faltan = {"cliente", "modelo"} - set(lector.fieldnames or [])
        if faltan:
            raise ValueError(f"al CSV le faltan columnas: {sorted(faltan)}")
        return [
            (f["cliente"].strip().lower() or "(sin cliente)", f["modelo"], int(f.get("n") or 1))
            for f in lector
        ]


def leer_pg(pg: LectorPG, desde: str) -> list[tuple[str, str | None, int]]:
    return [
        ((r["cliente"] or "(sin cliente)").strip().lower(), r["modelo"], int(r["n"]))
        for r in pg.consultar("modelos_historicos", desde)
    ]


def _mostrable(modelo) -> str:
    texto = str(modelo or "").strip().upper()
    return texto if _CODIGO.fullmatch(texto) else LIBRE


def calcular(filas, indice=None) -> dict:
    indice = indice or indice_defecto()
    por_cliente = collections.defaultdict(collections.Counter)
    no_encontrados = collections.Counter()
    for cliente, modelo, n in filas:
        r = indice.resolver(modelo)
        por_cliente[cliente][r.motivo] += n
        if r.motivo == NO_EN_CATALOGO:
            no_encontrados[_mostrable(modelo)] += n
    clientes = {}
    for cliente, cuenta in sorted(por_cliente.items()):
        total = sum(cuenta.values())
        clientes[cliente] = {
            "total": total,
            **{m: {"n": cuenta[m], "pct": round(100 * cuenta[m] / total, 1)} for m in MOTIVOS},
        }
    return {
        "clientes": clientes,
        "top_no_encontrados": [{"modelo": m, "n": n} for m, n in no_encontrados.most_common(TOP)],
    }


def imprimir(res: dict, fuente: str) -> None:
    print(f"== Cobertura de modelos (solo lectura) · fuente={fuente} ==")
    for cliente, d in res["clientes"].items():
        partes = " · ".join(f"{m} {d[m]['pct']}% ({d[m]['n']})" for m in MOTIVOS)
        print(f"{cliente} (n={d['total']}): {partes}")
    print(f"\nTop {TOP} modelos no encontrados:")
    for i, x in enumerate(res["top_no_encontrados"], 1):
        print(f"{i:>2}. {x['modelo']}  ({x['n']})")


def parsear(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--csv", help="CSV exportado (cliente,modelo[,n]); no abre la base")
    ap.add_argument("--tablas", choices=("qa", "prod"), default="qa")
    ap.add_argument("--confirmo-solo-lectura", action="store_true", help="obligatorio con --tablas prod")
    ap.add_argument("--desde", default="2000-01-01", help="YYYY-MM-DD (solo base)")
    ap.add_argument("--json", help="guarda el resumen completo en esta ruta")
    args = ap.parse_args(argv)
    if not args.csv and args.tablas == "prod" and not args.confirmo_solo_lectura:
        ap.error("--tablas prod exige --confirmo-solo-lectura (usa un usuario de base de solo lectura si existe)")
    return args


def main(argv=None, *, abrir_pg=None) -> int:
    try:
        args = parsear(argv)
    except SystemExit as e:
        return int(e.code or 0)
    pg = None
    try:
        if args.csv:
            filas, fuente = leer_csv(args.csv), f"csv:{os.path.basename(args.csv)}"
        else:
            pg = LectorPG((abrir_pg or abrir_pg_real)(), TABLAS[args.tablas])
            filas, fuente = leer_pg(pg, args.desde), f"postgres:{args.tablas}"
    except ConsultaNoPermitida as e:
        print(f"ABORTADO (solo lectura): {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"Falló la lectura: {type(e).__name__}", file=sys.stderr)
        return 4
    finally:
        if pg is not None:
            pg.cerrar()
    res = calcular(filas)
    imprimir(res, fuente)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
