"""Lector común de adjuntos de hoja de cálculo (.xlsx, .xls, .xlsm, .ods).

Reglas:
  * El encabezado se detecta por coincidencia con un vocabulario de columnas que
    recibe el cliente, no por posición (puede estar en la fila 1 a la 4; los
    encabezados agrupados y repetidos de arriba no puntúan).
  * Las celdas de encabezado se normalizan (saltos de línea, acentos,
    mayúsculas, espacios alrededor de "/").
  * Una hoja oculta se lee según ``hojas_ocultas``:
      "si_coinciden" (default): solo si su encabezado coincide con el de una hoja
                                visible de datos (KOF); los catálogos ocultos
                                (Imbera/Torrey) no coinciden y se ignoran.
      "nunca":                  se ignoran todas las ocultas.
      "siempre":                se leen las ocultas con encabezado detectado.
  * Las filas basura (vacías, con una sola celda llena, sin ninguna columna
    clave, o el encabezado repetido) se descartan y se cuentan en
    ``Tabla.descartes`` y en el log, sin imprimir valores.

Uso::

    tablas = leer_adjunto(nombre, bytes, vocabulario, claves=("NO SERIE", "MODELO"))
    for t in tablas:
        t.hoja, t.fila_encabezado, t.columnas, t.df, t.descartes

El índice de ``Tabla.df`` es el número de fila de la hoja (1 = primera fila), así
que se puede citar el renglón original. Todas las celdas son ``str`` (o ``None``
si están vacías), como el resto de los lectores.
"""

from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Iterable

import pandas as pd

EXTENSIONES_SOPORTADAS = (".xlsx", ".xls", ".xlsm", ".ods")
MODOS_HOJAS_OCULTAS = ("si_coinciden", "nunca", "siempre")

# Filas, desde arriba, donde se busca el encabezado.
MAX_FILAS_ENCABEZADO = 15


class AdjuntoIlegible(ValueError):
    """El archivo no es una hoja de cálculo que se pueda abrir."""


class DataFrameLector(pd.DataFrame):
    """DataFrame de celdas ``str`` o ``None`` (nunca NaN).

    Con pandas 3, ``iterrows`` reconstruye cada fila como Series y, al inferir
    el dtype ``str`` por defecto, convierte los ``None`` en NaN. Aquí se fuerza
    ``object`` para que los faltantes lleguen como ``None`` (p. ej. a
    PostgreSQL). ``itertuples``, ``to_dict`` e ``iloc`` ya conservan ``None``.
    """

    @property
    def _constructor(self):
        return DataFrameLector

    def iterrows(self):
        columnas = self.columns
        for indice, valores in zip(self.index, self.to_numpy(dtype=object)):
            yield indice, pd.Series(valores, index=columnas, dtype=object, name=indice)


@dataclass
class Tabla:
    archivo: str
    hoja: str
    oculta: bool
    fila_encabezado: int  # 1 = primera fila de la hoja
    columnas: list[str]  # normalizadas, únicas, en el orden de la hoja
    df: pd.DataFrame
    descartes: dict[str, int] = field(default_factory=dict)

    def filas(self) -> list[dict]:
        """Filas como dicts ``{columna: str | None}``, con la fila de la hoja en ``_fila``."""
        return [{"_fila": i, **fila} for i, fila in zip(self.df.index, self.df.to_dict("records"))]


def es_adjunto_soportado(nombre: str) -> bool:
    nombre = nombre or ""
    return (
        not nombre.startswith("~$")
        and Path(nombre).suffix.lower() in EXTENSIONES_SOPORTADAS
    )


def normalizar_encabezado(valor) -> str:
    """"DELEGACIÓN/\\nMunicipio/ Ciudad" -> "DELEGACION/MUNICIPIO/CIUDAD"."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = " ".join(texto.upper().split())  # \n, \r, \t y espacios repetidos
    return re.sub(r"\s*/\s*", "/", texto)


def _lleno(valor) -> bool:
    return valor is not None and not pd.isna(valor) and str(valor).strip() != ""


def _contenido(contenido: bytes) -> bytes:
    # Algunos adjuntos llegan en Base64 (mismo criterio que GEN_READER).
    if contenido.startswith(b"UEs"):
        return base64.b64decode(contenido)
    return contenido


def _hojas_ocultas_ods(contenido: bytes) -> set[str]:
    from odf.opendocument import load
    from odf.style import Style, TableProperties
    from odf.table import Table

    doc = load(BytesIO(contenido))
    estilos = set()
    for estilo in doc.automaticstyles.getElementsByType(Style):
        if estilo.getAttribute("family") != "table":
            continue
        for props in estilo.getElementsByType(TableProperties):
            if props.getAttribute("display") == "false":
                estilos.add(estilo.getAttribute("name"))
    return {
        t.getAttribute("name")
        for t in doc.spreadsheet.getElementsByType(Table)
        if t.getAttribute("stylename") in estilos
    }


def _ocultas(excel: pd.ExcelFile, contenido: bytes) -> set[str]:
    motor = excel.engine
    if motor == "openpyxl":
        return {h.title for h in excel.book.worksheets if h.sheet_state != "visible"}
    if motor == "xlrd":
        return {h.name for h in excel.book.sheets() if h.visibility != 0}
    if motor == "odf":
        return _hojas_ocultas_ods(contenido)
    return set()


def _fila_encabezado(crudo: pd.DataFrame, vocabulario: set[str], minimo: int) -> int | None:
    """Índice (0-based) de la fila con más coincidencias distintas, o None."""
    mejor, mejor_puntaje = None, 0
    for i in range(min(MAX_FILAS_ENCABEZADO, len(crudo))):
        celdas = {normalizar_encabezado(v) for v in crudo.iloc[i] if _lleno(v)}
        puntaje = len(celdas & vocabulario)
        if puntaje > mejor_puntaje:  # en empate gana la fila de arriba
            mejor, mejor_puntaje = i, puntaje
    return mejor if mejor_puntaje >= minimo else None


def _nombres_unicos(celdas) -> list[str]:
    vistos: dict[str, int] = {}
    nombres = []
    for i, celda in enumerate(celdas):
        nombre = normalizar_encabezado(celda)
        base = nombre or f"SIN_NOMBRE_{i + 1}"
        vistos[base] = vistos.get(base, 0) + 1
        nombres.append(base if vistos[base] == 1 else f"{base}_{vistos[base]}")
    return nombres


def _construir(
    crudo: pd.DataFrame, i_enc: int, claves: set[str]
) -> tuple[list[str], pd.DataFrame, dict[str, int]]:
    fila_enc = list(crudo.iloc[i_enc])
    nombres = _nombres_unicos(fila_enc)
    textos = [normalizar_encabezado(c) for c in fila_enc]
    cuerpo = crudo.iloc[i_enc + 1 :].copy()
    cuerpo.columns = nombres

    # Columnas sin nombre y sin un solo dato: ruido de formato.
    vacias = [
        n for n in nombres
        if n.startswith("SIN_NOMBRE_") and not cuerpo[n].map(_lleno).any()
    ]
    idx = [i for i, n in enumerate(nombres) if n not in vacias]
    nombres = [nombres[i] for i in idx]
    textos = [textos[i] for i in idx]
    cuerpo = cuerpo[nombres]
    claves_presentes = [n for n in nombres if n in claves]

    descartes = {"vacias": 0, "una_celda": 0, "encabezado_repetido": 0, "sin_clave": 0}
    conservar = []
    for fila in cuerpo.itertuples(index=False):
        llenas = [_lleno(v) for v in fila]
        n = sum(llenas)
        if n == 0:
            descartes["vacias"] += 1
        elif n == 1:
            descartes["una_celda"] += 1
        elif all(normalizar_encabezado(v) == t for v, t, ok in zip(fila, textos, llenas) if ok):
            descartes["encabezado_repetido"] += 1
        elif claves_presentes and not any(
            ok for nom, ok in zip(nombres, llenas) if nom in claves_presentes
        ):
            descartes["sin_clave"] += 1
        else:
            conservar.append(True)
            continue
        conservar.append(False)

    cuerpo.index = range(i_enc + 2, i_enc + 2 + len(cuerpo))  # fila de la hoja (1-based)
    cuerpo = cuerpo[conservar]
    cuerpo = cuerpo.map(lambda v: str(v).strip() if _lleno(v) else None).astype(object)
    cuerpo = cuerpo.where(cuerpo.notna(), None)
    cuerpo = DataFrameLector(cuerpo)
    return nombres, cuerpo, descartes


def leer_adjunto(
    nombre: str,
    contenido: bytes,
    vocabulario: Iterable[str],
    hojas_ocultas: str = "si_coinciden",
    *,
    claves: Iterable[str] = (),
    min_coincidencias: int = 2,
) -> list[Tabla]:
    """Lee las hojas de datos de un adjunto. Ver el docstring del módulo.

    ``vocabulario``: nombres de columna esperados (se normalizan igual que el
    archivo). ``claves``: subconjunto cuyos valores identifican una fila real
    (serie, modelo, folio); una fila sin ninguna se descarta. Si ninguna clave
    existe en la tabla, esa regla no se aplica. ``min_coincidencias``: columnas
    del vocabulario que debe tener la fila para ser encabezado.
    """
    if hojas_ocultas not in MODOS_HOJAS_OCULTAS:
        raise ValueError(f"hojas_ocultas debe ser uno de {MODOS_HOJAS_OCULTAS}")
    if not es_adjunto_soportado(nombre):
        raise ValueError(f"Extensión no soportada: {Path(nombre or '').suffix!r}")

    vocab = {normalizar_encabezado(v) for v in vocabulario} - {""}
    claves_n = {normalizar_encabezado(c) for c in claves} - {""}
    contenido = _contenido(contenido)

    try:
        excel = pd.ExcelFile(BytesIO(contenido))
        ocultas = _ocultas(excel, contenido)
        hojas = []
        for hoja in excel.sheet_names:
            oculta = hoja in ocultas
            if oculta and hojas_ocultas == "nunca":
                continue
            crudo = excel.parse(sheet_name=hoja, header=None, dtype=str)
            i_enc = _fila_encabezado(crudo, vocab, min_coincidencias)
            if i_enc is None:
                print(f"[LECTOR] {nombre} hoja={hoja!r}: sin encabezado reconocible; se ignora")
                continue
            hojas.append((hoja, oculta, crudo, i_enc))
    except AdjuntoIlegible:
        raise
    except Exception as e:  # archivo corrupto, motor ausente, etc.
        raise AdjuntoIlegible(f"No se pudo abrir {nombre!r}: {type(e).__name__}") from e

    tablas = []
    for hoja, oculta, crudo, i_enc in hojas:
        columnas, df, descartes = _construir(crudo, i_enc, claves_n)
        tablas.append(Tabla(nombre, hoja, oculta, i_enc + 1, columnas, df, descartes))

    if hojas_ocultas == "si_coinciden":
        referencia = [set(t.columnas) for t in tablas if not t.oculta]
        tablas = [t for t in tablas if not t.oculta or set(t.columnas) in referencia]

    for t in tablas:
        print(
            f"[LECTOR] {nombre} hoja={t.hoja!r} oculta={t.oculta} "
            f"encabezado=fila {t.fila_encabezado} filas={len(t.df)} descartes={t.descartes}"
        )
    return tablas
