"""Conciliación outbound desde el TEXTO del correo de REPARE ("Comparto
orden generada: 123456"), además de la del Excel. Se activa por cliente
(PerfilLayout.conciliar_texto); no cambia nada de los demás clientes.

Asignación (sin adivinar):
  1. Si el texto menciona series de filas PENDING y hay tantas OS como
     series mencionadas, se emparejan en orden de aparición.
  2. Si no menciona series, hay una sola OS y una sola fila PENDING, va a
     esa fila.
  3. En cualquier otro caso no se asigna nada (queda para revisión).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from config.customers.imbera import reglas_imbera as R
from parsers.imbera_parse.lector import normalizar


@dataclass
class ResultadoTexto:
    # "os": hay OS y se asignaron; "ambiguo": hay OS pero no se pudo
    # asignar; "no_os": estatus sin OS ("espera de pieza") o nada.
    tipo: str
    asignaciones: list[tuple[int, str]] = field(default_factory=list)
    os_encontradas: list[str] = field(default_factory=list)


def extraer_os(texto: str | None) -> list[str]:
    """OS de las frases "orden(es) generada(s): <n>[, <n>...]"."""
    encontradas = []
    for m in R.PATRON_OS_TEXTO.finditer(normalizar(texto)):
        for numero in R.PATRON_NUMERO_OS.findall(m.group(1)):
            if numero not in encontradas:
                encontradas.append(numero)
    return encontradas


def _posiciones(texto: str, valores: list[str]) -> list[tuple[int, str]]:
    posiciones = []
    for valor in valores:
        m = re.search(rf"(?<![\w-]){re.escape(valor)}(?![\w-])", texto)
        if m:
            posiciones.append((m.start(), valor))
    return sorted(posiciones)


def conciliar_texto(texto: str | None, filas: list[dict]) -> ResultadoTexto:
    """`filas`: cooler_request de la solicitud (row_number,
    serie_fabricante, serie_dnn_bnf, status)."""
    texto_n = normalizar(texto)
    os_list = extraer_os(texto)
    if not os_list:
        return ResultadoTexto("no_os")

    pendientes = [f for f in filas if (f.get("status") or "").upper() == "PENDING"]
    serie_a_fila = {}
    for f in pendientes:
        for serie in (f.get("serie_fabricante"), f.get("serie_dnn_bnf")):
            if serie:
                serie_a_fila.setdefault(normalizar(serie), f["row_number"])

    mencionadas = [s for _, s in _posiciones(texto_n, list(serie_a_fila))]
    if mencionadas:
        if len(mencionadas) == len(os_list):
            return ResultadoTexto(
                "os",
                [(serie_a_fila[s], os_value) for s, os_value in zip(mencionadas, os_list)],
                os_list,
            )
        return ResultadoTexto("ambiguo", os_encontradas=os_list)

    if len(os_list) == 1 and len(pendientes) == 1:
        return ResultadoTexto("os", [(pendientes[0]["row_number"], os_list[0])], os_list)

    return ResultadoTexto("ambiguo", os_encontradas=os_list)


def es_estatus_sin_os(texto: str | None) -> bool:
    """Respuesta de REPARE con estatus ("espera de pieza") y sin OS."""
    return bool(R.PATRON_ESTATUS_REPARE.search(normalizar(texto))) and not extraer_os(texto)
