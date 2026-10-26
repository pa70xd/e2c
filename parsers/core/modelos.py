"""Resolución de modelo -> (categoría, línea) contra el catálogo de modelos.

Sin fuzzy matching ni LLM: un modelo mal asignado es peor que uno vacío.
Orden: exacto (trim + mayúsculas) -> normalizado (sin espacios, guiones,
puntos ni barras) -> vacío con motivo.
"""

import logging
import re
from typing import NamedTuple

import pandas as pd

log = logging.getLogger(__name__)

EXACTO = "exacto"
NORMALIZADO = "normalizado"
NO_EN_CATALOGO = "no_en_catalogo"
AMBIGUO = "ambiguo"
SIN_MODELO = "sin_modelo"
MOTIVOS = (EXACTO, NORMALIZADO, NO_EN_CATALOGO, AMBIGUO, SIN_MODELO)

_SEPARADORES = re.compile(r"[\s\-./\\]+")
_PLACEHOLDER = re.compile(r"X+")
_VACIOS = {"", "NA", "N/A", "NAN", "NONE", "NULL"}


class Resultado(NamedTuple):
    modelo: str | None
    categoria: str | None
    linea: str | None
    motivo: str


def _limpiar(texto) -> str:
    if texto is None or (not isinstance(texto, str) and pd.isna(texto)):
        return ""
    return str(texto).strip().upper()


def normalizar(texto) -> str:
    return _SEPARADORES.sub("", _limpiar(texto))


class IndiceModelos:
    """Índice inverso modelo -> {(categoría, línea)}, exacto y normalizado."""

    def __init__(self, catalogo: dict):
        exacto: dict[str, set] = {}
        normalizado: dict[str, set] = {}
        nombres: dict[str, str] = {}  # clave normalizada -> grafía canónica
        for categoria, lineas in catalogo.items():
            for linea, modelos in lineas.items():
                for m in modelos:
                    clave = _limpiar(m)
                    # el placeholder del catálogo no es un modelo
                    if not clave or _PLACEHOLDER.fullmatch(clave):
                        continue
                    par = (categoria, linea)
                    exacto.setdefault(clave, set()).add(par)
                    norm = normalizar(clave)
                    normalizado.setdefault(norm, set()).add(par)
                    if norm not in nombres or clave < nombres[norm]:
                        nombres[norm] = clave
        self._exacto = exacto
        self._normalizado = normalizado
        self._nombres = nombres
        self._avisados: set[str] = set()

    def __len__(self):
        return len(self._exacto)

    def candidatos(self, texto) -> set:
        return self._exacto.get(_limpiar(texto), set())

    def resolver(self, texto) -> Resultado:
        clave = _limpiar(texto)
        if clave in _VACIOS:
            return Resultado(None, None, None, SIN_MODELO)

        pares = self._exacto.get(clave)
        if pares:
            if len(pares) == 1:
                (cat, lin), = pares
                return Resultado(clave, cat, lin, EXACTO)
            return self._ambiguo(clave, pares)

        norm = normalizar(clave)
        pares = self._normalizado.get(norm)
        if pares:
            if len(pares) == 1:
                (cat, lin), = pares
                return Resultado(self._nombres[norm], cat, lin, NORMALIZADO)
            return self._ambiguo(clave, pares)

        return Resultado(None, None, None, NO_EN_CATALOGO)

    def _ambiguo(self, clave, pares) -> Resultado:
        if clave not in self._avisados:
            self._avisados.add(clave)
            log.warning(
                "modelo ambiguo %r: candidatos %s",
                clave,
                " ; ".join(f"{c} / {l}" for c, l in sorted(pares)),
            )
        return Resultado(None, None, None, AMBIGUO)


_indice_defecto: IndiceModelos | None = None


def indice_defecto() -> IndiceModelos:
    """Índice del catálogo de modelos, construido una vez por proceso."""
    global _indice_defecto
    if _indice_defecto is None:
        from config.customers.danone.model_line_cat import catalog

        _indice_defecto = IndiceModelos(catalog)
    return _indice_defecto


def resolver_modelo(texto, indice: IndiceModelos | None = None) -> Resultado:
    return (indice or indice_defecto()).resolver(texto)


def normalizar_id(valor) -> str | None:
    """Serie o activo: trim, mayúsculas; vacío / NA / N/A -> None."""
    limpio = _limpiar(valor)
    return None if limpio in _VACIOS else limpio


def llenar_modelo(duck_conn, table: str, col_activo: str, col_serie: str) -> None:
    """Llena ACTIVO_GEN, SERIE_GEN, MODELO_GEN, CATEGORIA_GEN, LINEA_GEN y
    MODELO_GEN_MOTIVO de la tabla de trabajo. Idempotente: recalcula siempre
    desde las columnas originales."""
    for columna in (
        "ACTIVO_GEN", "SERIE_GEN", "MODELO_GEN",
        "CATEGORIA_GEN", "LINEA_GEN", "MODELO_GEN_MOTIVO",
    ):
        duck_conn.execute(
            f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{columna}" VARCHAR'
        )

    cols = {r[0] for r in duck_conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
        [table],
    ).fetchall()}
    sel = lambda c: f'CAST("{c}" AS VARCHAR)' if c in cols else "CAST(NULL AS VARCHAR)"

    filas = duck_conn.execute(
        f'SELECT rowid, {sel("MODELO")}, {sel(col_activo)}, {sel(col_serie)} FROM "{table}"'
    ).fetchall()
    if not filas:
        return

    indice = indice_defecto()
    datos = []
    for rowid, modelo, activo, serie in filas:
        r = indice.resolver(modelo)
        datos.append((
            rowid, normalizar_id(activo), normalizar_id(serie),
            r.modelo, r.categoria, r.linea, r.motivo,
        ))

    df = pd.DataFrame(datos, columns=[
        "rowid", "activo", "serie", "modelo", "categoria", "linea", "motivo",
    ])
    duck_conn.register("_modelos_resueltos", df)
    try:
        duck_conn.execute(f'''
            UPDATE "{table}" AS t
            SET "ACTIVO_GEN" = m.activo,
                "SERIE_GEN" = m.serie,
                "MODELO_GEN" = m.modelo,
                "CATEGORIA_GEN" = m.categoria,
                "LINEA_GEN" = m.linea,
                "MODELO_GEN_MOTIVO" = m.motivo
            FROM _modelos_resueltos AS m
            WHERE t.rowid = m.rowid
        ''')
    finally:
        duck_conn.unregister("_modelos_resueltos")
