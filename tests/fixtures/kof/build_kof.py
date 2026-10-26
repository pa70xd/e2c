"""Genera los Excel y correos SINTÉTICOS de KOF.

    python tests/fixtures/kof/build_kof.py            # reescribe tests/fixtures/kof/
    python tests/fixtures/kof/build_kof.py --check    # sale 1 si lo versionado difiere

Todo es inventado: solo se tomó la ESTRUCTURA de los correos reales (que no se
comparten). Dominios ``example.com``, teléfonos 555-01xx.

  * reporte_falla.xlsx: "Reportes por falla de enfriador". Hoja visible
    REPORTE con 4 filas buenas, 1 sin ID de detallista y 6 filas basura de una
    celda; 7 hojas ocultas con el MISMO encabezado y 12 filas válidas más (una
    es venta de extensión).
  * bitacora.xlsx: corte diario de movimientos, 6 filas (3 Cambio de Equipo,
    2 Cobertura, 1 Equipo Adicional) -> 9 registros.
  * respuesta_bitacora.xlsx: REPARE responde la bitácora ya desdoblada (9
    filas) con la columna OS llena.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

from openpyxl import Workbook, load_workbook

OUT = Path(__file__).resolve().parent
_FIXED = dt.datetime(2026, 1, 1, 0, 0, 0)

FALLA_HEADERS = [
    "MODELO", "No SERIE", "FALLA", "DELEGACION/MUNICIPIO/CIUDAD",
    "No CLIENTE DETALLISTA- CONCATENADO", "ID DISTRIBUIDOR", "ID DETALLISTA",
    "CEDIS/DISTRIBUIDORA/ SUCURSAL", "OBSERVACIONES", "SOLICITUD DE SERVICIO",
    "ACTIVO/PLACA", "OS REPARE",
]

BITACORA_HEADERS = [
    "Folio (.Net)", "Tipo de Movimiento", "ID Detallista", "Nombre", "Dirección",
    "CP", "Municipio", "CEDIS", "Modelo a instalar", "Serie a instalar",
    "SAP a instalar", "Modelo a retirar", "Serie a retirar", "SAP a retirar",
    "Teléfono", "Observaciones",
]

FALLAS = ("NO ENFRIA", "LO CONGELA", "NO ENCIENDE")


def _wb() -> Workbook:
    wb = Workbook()
    wb.properties.creator = "e2c-tests"
    wb.properties.created = _FIXED
    wb.properties.modified = _FIXED
    return wb


def _falla_row(n: int, *, falla=None, solicitud="SERVICIO", detallista=True) -> list:
    return [
        f"VR-{10 + n % 3}", f"KS{n:07d}", falla or FALLAS[n % 3], "MUNICIPIO EJEMPLO",
        f"9{n:04d}-DET{n:04d}", f"DIS{n % 2 + 1:03d}", f"DET{n:04d}" if detallista else None,
        f"CEDIS EJEMPLO {n % 2 + 1}", f"Observación {n}", solicitud, f"PL{n:06d}", None,
    ]


def build_reporte_falla(path: Path) -> None:
    wb = _wb()
    ws = wb.active
    ws.title = "REPORTE"
    ws.append(["REPORTE DE FALLAS DE ENFRIADORES"])
    ws.append(FALLA_HEADERS)
    for n in (1, 2):
        ws.append(_falla_row(n))
    ws.append(["Nota: favor de atender"])          # basura
    ws.append([None, None, "x"])                   # basura
    for n in (3, 4):
        ws.append(_falla_row(n))
    ws.append(_falla_row(5, detallista=False))     # rechazada: sin ID detallista
    for basura in (["TOTAL"], [None, "4"], ["-"], ["Revisado"]):
        ws.append(basura)

    ocultas = [(6, 7), (8, 9), (10, 11), (12, 13), (14, 15), (16,), (17,)]
    for i, numeros in enumerate(ocultas, start=1):
        oculta = wb.create_sheet(f"Hoja{i}")
        oculta.sheet_state = "hidden"
        oculta.append(FALLA_HEADERS)
        for n in numeros:
            if n == 16:
                oculta.append(_falla_row(n, falla="CAMBIO", solicitud="VENTA DE EXTENSION"))
            else:
                oculta.append(_falla_row(n))
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def _bitacora_rows() -> list[list]:
    filas = []
    tipos = ["Cambio de Equipo", "Cobertura", "Cambio de Equipo", "Equipo Adicional", "Cambio de Equipo", "Cobertura"]
    for n, tipo in enumerate(tipos, start=1):
        cambio = tipo == "Cambio de Equipo"
        filas.append([
            f"80{n:04d}", tipo, f"DET{100 + n:04d}", f"Tienda Ejemplo {n}", f"Calle Ficticia {n}",
            "06000", "MUNICIPIO EJEMPLO", "CEDIS EJEMPLO 1",
            "VR-20", f"KN{n:07d}", f"SAPN{n:05d}",
            "VR-10" if cambio else None, f"KV{n:07d}" if cambio else None, f"SAPV{n:05d}" if cambio else None,
            f"55501{n:05d}", f"Movimiento {n}",
        ])
    return filas


def build_bitacora(path: Path) -> None:
    wb = _wb()
    ws = wb.active
    ws.title = "Bitacora"
    ws.append(BITACORA_HEADERS)
    for fila in _bitacora_rows():
        ws.append(fila)
    wb.save(path)


def build_respuesta_bitacora(path: Path) -> None:
    """Desdoblada: cada Cambio de Equipo es una fila de instalación y otra de
    retiro (serie en "Serie a retirar"). Una OS vacía."""
    wb = _wb()
    ws = wb.active
    ws.title = "Bitacora"
    ws.append(BITACORA_HEADERS + ["OS"])
    os_n = 0
    for fila in _bitacora_rows():
        cambio = fila[1] == "Cambio de Equipo"
        instalacion = list(fila)
        instalacion[1] = "Instalación" if cambio else fila[1]
        instalacion[11:14] = [None, None, None]
        os_n += 1
        ws.append(instalacion + [None if os_n == 4 else f"4030{os_n:05d}"])
        if cambio:
            retiro = list(fila)
            retiro[1] = "Retiro"
            retiro[8:11] = [None, None, None]
            os_n += 1
            ws.append(retiro + [f"4030{os_n:05d}"])
    wb.save(path)


CORREOS = {
    "init_falla": {
        "subject": "Reportes por falla de enfriador",
        "body": "Buen día.\nSe envían los reportes por falla de enfriador.\nSaludos,\nContacto KOF Ejemplo",
    },
    "init_bitacora": {
        "subject": "Bitácora Plaza Ejemplo 02/03/2026",
        "body": "me apoyan con esta carga",
    },
    "init_texto": {
        "subject": "Proyecto especial instalación eléctrica",
        "body": (
            "Buen día, me apoyan con lo siguiente:\n"
            "Folio (.Net): 900001\n"
            "Nombre: Tienda Ejemplo Proyecto\n"
            "Dirección: Calle Ficticia 300\n"
            "Municipio: MUNICIPIO EJEMPLO\n"
            "CEDIS: CEDIS EJEMPLO 2\n"
            "Observaciones: instalación eléctrica en áreas generales\n"
            "Teléfono: 5550100300\n"
            "Saludos"
        ),
    },
    "inbound": {
        "subject": "RE: Bitácora Plaza Ejemplo 02/03/2026",
        "body": "Agrego un equipo más, me apoyan con esta carga",
    },
    "outbound": {
        "subject": "RE: BITACORA Plaza Ejemplo 02/03/2026",
        "body": "Se adjunta la bitácora con las OS generadas.\nOperador REPARE Ejemplo",
    },
    "comandos": {
        "ayuda": "bot.help",
        "estatus": "bot.status",
        "cancelar": "bot.cancelar",
        "finalizar": "bot.cerrar",
        "global": "bot.global",
    },
}


def build_all(out: Path = OUT) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    build_reporte_falla(out / "reporte_falla.xlsx")
    build_bitacora(out / "bitacora.xlsx")
    build_respuesta_bitacora(out / "respuesta_bitacora.xlsx")
    (out / "correos.json").write_text(json.dumps(CORREOS, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _dump(path: Path) -> list:
    wb = load_workbook(path)
    try:
        return [(ws.title, ws.sheet_state, [list(r) for r in ws.iter_rows(values_only=True)]) for ws in wb.worksheets]
    finally:
        wb.close()


def check(out: Path = OUT) -> list[str]:
    diffs = []
    with tempfile.TemporaryDirectory() as tmp:
        build_all(Path(tmp))
        for built in sorted(Path(tmp).iterdir()):
            current = Path(out) / built.name
            if not current.exists():
                diffs.append(f"falta {built.name}")
            elif built.suffix == ".xlsx":
                if _dump(built) != _dump(current):
                    diffs.append(f"difiere {built.name}")
            elif built.read_bytes() != current.read_bytes():
                diffs.append(f"difiere {built.name}")
    return diffs


if __name__ == "__main__":
    if "--check" in sys.argv:
        problemas = check()
        print("\n".join(problemas))
        sys.exit(1 if problemas else 0)
    build_all()
    print(f"Fixtures de KOF regenerados en {OUT}")
