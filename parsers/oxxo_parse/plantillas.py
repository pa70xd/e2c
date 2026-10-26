"""Plantillas de correo de Oxxo, leídas con regex por campo etiquetado.

Sin LLM: el resultado es determinista. Tolera acentos, mayúsculas, espacios,
saltos de línea sueltos y líneas extra. Si falta un campo clave (ticket de
mantenimiento o folio de garantía) NO se inventa: el resultado trae
``motivo_revision`` y el parser manda el correo a revisión.

Las etiquetas se buscan sobre una copia del texto sin acentos y del mismo
largo, así que los valores se cortan del texto original (con acentos). Un
valor llega hasta la siguiente etiqueta conocida o el fin de línea, lo que
ocurra primero; solo ``MULTILINEA`` continúa en las líneas siguientes.

Nunca se imprime texto del correo: los resultados solo viajan hacia el
repositorio.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from config.customers.oxxo.reglas_oxxo import (
    LONGITUD_TICKET,
    MOTIVO_SIN_FOLIO,
    MOTIVO_SIN_TICKET,
    MOTIVO_TICKET_INCONSISTENTE,
)

MOTIVO_FOLIO_INCONSISTENTE = "folio_inconsistente"

_FOLD = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def normalizar_texto(texto: str | None) -> str:
    """NFC, saltos de línea unificados y espacios raros convertidos en espacio."""
    t = unicodedata.normalize("NFC", texto or "")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ ​  ﻿\t]", " ", t)


def _fold(texto: str) -> str:
    """Sin acentos y del MISMO largo (los índices valen para el original)."""
    return texto.translate(_FOLD)


# ---------------------------------------------------------------- asuntos

_PREFIJOS = re.compile(r"^\s*((re|rv|fw|fwd)\s*:\s*)+", re.IGNORECASE)
_ETIQUETAS_ASUNTO = re.compile(r"\[[^\]]*\]")


def limpiar_asunto(asunto: str | None) -> str:
    """Asunto sin ``[..]``, ``RE:``/``RV:``/``FW:``, sin acentos y con los
    espacios colapsados."""
    texto = _ETIQUETAS_ASUNTO.sub(" ", normalizar_texto(asunto))
    texto = _PREFIJOS.sub("", texto)
    return " ".join(_fold(texto).split())


_ASUNTO_MANTENIMIENTO = re.compile(r"abierto\s*-\s*asignado", re.IGNORECASE)
_TICKET_ASUNTO = re.compile(r"abierto\s*-\s*asignado\s*[-=~]*\s*>*\s*(\d+)", re.IGNORECASE)
_ASUNTO_SEGUIMIENTO = re.compile(r"seguimiento\s+a\s+folio", re.IGNORECASE)
_FOLIO_ASUNTO = re.compile(r"seguimiento\s+a\s+folio\s*:?\s*(\S+)", re.IGNORECASE)
_ASUNTO_EXCEL = re.compile(
    r"solicitud\s+de\s+orden\s+de\s+servicio\s+oxxo|solicitud\s+de\s+generacion\s+de\s+os",
    re.IGNORECASE,
)


def es_asunto_mantenimiento(asunto: str | None) -> bool:
    return bool(_ASUNTO_MANTENIMIENTO.search(limpiar_asunto(asunto)))


def es_asunto_seguimiento(asunto: str | None) -> bool:
    return bool(_ASUNTO_SEGUIMIENTO.search(limpiar_asunto(asunto)))


def es_asunto_excel_garantias(asunto: str | None) -> bool:
    return bool(_ASUNTO_EXCEL.search(limpiar_asunto(asunto)))


# ---------------------------------------------------------------- etiquetas

# clave -> patrón (sobre texto sin acentos, sin distinguir mayúsculas).
ETIQUETAS_MANTENIMIENTO = {
    "motivo": r"motivo\s*:",
    "propietario": r"representante\s+propietario\s*:",
    "prestador": r"prestador\s+de\s+servicio\s*:",
    "categoria": r"categoria\s*:",
    "falla": r"falla\s+especifica\s*:",
    "ticket": r"(?:el\s+)?numero\s+de\s+ticket(?:\s+es)?\s*:?",
    "prioridad": r"prioridad\s*:",
}

ETIQUETAS_GARANTIAS = {
    "fecha": r"fecha\s+de\s+generacion\s+de\s+folio\s*:",
    "plaza": r"descripcion\s+servicio(?:\s*\(\s*plaza\s*\))?\s*:",
    "cr": r"cr\s+tienda\s*:",
    "reporta": r"nombre\s+de\s+quien\s+reporta\s*:",
    "telefono": r"telefono(?:\s+de\s+contacto)?\s*:",
    "correo": r"correo(?:\s+electronico)?\s*:",
    "marca": r"marca(?:\s*/\s*fabricante(?:\s+del\s+equipo)?)?\s*:",
    "equipo": r"equipo\s*:",
    "modelo": r"modelo\s*:",
    "serie": r"(?:n(?:umero|o\.?|um\.?)\s*)?(?:de\s+)?serie\s*:",
    "diagnostico": r"diagnostico(?:\s+y\s*/\s*o\s+falla)?\s*:",
    "direccion_envio": r"direccion\s+de\s+envio(?:\s+de\s+garantia)?\s*:",
    "folio_mant": r"folio\s+referencia\s+mantenimiento\s*:",
    "mensaje": r"mensaje\s+de\s+seguimiento\s*:",
    "folio": r"folio\s*:",
}

# Campos que pueden seguir en las líneas de abajo (hasta línea en blanco).
MULTILINEA = frozenset({"mensaje", "diagnostico", "falla", "direccion_envio"})
MAX_LINEAS_CONTINUACION = 3


def _compilar(etiquetas: dict[str, str]) -> re.Pattern:
    alternativas = "|".join(f"(?P<{clave}>{patron})" for clave, patron in etiquetas.items())
    return re.compile(rf"(?<![a-z0-9])(?:{alternativas})", re.IGNORECASE)


_RE_MANTENIMIENTO = _compilar(ETIQUETAS_MANTENIMIENTO)
_RE_GARANTIAS = _compilar(ETIQUETAS_GARANTIAS)


def _limpiar_valor(valor: str) -> str:
    return " ".join(valor.split()).strip(" .;,")


def extraer_campos(texto: str | None, patron: re.Pattern) -> dict[str, str]:
    """{clave: valor} de los campos etiquetados. La primera aparición de
    cada etiqueta gana; las etiquetas sin valor no aparecen."""
    t = normalizar_texto(texto)
    f = _fold(t)
    marcas = list(patron.finditer(f))
    campos: dict[str, str] = {}
    for i, m in enumerate(marcas):
        clave = m.lastgroup
        if clave in campos:
            continue
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(t)
        lineas = t[m.end():fin].split("\n")
        valor = lineas[0].strip()
        resto = [linea.strip() for linea in lineas[1:]]
        if not valor:
            valor = next((linea for linea in resto if linea), "")
        elif clave in MULTILINEA:
            extra = []
            for linea in resto[:MAX_LINEAS_CONTINUACION]:
                if not linea:
                    break
                extra.append(linea)
            valor = " ".join([valor, *extra])
        valor = _limpiar_valor(valor)
        if valor:
            campos[clave] = valor
    return campos


# ---------------------------------------------------------------- conversión

def _solo_ticket(valor: str | None) -> str | None:
    """El número tal cual si tiene EXACTAMENTE LONGITUD_TICKET dígitos."""
    if not valor:
        return None
    m = re.search(r"\d+", valor)
    if m and len(m.group(0)) == LONGITUD_TICKET:
        return m.group(0)
    return None


def normalizar_telefono(valor: str | None) -> str | None:
    """Solo dígitos; ``52``/``521`` de lada se quitan. Menos de 10 -> None."""
    digitos = re.sub(r"\D", "", valor or "")
    if len(digitos) in (12, 13) and digitos.startswith(("52", "521")):
        digitos = digitos[-10:]
    return digitos if len(digitos) == 10 else None


_FORMATOS_FECHA = (
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
)


def parsear_fecha(valor: str | None) -> datetime | None:
    texto = " ".join((valor or "").split())
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def _region(prestador: str | None) -> str | None:
    """'REPARE - Centro' -> 'Centro'. Sin prefijo REPARE, el texto completo."""
    if not prestador:
        return None
    partes = re.split(r"\s*[-–—]\s*", prestador, maxsplit=1)
    if len(partes) == 2 and _fold(partes[0]).strip().lower() == "repare":
        return partes[1].strip() or None
    return prestador


# ---------------------------------------------------------------- mantenimiento

_ENCABEZADO_TIENDA = re.compile(
    r"la\s+tienda\s+oxxo\s+(?P<cr>[a-z0-9-]+)\s+(?P<tienda>.+?)\s*,?\s*"
    r"ubicada\s+en\s+(?P<direccion>.+?)\s*,?\s*nos\s+report",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class Mantenimiento:
    """OS nueva de ruta. Folio = ticket, sin serie."""

    ticket: str | None
    cr: str | None = None
    # "<plaza> <nombre tienda>": la plantilla no los separa con un delimitador.
    tienda: str | None = None
    direccion: str | None = None
    motivo: str | None = None
    propietario: str | None = None
    region: str | None = None
    categoria: str | None = None
    falla: str | None = None
    prioridad: str | None = None
    # Código sin PII cuando falta o no cuadra el ticket (va a revisión).
    motivo_revision: str | None = None


def parse_mantenimiento(asunto: str | None, cuerpo: str | None) -> Mantenimiento | None:
    """None si el correo no es la plantilla de mantenimiento."""
    t = normalizar_texto(cuerpo)
    f = _fold(t)
    encabezado = _ENCABEZADO_TIENDA.search(f)
    if not es_asunto_mantenimiento(asunto) and not encabezado:
        return None

    campos = extraer_campos(t, _RE_MANTENIMIENTO)

    m = _TICKET_ASUNTO.search(limpiar_asunto(asunto))
    ticket_asunto = _solo_ticket(m.group(1)) if m else None
    ticket_cuerpo = _solo_ticket(campos.get("ticket"))
    motivo_revision = None
    if ticket_asunto and ticket_cuerpo and ticket_asunto != ticket_cuerpo:
        ticket, motivo_revision = None, MOTIVO_TICKET_INCONSISTENTE
    else:
        ticket = ticket_asunto or ticket_cuerpo
        if ticket is None:
            motivo_revision = MOTIVO_SIN_TICKET

    cr = tienda = direccion = None
    if encabezado:
        cr = t[encabezado.start("cr"):encabezado.end("cr")].upper()
        tienda = _limpiar_valor(t[encabezado.start("tienda"):encabezado.end("tienda")])
        direccion = _limpiar_valor(t[encabezado.start("direccion"):encabezado.end("direccion")])

    prioridad = campos.get("prioridad")
    return Mantenimiento(
        ticket=ticket,
        cr=cr,
        tienda=tienda or None,
        direccion=direccion or None,
        motivo=campos.get("motivo"),
        propietario=campos.get("propietario"),
        region=_region(campos.get("prestador")),
        categoria=campos.get("categoria"),
        falla=campos.get("falla"),
        prioridad=prioridad.upper() if prioridad else None,
        motivo_revision=motivo_revision,
    )


# ---------------------------------------------------------------- garantías

_FOLIO_VALIDO = re.compile(r"[A-Z0-9][A-Z0-9._/-]{2,39}")


def _folio(valor: str | None) -> str | None:
    candidato = (valor or "").strip(" .,;:").upper()
    return candidato if _FOLIO_VALIDO.fullmatch(candidato) else None


@dataclass(frozen=True)
class Seguimiento:
    """'Seguimiento a Folio': escalación de un folio de garantía. El correo
    del solicitante (``Correo Electrónico``) se lee solo para delimitar
    campos: no se conserva."""

    folio: str | None
    fecha: datetime | None = None
    plaza: str | None = None
    cr: str | None = None
    reporta: str | None = None
    telefono: str | None = None
    equipo: str | None = None
    marca: str | None = None
    modelo: str | None = None
    serie: str | None = None
    diagnostico: str | None = None
    direccion_envio: str | None = None
    folio_mantenimiento: str | None = None
    mensaje: str | None = None
    motivo_revision: str | None = None


def parse_seguimiento(asunto: str | None, cuerpo: str | None) -> Seguimiento | None:
    """None si el asunto no es 'Seguimiento a Folio'."""
    if not es_asunto_seguimiento(asunto):
        return None

    campos = extraer_campos(cuerpo, _RE_GARANTIAS)

    m = _FOLIO_ASUNTO.search(limpiar_asunto(asunto))
    folio_asunto = _folio(m.group(1)) if m else None
    folio_cuerpo = _folio(campos.get("folio"))
    motivo_revision = None
    if folio_asunto and folio_cuerpo and folio_asunto != folio_cuerpo:
        folio, motivo_revision = None, MOTIVO_FOLIO_INCONSISTENTE
    else:
        folio = folio_asunto or folio_cuerpo
        if folio is None:
            motivo_revision = MOTIVO_SIN_FOLIO

    return Seguimiento(
        folio=folio,
        fecha=parsear_fecha(campos.get("fecha")),
        plaza=campos.get("plaza"),
        cr=(campos.get("cr") or "").upper() or None,
        reporta=campos.get("reporta"),
        telefono=normalizar_telefono(campos.get("telefono")),
        equipo=campos.get("equipo"),
        marca=campos.get("marca"),
        modelo=campos.get("modelo"),
        serie=campos.get("serie"),
        diagnostico=campos.get("diagnostico"),
        direccion_envio=campos.get("direccion_envio"),
        folio_mantenimiento=campos.get("folio_mant"),
        mensaje=campos.get("mensaje"),
        motivo_revision=motivo_revision,
    )


# ---------------------------------------------------------------- "N OS"

_CUANTAS_OS = re.compile(r"(?<![\w])(\d{1,3})\s*os\b", re.IGNORECASE)


def contar_os_solicitadas(cuerpo: str | None) -> int | None:
    """El 'N' de '4 OS' en el cuerpo. None si no aparece o si el cuerpo
    menciona cantidades distintas (ambiguo: no se valida)."""
    cantidades = {int(n) for n in _CUANTAS_OS.findall(_fold(normalizar_texto(cuerpo)))}
    return cantidades.pop() if len(cantidades) == 1 else None
