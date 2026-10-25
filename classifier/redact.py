"""Redacción de PII previa a cualquier proveedor externo (LLM).

``redact(texto)`` es OBLIGATORIA antes de enviar texto de un correo fuera del
proceso. Solo biblioteca estándar, sin modelos ni red. Marcadores estables:

* ``[CORREO]``   direcciones de correo (también ofuscadas: ``x [at] y [dot] com``).
* ``[TELEFONO]`` teléfonos mexicanos (10 dígitos, +52/52/521, espacios, guiones,
  puntos, paréntesis, extensiones).
* ``[FIRMA]``    bloque posterior a una despedida típica, pies legales, "--" y
  "Enviado desde mi ...".
* ``[ID]``       RFC, CURP y nombres de persona detectables sin modelo: junto a
  la despedida, antes de ``<[CORREO]>``, en cabeceras De/Para/Cc y tras
  etiquetas "Contacto:", "Responsable:", etc.

No se tocan (el clasificador los necesita): folios, series, códigos de modelo,
tipos de servicio, palabras de acción y direcciones de punto de venta.

Criterio serie vs. teléfono
---------------------------
* Un token con letras (``ABC123456``, ``FVC14-E1``) jamás es teléfono: solo se
  evalúan secuencias de dígitos con separadores opcionales.
* Corridas de 11+ dígitos pegados (series numéricas de 12 o 18 dígitos) no son
  teléfono. Un número con prefijo ``52``/``521`` sin ``+`` solo cuenta si hay una
  palabra de teléfono antes o va con separadores.
* Un número de exactamente 10 dígitos (con o sin formato) es teléfono salvo que,
  en la misma línea y antes del número, la última palabra clave sea de serie o
  folio (serie, s/n, folio, ticket, activo, modelo, equipo, inventario...) sin
  una palabra de teléfono posterior ("Tel", "Cel", "WhatsApp"...). Un encabezado
  de lista en la línea anterior ("Series:") extiende el contexto.
* Ante la duda sin contexto se redacta (privacidad primero): una tabla de series
  de 10 dígitos sin ninguna etiqueta puede perder datos; las series reales
  del catálogo son de 12/18 dígitos o alfanuméricas y sobreviven.
* RFC/CURP exigen fecha válida (AAMMDD) para no confundirse con series.

Limitaciones: nombres sin despedida ni etiqueta no se detectan sin un modelo;
direcciones fiscales dentro de un bloque de firma se redactan junto al bloque
(el bloque termina en la primera línea con palabras de acción, equipo, serie,
folio, dirección de punto de venta o una línea larga de prosa).
"""
import re
import unicodedata
from typing import Iterable

CORREO = "[CORREO]"
TELEFONO = "[TELEFONO]"
FIRMA = "[FIRMA]"
ID = "[ID]"

_FLAGS = re.IGNORECASE
_LETRA = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
_MAY = "A-ZÁÉÍÓÚÜÑ"


# ---------------------------------------------------------------- normalización
_INVISIBLES = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto).translate(_INVISIBLES)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"&nbsp;|&#160;", " ", texto, flags=_FLAGS)
    texto = re.sub(r"&#64;|&commat;", "@", texto, flags=_FLAGS)
    texto = re.sub(r"[  -   　]", " ", texto)
    return re.sub(r"[ \t]+$", "", texto, flags=re.M)


# ---------------------------------------------------------------------- correos
_EMAIL = re.compile(r"[\w.+%'-]+@[\w-]+(?:\.[\w-]+)+")
_EMAIL_OFUSCADO = re.compile(
    r"[\w.+%'-]+\s*[\[(]\s*(?:at|arroba)\s*[\])]\s*[\w-]+"
    r"(?:(?:\s*[\[(]\s*(?:dot|punto)\s*[\])]\s*|\.)[\w-]+)+",
    _FLAGS,
)


def _correos(t: str) -> str:
    t = _EMAIL.sub(CORREO, t)
    return _EMAIL_OFUSCADO.sub(CORREO, t)


# -------------------------------------------------------------------- teléfonos
_SEP = r"[ \t]?[-–.]?[ \t]?"
_TEL = re.compile(
    r"(?<![\w/@\]])"
    r"(?P<cc>(?:(?:\+|00)[ \t]?)?52(?:[ \t.-]?1)?" + _SEP + r"|0(?:1|4[45])" + _SEP + r")?"
    r"(?P<loc>(?:\(\d{2,3}\)|\d{2,3})" + _SEP + r"\d{3,4}" + _SEP + r"\d{4})"
    r"(?P<ext>[ \t]*(?:ext(?:ensi[oó]n)?\.?|x|#)[ \t]*\.?[ \t]*\d{1,6})?"
    r"(?!\w|[-.]\d)",
    _FLAGS,
)
_TEL_CORTO = re.compile(
    r"\b(?P<kw>tel(?:[eé]fono)?s?\.?|cel(?:ular)?|m[oó]vil|whats?[ ]?app|fax)"
    r"(?P<sep>[ \t.:#-]*)(?P<n>\d{4}[ -]?\d{4}|\d{3}[ -]?\d{4})(?!\w|[-.]\d)",
    _FLAGS,
)
_KW_TEL = re.compile(
    r"\b(?:tel(?:[eé]fono)?s?|cel(?:ular)?|m[oó]vil|whats?[ ]?app|wa|fax|llamar|"
    r"llamada|contacto|marcar|lada|directo|oficina)\b",
    _FLAGS,
)
_KW_SERIE = re.compile(
    r"(?:\b(?:series?|serial(?:es)?|folios?|tickets?|activos?|modelos?|equipos?|"
    r"coolers?|enfriadores?|inventario|etiqueta|marbete|placa|pedido|orden|"
    r"referencia|ref|sku|c[oó]digos?|caso)\b|\bs/n\b|\bn/s\b)",
    _FLAGS,
)


_MARCADORES = re.compile(r"\[(?:CORREO|TELEFONO|ID|FIRMA)\]")


def _linea_antes(s: str, pos: int) -> str:
    # los marcadores no cuentan como palabras clave ("[TELEFONO]" ≠ "tel")
    return _MARCADORES.sub(" ", s[s.rfind("\n", 0, pos) + 1:pos])


def _contexto_serie(s: str, pos: int) -> bool:
    """True si el número en ``pos`` va precedido de una palabra de serie/folio."""
    antes = _linea_antes(s, pos)
    ult_serie = max((m.start() for m in _KW_SERIE.finditer(antes)), default=-1)
    ult_tel = max((m.start() for m in _KW_TEL.finditer(antes)), default=-1)
    if ult_serie >= 0 or ult_tel >= 0:
        return ult_serie > ult_tel
    if antes.strip(" \t,;|-") == "":
        # encabezado de lista en la línea anterior: "Series:" / "Folios:"
        for ult in reversed([_MARCADORES.sub(" ", ln) for ln in s[:pos].split("\n")[:-1] if ln.strip()]):
            if re.fullmatch(r"[\s\w,;|.-]*", ult) and not _KW_SERIE.search(ult) \
                    and not ult.rstrip().endswith(":"):
                continue  # otro elemento de la misma lista
            return bool(_KW_SERIE.search(ult)) and not _KW_TEL.search(ult) \
                and ult.rstrip().endswith(":")
    return False


def _telefono(m: re.Match) -> str:
    s = m.string
    loc = m.group("loc")
    digitos = re.sub(r"\D", "", loc)
    if len(digitos) != 10:
        return m.group(0)
    cc = m.group("cc") or ""
    previo = s[m.start() - 1] if m.start() else ""
    if previo == "-" and m.start() > 1 and s[m.start() - 2].isalnum():
        return m.group(0)  # parte de un código tipo ABC-5551234567
    if _contexto_serie(s, m.start()):
        return m.group(0)
    if cc and "+" not in cc and not cc.startswith("00"):
        # "52"/"521" sin "+": exige formato o palabra de teléfono
        antes = _linea_antes(s, m.start())
        if not (re.search(r"\D", loc + cc) and (" " in cc or "-" in cc or "." in cc)) \
                and not _KW_TEL.search(antes):
            return m.group(0)
    return TELEFONO


def _telefonos(t: str) -> str:
    t = _TEL.sub(_telefono, t)
    return _TEL_CORTO.sub(lambda m: f"{m.group('kw')}{m.group('sep')}{TELEFONO}", t)


# -------------------------------------------------------------------- RFC/CURP
_RFC = re.compile(r"(?<![\w-])[A-ZÑ&]{3,4}(\d{2})(\d{2})(\d{2})[A-Z0-9]{3}(?![\w-])")
_CURP = re.compile(
    r"(?<![\w-])[A-Z]{4}(\d{2})(\d{2})(\d{2})[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d(?![\w-])"
)
_ID_ETIQ = re.compile(
    r"\b(?P<et>RFC|CURP)(?P<sep>[ \t.:#-]*)(?P<v>[A-ZÑ&0-9]{10,18})(?![\w-])", _FLAGS
)


def _fecha_valida(m: re.Match) -> bool:
    mes, dia = int(m.group(2)), int(m.group(3))
    return 1 <= mes <= 12 and 1 <= dia <= 31


def _ids(t: str) -> str:
    t = _ID_ETIQ.sub(lambda m: f"{m.group('et')}{m.group('sep')}{ID}", t)
    t = _CURP.sub(lambda m: ID if _fecha_valida(m) else m.group(0), t)
    return _RFC.sub(lambda m: ID if _fecha_valida(m) else m.group(0), t)


# ---------------------------------------------------------------------- nombres
_PARTICULA = r"(?:de|del|la|las|los|y|e|van|von|da|di)"
_PALABRA = rf"[{_MAY}][{_LETRA}'’.-]*"
_NOMBRE_SIMPLE = rf"{_PALABRA}(?:[ ]+(?:{_PARTICULA}[ ]+)*{_PALABRA}){{0,4}}"
_NOMBRE = rf"(?:{_NOMBRE_SIMPLE}|{_PALABRA}(?:[ ]+{_PALABRA})?[ ]*,[ ]*{_PALABRA}(?:[ ]+{_PALABRA}){{0,2}})"
_NOMBRE_RE = re.compile(rf"{_NOMBRE}")
_ANTES_CORREO = re.compile(
    rf'(?:"[^"\n<>\[\]]{{1,60}}"|{_NOMBRE})[ ]*<[ ]*(?:mailto:)?\[CORREO\][ ]*>'
)
_ETIQ_NOMBRE = re.compile(
    rf"(?im)^(?P<pre>[ \t>]*(?:contacto|responsable|encargad[oa]|solicitante|"
    rf"atenci[oó]n|con atenci[oó]n a|a la atenci[oó]n de)[ \t]*:[ \t]*)"
    rf"(?P<n>{_NOMBRE_SIMPLE})[ \t]*$"
)
_CABECERA = re.compile(
    r"^(?P<pre>(?:De|From|Para|To|Cc|Cco|Bcc)[ \t]*:[ \t]*)(?P<v>.*)$", _FLAGS
)


def _es_nombre(s: str) -> bool:
    s = s.strip()
    return bool(s) and _NOMBRE_RE.fullmatch(s) is not None and not _CONTENIDO.search(s)


def _nombres_en_cabecera(valor: str) -> str:
    partes = valor.split(";")
    salida = []
    for p in partes:
        lead = p[: len(p) - len(p.lstrip())]
        core = p.strip()
        if core and "[" not in core and "@" not in core and _es_nombre(core):
            salida.append(lead + ID)
        else:
            salida.append(p)
    return ";".join(salida)


def _nombres(t: str) -> str:
    t = _ANTES_CORREO.sub(f"{ID} <{CORREO}>", t)
    t = _ETIQ_NOMBRE.sub(lambda m: m.group("pre") + ID, t)
    out = []
    for linea in t.split("\n"):
        pref, cuerpo = _quote_split(linea)
        m = _CABECERA.match(cuerpo)
        if m:
            linea = pref + m.group("pre") + _nombres_en_cabecera(m.group("v"))
        out.append(linea)
    return "\n".join(out)


# ------------------------------------------------------------- firmas y pies
_CITA = re.compile(r"^(?P<p>[ \t]*(?:>[ \t]*)*)(?P<b>.*)$")


def _quote_split(linea: str):
    m = _CITA.match(linea)
    return m.group("p"), m.group("b")


_DESPEDIDAS = (
    r"saludos?[ ]+cordiales|cordiales[ ]+saludos|(?:un[ ]+)?cordial[ ]+saludo|"
    r"reciba[ ]+un[ ]+cordial[ ]+saludo|cordialmente|atentamente|"
    r"a[ ]*t[ ]*e?[ ]*n[ ]*t[ ]*a[ ]*m[ ]*e[ ]*n[ ]*t[ ]*e|atte\.?|attn?\.?|"
    r"sin[ ]+m[aá]s[ ]+por[ ]+el[ ]+momento|"
    r"quedo[ ]+(?:atent[oa]|al[ ]+pendiente)(?:[ ]+a[ ]+(?:sus|tus)[ ]+"
    r"(?:comentarios|[oó]rdenes|indicaciones|respuestas?))?|"
    r"quedamos[ ]+(?:atent[oa]s|al[ ]+pendiente)(?:[ ]+a[ ]+(?:sus|tus)[ ]+"
    r"(?:comentarios|[oó]rdenes|indicaciones|respuestas?))?|"
    r"(?:muchas[ ]+|mil[ ]+)?gracias(?:[ ]+de[ ]+antemano)?(?:[ ]+por[ ]+(?:su|tu|el)[ ]+"
    r"(?:atenci[oó]n|apoyo|ayuda|respuesta|tiempo|colaboraci[oó]n))?|"
    r"que[ ]+tengas?[ ]+(?:un[ ]+)?(?:excelente|buen|lindo|bonito)[ ]+d[ií]a|"
    r"(?:un[ ]+)?saludos?|slds?|sds|salu2|"
    r"(?:best|kind|warm)[ ]+regards|regards|thanks|thank[ ]+you|sincerely"
)
_DESPEDIDA_RE = re.compile(
    rf"^(?P<d>(?:{_DESPEDIDAS}))(?P<punt>[ \t,.;:!¡\-–—]*)(?P<resto>.*)$", _FLAGS
)
_DELIM_FIRMA = re.compile(r"^(?:--|—|___+)[ \t]*$")
_ENVIADO = re.compile(
    r"^(?:enviado[ ]+desde[ ]+mi|enviado[ ]+desde[ ]+(?:outlook|gmail|yahoo|mi)|"
    r"obtener[ ]+outlook|sent[ ]+from[ ]+my|get[ ]+outlook)\b", _FLAGS
)
_LEGAL = re.compile(
    r"^[\W_]*(?:aviso[ ]+de[ ]+privacidad|aviso[ ]+legal|aviso[ ]+de[ ]+confidencialidad|"
    r"(?:este|el)[ ]+(?:correo|mensaje|e-?mail)[ ]+(?:electr[oó]nico[ ]+)?(?:y[ ]+sus[ ]+"
    r"(?:anexos|adjuntos)[ ]+)?(?:es|son|contiene|puede[ ]+contener)[ ]+"
    r"(?:confidencial|privad|informaci[oó]n)|"
    r"este[ ]+mensaje[ ]+y[ ]+sus[ ]+(?:anexos|adjuntos)|"
    r"la[ ]+informaci[oó]n[ ]+(?:contenida|transmitida)[ ]+en[ ]+este|"
    r"confidencialidad\b|disclaimer|"
    r"this[ ]+(?:e-?mail|message)[ ]+(?:and[ ]+any[ ]+attachments[ ]+)?(?:is|are|may[ ]+contain)[ ]+"
    r"(?:confidential|privileged)|confidentiality[ ]+notice)",
    _FLAGS,
)
_FRONTERA = re.compile(
    r"^(?:(?:El|On)\b.*(?:escribi[óo]|wrote)[ ]*:?|.*\b(?:escribi[óo]|wrote)[ ]*:[ ]*|"
    r"(?:De|From|Enviado(?:[ ]+el)?|Sent|Fecha|Date|Asunto|Subject)[ ]*:|"
    r"[-_=*]{3,}[ ]*(?:Original|Mensaje|Forwarded|Reenviado|Begin)|"
    r"_{5,}[ ]*$|begin[ ]+forwarded[ ]+message)",
    _FLAGS,
)
_CONTENIDO = re.compile(
    r"\b(?:alta|altas|baja|bajas|dar[ ]+de[ ]+(?:alta|baja)|retiro|retirar|retirada|"
    r"cancelar|cancelaci[oó]n|cambio|cambiar|instalaci[oó]n|instalar|reubicaci[oó]n|"
    r"reubicar|mantenimiento|reparaci[oó]n|reemplazo|folio|folios|serie|series|modelo|"
    r"activo|tipo[ ]+de[ ]+servicio|cooler|coolers|enfriador|refrigerador|"
    r"punto[ ]+de[ ]+venta|pdv|ticket|solicitud|calle|avenida|colonia|"
    r"domicilio|direcci[oó]n|ubicaci[oó]n)\b|\b(?:av|col|c\.?p)\.?[ ]*(?:\d{5}\b|(?<=\.)|\b)|\bs/n\b",
    _FLAGS,
)
_SERIE_TOKEN = re.compile(
    r"(?<![\w-])(?=[A-Z0-9-]*\d)(?=[A-Z0-9-]*[A-Z])[A-Z0-9-]{6,}(?![\w-])|(?<!\d)\d{11,}(?!\d)"
)
_MARCADOR_SOLO = re.compile(r"^(?:[ \t,.;:|<>()\-]|\[(?:CORREO|TELEFONO|ID|FIRMA)\])*$")
_LINEA_LARGA = 100


def _es_contenido(cuerpo: str) -> bool:
    return "\ue000" in cuerpo or bool(_CONTENIDO.search(cuerpo) or _SERIE_TOKEN.search(cuerpo))


def _es_frontera(cuerpo: str) -> bool:
    return bool(_FRONTERA.match(cuerpo.strip()))


def _resto_despedida(resto: str):
    """Clasifica lo que sigue a la despedida: 'vacio', 'nombre', 'marcador' o None."""
    r = resto.strip(" \t,.;:!¡-–—")
    if not r:
        return "vacio"
    if _MARCADOR_SOLO.match(r):
        return "marcador"
    if r.startswith("[ID]") and _MARCADOR_SOLO.match(r):
        return "marcador"
    if _es_nombre(r) and len(r) <= 60:
        return "nombre"
    return None


def _pref(pref: str) -> str:
    return pref if ">" in pref else ""


def _blancos(partes, desde: int):
    """Líneas en blanco entre la despedida y el inicio del bloque (se conservan)."""
    out = []
    while desde < len(partes) and partes[desde][1].strip() == "":
        out.append(partes[desde][0].rstrip() if ">" in partes[desde][0] else "")
        desde += 1
    return out


def _firmas(t: str) -> str:
    lineas = t.split("\n")
    n = len(lineas)
    partes = [_quote_split(ln) for ln in lineas]
    salida = []
    i = 0

    def bloque(desde: int, profundidad: int, parar_en_contenido: bool) -> int:
        """Índice (exclusivo) de la última línea del bloque que empieza en ``desde``."""
        fin = desde
        j = desde
        while j < n:
            pref, cuerpo = partes[j]
            if cuerpo.strip() == "":
                j += 1
                continue
            if pref.count(">") != profundidad or _es_frontera(cuerpo):
                break
            if cuerpo.strip() == FIRMA:  # bloque ya redactado: lo absorbe y termina
                return j + 1
            if parar_en_contenido and (
                _es_contenido(cuerpo) or len(cuerpo.strip()) > _LINEA_LARGA
            ):
                break
            j += 1
            fin = j
        return fin

    while i < n:
        pref, cuerpo = partes[i]
        prof = pref.count(">")
        c = cuerpo.strip()

        if _LEGAL.match(c):
            fin = bloque(i + 1, prof, False)
            salida.append(f"{_pref(pref)}{FIRMA}")
            i = max(fin, i + 1)
            continue

        if _ENVIADO.match(c):
            salida.append(f"{_pref(pref)}{FIRMA}")
            i += 1
            continue

        if _DELIM_FIRMA.match(c):
            fin = bloque(i + 1, prof, True)
            if fin > i + 1:
                salida.append(lineas[i])
                salida.extend(_blancos(partes, i + 1))
                salida.append(f"{_pref(pref)}{FIRMA}")
                i = fin
                continue

        m = _DESPEDIDA_RE.match(c)
        if m:
            clase = _resto_despedida(m.group("resto"))
            if clase is not None:
                cabeza = f"{m.group('d')}{m.group('punt')}".rstrip()
                if clase == "nombre":
                    cabeza = f"{cabeza} {ID}"
                elif clase == "marcador":
                    cabeza = f"{cabeza} {m.group('resto').strip()}"
                salida.append(f"{pref}{cabeza}")
                fin = bloque(i + 1, prof, True)
                if fin > i + 1:
                    salida.extend(_blancos(partes, i + 1))
                    salida.append(f"{_pref(pref)}{FIRMA}")
                    i = fin
                else:
                    i += 1
                continue

        # despedida al final de una línea de prosa: solo si lo siguiente parece un nombre
        m = re.search(rf"[,.;!]\s*(?:{_DESPEDIDAS})[ \t.!,]*$", c, _FLAGS)
        if m and not _LEGAL.match(c):
            j = i + 1
            while j < n and partes[j][1].strip() == "":
                j += 1
            if j < n and partes[j][0].count(">") == prof:
                sig = partes[j][1].strip()
                if _es_nombre(sig) and len(sig) <= 60:
                    salida.extend(lineas[i:j])
                    fin = bloque(j, prof, True)
                    salida.append(f"{_pref(pref)}{FIRMA}")
                    i = fin
                    continue

        salida.append(lineas[i])
        i += 1
    # bloques [FIRMA] contiguos (mismo nivel de cita) se fusionan: idempotencia
    res = []
    for ln in salida:
        if res and ln.endswith(FIRMA) and res[-1] == ln and ln.strip(" >\t") == FIRMA:
            continue
        res.append(ln)
    return "\n".join(res)


# ---------------------------------------------------------------------- público
def redact(text: str, conservar: Iterable[str] = ()) -> str:
    """Sustituye PII por marcadores estables. Idempotente y sin dependencias.

    ``conservar``: tokens exactos (p. ej. series ya guardadas en thread_ctx) que
    nunca se redactan, aunque parezcan teléfono. Solo coinciden como token
    completo; cualquier otro número sigue las reglas normales.
    """
    if not text:
        return text
    t = _normalizar(text)
    protegidos = []
    for tok in sorted({unicodedata.normalize("NFKC", str(c)).strip() for c in conservar if c},
                      key=len, reverse=True):
        marca = f"\ue000{chr(0xe100 + len(protegidos))}\ue001"
        nuevo = re.sub(rf"(?<![\w]){re.escape(tok)}(?![\w])", marca, t)
        if nuevo != t:
            protegidos.append((marca, tok))
            t = nuevo
    t = _correos(t)
    t = _ids(t)
    t = _telefonos(t)
    t = _nombres(t)
    t = _firmas(t)
    t = re.sub(r"[ \t]+$", "", t, flags=re.M)
    for marca, tok in protegidos:
        t = t.replace(marca, tok)
    return t
