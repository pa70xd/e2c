"""Lectura de KOF: encabezado por hoja (visibles y ocultas), alias de columnas,
filas basura y formato en texto plano."""

import re
import unicodedata

import pandas as pd

from config.customers.kof import columns_names as col
from config.customers.kof.reglas_kof import MIN_CLAVES_TEXTO_PLANO
from parsers.core.correo import detectar_tipo_correo as core_detectar_tipo_correo
from parsers.kof_parse import lector_adapter

HOJA = "HOJA"
FILA = "FILA"
ARCHIVO = "ARCHIVO"
TEXTO_PLANO = "(texto plano)"

# Filas con menos celdas llenas son basura (títulos, totales, notas sueltas).
MIN_CELDAS_FILA = 2


def normalizar(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto).strip().upper())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("N°", "NO").replace("Nº", "NO").replace("NO.", "NO")
    texto = " ".join(texto.split())
    return re.sub(r"\s*([/-])\s*", r"\1", texto)


_ALIAS = {normalizar(k): v for k, v in col.NAMES_COLUMNS.items()}


def columna_canonica(encabezado) -> str | None:
    if encabezado is None or pd.isna(encabezado):
        return None
    return _ALIAS.get(normalizar(encabezado))


def _es_encabezado(valores) -> bool:
    canonicas = {columna_canonica(v) for v in valores} - {None}
    return len(canonicas) >= col.MIN_COLUMNAS_ENCABEZADO and bool(canonicas & col.LLAVES_ENCABEZADO)


def _limpia(valor):
    if valor is None or pd.isna(valor):
        return None
    valor = str(valor).strip()
    return None if valor.lower() in ("", "nan", "none") else valor


def tabla_de_hoja(hoja: dict) -> pd.DataFrame | None:
    """Filas de una hoja con columnas canónicas, o None si no hay encabezado."""
    df = hoja["dataframe"]
    for i in range(min(len(df), col.FILAS_BUSQUEDA_ENCABEZADO)):
        if _es_encabezado(df.iloc[i].tolist()):
            break
    else:
        return None

    columnas = {}
    for posicion, encabezado in enumerate(df.iloc[i].tolist()):
        canonica = columna_canonica(encabezado)
        # Si dos encabezados caen en la misma columna gana el primero.
        if canonica and canonica not in columnas.values():
            columnas[posicion] = canonica

    filas = []
    for j in range(i + 1, len(df)):
        crudo = df.iloc[j].tolist()
        if sum(_limpia(v) is not None for v in crudo) < MIN_CELDAS_FILA:
            continue
        fila = {canonica: _limpia(crudo[p]) for p, canonica in columnas.items()}
        fila[ARCHIVO] = hoja["name"]
        fila[HOJA] = hoja["hoja"]
        fila[FILA] = j + 1  # renglón de Excel (1-based)
        filas.append(fila)

    return pd.DataFrame(filas, columns=list(columnas.values()) + [ARCHIVO, HOJA, FILA])


def unir_hojas(hojas: list[dict]) -> pd.DataFrame:
    """Todas las hojas con encabezado reconocido, sin filas repetidas entre
    hojas (KOF copia el encabezado en hojas ocultas)."""
    tablas = [t for t in (tabla_de_hoja(h) for h in hojas) if t is not None and not t.empty]
    if not tablas:
        return pd.DataFrame()
    df = pd.concat(tablas, ignore_index=True)
    datos = [c for c in df.columns if c not in (ARCHIVO, HOJA, FILA)]
    return df.drop_duplicates(subset=datos, keep="first").reset_index(drop=True)


def tabla_de_texto(texto: str | None) -> pd.DataFrame:
    """Formato en texto plano: líneas "CLAVE: valor" con los mismos alias.
    Exige el folio y al menos MIN_CLAVES_TEXTO_PLANO claves reconocidas."""
    fila = {}
    for linea in (texto or "").splitlines():
        if ":" not in linea:
            continue
        clave, valor = linea.split(":", 1)
        canonica = columna_canonica(clave)
        if canonica and canonica not in fila and _limpia(valor):
            fila[canonica] = _limpia(valor)

    if col.FOLIO not in fila or len(fila) < MIN_CLAVES_TEXTO_PLANO:
        return pd.DataFrame()

    fila.update({ARCHIVO: None, HOJA: TEXTO_PLANO, FILA: None})
    return pd.DataFrame([fila])


class KOF_READER:

    @staticmethod
    async def get_tabla(client, user_id, mail_id, mail=None) -> tuple[pd.DataFrame, bool]:
        """(filas, hubo_excel). Excel adjuntos (todas las hojas); sin Excel y
        con ``mail``, el cuerpo en texto plano."""
        hojas = await lector_adapter.leer_adjuntos(client, user_id, mail_id)
        if hojas:
            return unir_hojas(hojas), True
        body = getattr(getattr(mail, "unique_body", None), "content", None)
        return tabla_de_texto(body) if mail is not None else pd.DataFrame(), False

    detectar_tipo_correo = staticmethod(core_detectar_tipo_correo)
