"""Redacción de PII previa a cualquier proveedor externo (LLM).

``redact(texto)`` es OBLIGATORIA antes de enviar texto de un correo fuera del
proceso. Solo biblioteca estándar, sin modelos ni red. Marcadores estables:

* ``[CORREO]``   direcciones de correo (también ofuscadas: ``x [at] y [dot] com``).
* ``[TELEFONO]`` teléfonos mexicanos (10 dígitos, +52/52/521, espacios, guiones,
  puntos, paréntesis, extensiones).
* ``[FIRMA]``    bloque posterior a una despedida típica, pies legales, "--" y
  "Enviado desde mi ...".
* ``[ID]``       RFC, CURP y nombres de persona detectables sin modelo: junto a
  la despedida, antes de ``<[CORREO]>`` o ``[mailto:...]``, en cabeceras
  De/Para/Cc (también minúsculas, entre comillas, "Apellido, Nombre", en la línea
  siguiente o a mitad de línea), en "El ... <nombre> escribió:", tras etiquetas de
  campo ("Contacto:", "Nombre de quien reporta:", "Representante Propietario:"...),
  en tablas aplanadas y en saludos ("Buen día Juan,", "Juan buenos días",
  "Estimada Ana:", "@Juan Pérez").
* ``[UBICACION]`` coordenadas decimales/DMS, "Latitud:/Longitud:" y URLs de mapas
  (maps.google, goo.gl/maps, maps.app.goo.gl).
* ``[MONTO]``    importes con ``$`` ("$ 5,000", "$5,000.00 MXN") o "5,000 pesos".
* ``[DIRECCION]`` valor de "Dirección de envío/entrega/garantía/fiscal:", de
  "ubicada en <calle...>" y de columnas calle/colonia/CP de tablas.

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

Criterio v2 (nombres y direcciones)
-----------------------------------
* El valor se redacta y la etiqueta se conserva ("Contacto: [ID]").
* Etiquetas "fuertes" (nombre de quien reporta, representante, contacto,
  responsable, solicitante...) redactan también minúsculas; las "débiles"
  (atención, técnico, gerente...) exigen mayúsculas y que lo siguiente sea un
  separador, y nunca una oración ("Atención: El dominio x.com.mx va a...").
* Jamás se redactan: folios, tickets, series, modelos, IDs tipo IMB-070526_4960,
  tipos de servicio, cadenas/clientes (OXXO, Jumex, KOF...), razones sociales
  (S.A. de C.V.) ni valores genéricos ("tienda", "pendiente", "N/A").
* Nombre de tienda que contiene el nombre de una persona ("Abarrotes Juan Pérez"):
  se conserva mientras vaya como dato de punto de venta; si está tras una etiqueta
  de persona ("Contacto:"), saludo, firma o cabecera se redacta (privacidad primero).
* Direcciones: solo las etiquetadas como de envío/entrega/garantía/facturación/fiscal/
  particular, "ubicada en" con señas de calle y columnas calle/colonia/CP. Un
  "Dirección:" o "Domicilio:" sin calificar y las líneas de punto de venta se conservan
  porque el clasificador las usa.
* Tablas aplanadas: N encabezados conocidos en N líneas + N valores en las N líneas
  siguientes (una sola fila); filas con barras o tabuladores por columna.
* Saludos: se ignoran palabras de grupo ("equipo", "todos", "soporte"...) y cadenas;
  tras "Buen día," con coma solo se redacta si lo siguiente va en mayúscula.

Limitaciones: nombres sin despedida ni etiqueta no se detectan sin un modelo;
direcciones fiscales dentro de un bloque de firma se redactan junto al bloque
(el bloque termina en la primera línea con palabras de acción, equipo, serie,
folio, dirección de punto de venta o una línea larga de prosa).
"""
import re
import unicodedata
from typing import Iterable

REDACT_VERSION = 2  # candado del modo sombra: 1 = redacción original, 2 = F1-F9

CORREO = "[CORREO]"
TELEFONO = "[TELEFONO]"
FIRMA = "[FIRMA]"
ID = "[ID]"
MONTO = "[MONTO]"
UBICACION = "[UBICACION]"
DIRECCION = "[DIRECCION]"

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


_TLD = r"(?:com|mx|net|org|edu|gob|gov|info|biz|co|es|us|io|ar|br|cl|pe|uk|de|fr|it|ca)"
# vista previa de Outlook: "juan. perez@ example. com" (solo si hay un espacio de por medio)
_EMAIL_ESPACIADO = re.compile(
    r"[\w+%'-]+(?:\.[ \t]*[\w+%'-]+){0,3}[ \t]*@[ \t]*[\w-]+(?:\.[ \t]*[\w-]+)*?\.[ \t]*" + _TLD
    + r"\b(?:\.[ \t]*" + _TLD + r"\b)?",
    _FLAGS,
)


def _correo_espaciado(m: re.Match) -> str:
    t = m.group(0)
    local, _, dominio = t.partition("@")
    if re.search(r"[ \t]", dominio) or local != local.rstrip(" \t"):
        return CORREO
    # espacio solo en el usuario ("juan. perez@example.com"): si empieza con
    # mayúscula es una oración ("Atte. ana@..."), no se toca aquí
    if re.search(r"\.[ \t]", local) and local == local.lower():
        return CORREO
    return t


def _correos(t: str) -> str:
    t = _EMAIL_ESPACIADO.sub(_correo_espaciado, t)
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


_MARCADORES = re.compile(r"\[(?:CORREO|TELEFONO|ID|FIRMA|MONTO|UBICACION|DIRECCION)\]")


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


# ------------------------------------------------------- ubicaciones y montos
_URL_MAPA = re.compile(
    r"(?:https?://)?(?:(?:www\.)?maps\.google\.[\w.]+|(?:www\.)?google\.[a-z.]+/maps|"
    r"goo\.gl/maps|maps\.app\.goo\.gl|maps\.apple\.com|(?:www\.)?waze\.com/ul)"
    r"[^\s<>\"')\]]*",
    _FLAGS,
)
_COORD_PAR = re.compile(
    r"(?<![\w.])(?P<a>-?\d{1,3}\.\d{2,})[ \t]*[,;/][ \t]*(?P<b>-?\d{1,3}\.\d{2,})(?![\w.]|\.\d)"
)
_COORD_ETIQ = re.compile(
    r"\b(?P<et>latitud|longitud|lat|lng|lon|coordenadas?|coords?|gps)(?P<sep>[ \t.:=#]*)"
    r"(?P<v>-?\d{1,3}(?:\.\d+)?[ \t]*°?(?:[ \t]*[,;/][ \t]*-?\d{1,3}(?:\.\d+)?[ \t]*°?)?)(?![\w])",
    _FLAGS,
)
_COORD_DMS = re.compile(
    r"\b\d{1,3}[°º][ \t]*\d{1,2}['′’][ \t]*\d{1,2}(?:\.\d+)?[\"″”]?[ \t]*[NSEWO]\b"
    r"(?:[ ,;]*\d{1,3}[°º][ \t]*\d{1,2}['′’][ \t]*\d{1,2}(?:\.\d+)?[\"″”]?[ \t]*[NSEWO]\b)?"
)
_MONTO_RE = re.compile(
    r"(?:\b(?:USD|MXN|US|MN)[ \t]*)?\$[ \t]*\d{1,3}(?:[, ]\d{3})+(?:\.\d{1,2})?(?:[ \t]*(?:MXN|M\.N\.|MN|USD|pesos|dlls|d[oó]lares)(?!\w))?"
    r"|(?:\b(?:USD|MXN|US|MN)[ \t]*)?\$[ \t]*\d+(?:\.\d{1,2})?(?:[ \t]*(?:MXN|M\.N\.|MN|USD|pesos|dlls|d[oó]lares)(?!\w))?"
    r"|(?<![\w.,])\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?[ \t]*(?:pesos|MXN|USD|M\.N\.|dlls|d[oó]lares)\b"
    r"|(?<![\w.,])\d+(?:\.\d{1,2})?[ \t]*(?:pesos|MXN|USD)\b",
    _FLAGS,
)


def _coord_par(m: re.Match) -> str:
    a, b = m.group("a"), m.group("b")
    da, db = len(a.split(".")[1]), len(b.split(".")[1])
    fa, fb = float(a), float(b)
    if abs(fa) > 90 or abs(fb) > 180:
        return m.group(0)
    mexico = 14 <= fa <= 33 and -119 <= fb <= -86
    if mexico or (da >= 3 and db >= 3):
        return UBICACION
    return m.group(0)


def _coord_etiqueta(m: re.Match) -> str:
    if m.group("et").lower() in ("lat", "lng", "lon", "gps") and "." not in m.group("v"):
        return m.group(0)
    return f"{m.group('et')}{m.group('sep')}{UBICACION}"


def _ubicaciones(t: str) -> str:
    t = _URL_MAPA.sub(UBICACION, t)
    t = _COORD_DMS.sub(UBICACION, t)
    t = _COORD_ETIQ.sub(_coord_etiqueta, t)
    return _COORD_PAR.sub(_coord_par, t)


def _montos(t: str) -> str:
    return _MONTO_RE.sub(MONTO, t)


# ---------------------------------------------------------------------- nombres
_PARTICULA = r"(?:de|del|la|las|los|y|e|van|von|da|di)"
_PALABRA = rf"[{_MAY}][{_LETRA}'’.-]*"
_NOMBRE_SIMPLE = rf"{_PALABRA}(?:[ ]+(?:{_PARTICULA}[ ]+)*{_PALABRA}){{0,4}}"
_NOMBRE = rf"(?:{_NOMBRE_SIMPLE}|{_PALABRA}(?:[ ]+{_PALABRA})?[ ]*,[ ]*{_PALABRA}(?:[ ]+(?:{_PARTICULA}[ ]+)*{_PALABRA}){{0,3}})"
_NOMBRE_RE = re.compile(rf"{_NOMBRE}")
_ANTES_CORREO = re.compile(
    rf'(?:"[^"\n<>\[\]]{{1,60}}"|{_NOMBRE})[ ]*<[ ]*(?:mailto:)?\[CORREO\][ ]*>'
)
def _es_nombre(s: str) -> bool:
    s = s.strip()
    return bool(s) and _NOMBRE_RE.fullmatch(s) is not None and not _CONTENIDO.search(s)


# ------------------------------------------------- nombres en contexto (F1,F2,F4,F5,F8)
_CADENAS = {
    "oxxo", "jumex", "kof", "femsa", "imbera", "repare", "emerald", "solkos", "coca", "cola",
    "coca-cola", "pepsi", "bimbo", "danone", "bachoco", "sigma",
}
_EMPRESA = re.compile(
    r"\bS\.?[ ]?A\.?(?![\w])|\bC\.?[ ]?V\.?(?![\w])|\bS\.?[ ]?de[ ]?R\.?[ ]?L\b|\bS\.?[ ]?A\.?[ ]?B\b",
    _FLAGS,
)
_NO_NOMBRE = {
    "na", "n/a", "no aplica", "ninguno", "ninguna", "pendiente", "sin datos", "sin dato", "s/d",
    "no", "si", "tienda", "la tienda", "el cliente", "cliente", "encargado", "encargada", "gerente",
    "mismo", "el mismo", "no proporcionado", "no indica", "no registrado", "ver correo", "ver abajo",
    "mantenimiento", "soporte", "proveedor", "servicio", "ventas", "logistica", "almacen",
    "administracion", "sistemas", "operaciones", "por definir", "por confirmar", "definir", "confirmar",
    "la misma", "sin contacto", "sin responsable", "tecnico", "supervisor", "jefe", "dueno", "usuario",
}
_NO_SALUDO = {
    "equipo", "equipos", "team", "todos", "todas", "todo", "soporte", "mesa", "ayuda", "companeros",
    "companeras", "colegas", "amigos", "amigas", "gente", "clientes", "cliente", "usuarios", "usuario",
    "proveedor", "proveedores", "area", "departamento", "administrador", "administradores",
    "sistema", "sistemas", "servicio", "servicios", "favor", "buen", "buena", "buenos", "buenas", "dia",
    "dias", "tarde", "tardes", "noche", "noches", "hola", "gracias", "saludos", "estimado",
    "estimada", "estimados", "estimadas", "apreciable", "apreciables", "atencion", "a", "de", "del",
    "la", "el", "los", "las", "un", "una", "por", "para", "que", "como", "ya", "se", "le", "les",
    "nos", "me", "mi", "su", "sus", "tu", "tus", "y", "e", "o", "u", "en", "con", "sin", "si", "no",
    "ok", "nuevamente", "nuevo", "reciban", "reciba", "espero", "solicito", "adjunto", "envio",
    "queria", "quisiera", "necesito", "tenemos", "cordial", "cordiales", "mucho", "muchas", "mil",
    "buenisimos", "hello", "hi", "hey", "dear", "all", "everyone", "there", "gerencia", "direccion",
    "logistica", "ventas", "operaciones", "facturacion", "cobranza", "garantias", "mantenimiento",
    "tienda", "sucursal", "gente", "mundo", "amigo", "jefe", "jefa", "licenciado", "ingeniero",
    "doctor", "maestro", "maestra", "profe", "ingeniera", "licenciada", "doctora",
} | _CADENAS
_TITULOS = {"sr", "sra", "srita", "lic", "ing", "dr", "dra", "arq", "mtro", "mtra", "c", "don",
            "dona", "senor", "senora", "senorita", "prof", "profa", "tec", "cp"}
_PART_RE = re.compile(rf"^{_PARTICULA}$", _FLAGS)


def _plano(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip(".,;:!¡?\"'“”")


def _es_cap(tok: str) -> bool:
    return bool(re.match(rf"[{_MAY}]", tok))


_ETQ_CORTA = {"tel", "tels", "telefono", "cel", "celular", "movil", "whatsapp", "wa", "correo", "email",
              "e-mail", "mail", "ext", "extension", "fax", "puesto", "cargo", "area", "depto"}


def _corrida_nombre(r: str, fuerte: bool, max_palabras: int = 6, cola_libre: bool = False):
    """(inicio, fin) del nombre al comienzo de ``r`` o None.

    ``fuerte``: la etiqueta garantiza que el valor es una persona (acepta minúsculas);
    si no, exige palabras con mayúscula inicial y que lo siguiente sea un separador.
    """
    i = len(r) - len(r.lstrip(" \t\"“"))
    cuerpo = r[i:]
    toks = []
    prev = 0
    for m in re.finditer(rf"[{_LETRA}][{_LETRA}'’.\-]*|,", cuerpo):
        if cuerpo[prev:m.start()].strip(" \t\"“”"):
            break
        toks.append((m.start(), m.end(), m.group()))
        prev = m.end()
    ok = []
    for ini, fin, tok in toks:
        if tok == ",":
            if not ok or ok[-1][2] == ",":
                break
            ok.append((ini, fin, tok))
            continue
        sig = cuerpo[fin:fin + 1]
        plano = _plano(tok)
        if ok and _ETQ_SIGUE.match(cuerpo, ini):
            break
        if sig.isdigit() or sig == "_":
            break  # código pegado a letras (IMB-070526_4960), no un nombre
        if sig == ":" or plano in _ETQ_CORTA or "." in tok.rstrip(".") or _CONTENIDO.search(tok):
            break
        if tok[0].isdigit() or len(ok) >= max_palabras:
            break
        if not fuerte and not (_es_cap(tok) or _PART_RE.match(tok)):
            break
        ok.append((ini, fin, tok))
    while ok and (ok[-1][2] == "," or _PART_RE.match(ok[-1][2]) or _plano(ok[-1][2]) in ("y", "e", "o")):
        ok.pop()
    palabras = [x for x in ok if x[2] != ","]
    if not palabras:
        return None
    if not fuerte:
        if _plano(palabras[0][2]) in ("el", "la", "los", "las", "un", "una") or _plano(palabras[0][2]) in _NO_SALUDO:
            return None
        tail = cuerpo[ok[-1][1]:].lstrip(" \t\"”")
        if not cola_libre and tail and tail[0] not in ",;|[(<-–" and not tail.startswith("/"):
            return None
    texto = cuerpo[ok[0][0]:ok[-1][1]]
    if _plano(texto) in _NO_NOMBRE or _EMPRESA.search(texto) or any(_plano(p[2]) in _CADENAS for p in palabras):
        return None
    fin = ok[-1][1] + (1 if cuerpo[ok[-1][1]:ok[-1][1] + 1] in "\"”" else 0)
    ini = ok[0][0]
    if ini > 0 and cuerpo[ini - 1] in "\"“":
        ini -= 1
    return i + ini, i + fin


# etiquetas de campo -> tipo: 'p' persona, 'd' dirección
_ET_PERSONA_FUERTE = (
    r"nombre(?:[ ]+(?:completo|(?:de|del)[ ]+(?:la[ ]+)?(?:quien[ ]+(?:reporta|solicita|atiende|recibe|llama)|"
    r"persona(?:[ ]+que[ ]+(?:reporta|solicita|atiende|recibe|llama))?|reportante|solicitante|contacto|"
    r"responsable|encargad[oa]|propietari[oa]|representante|usuari[oa]|t[eé]cnico|cliente|titular)))?"
    r"|quien[ ]+(?:reporta|solicita|atiende|recibe|llama)|persona[ ]+que[ ]+(?:reporta|solicita|atiende|recibe|llama)"
    r"|reportante|solicitante|contacto(?:[ ]+(?:en[ ]+tienda|de[ ]+la[ ]+tienda))?|responsable|"
    r"encargad[oa]|propietari[oa]|representante(?:[ ]+(?:legal|propietari[oa]))?"
)
_ET_PERSONA_DEBIL = (
    r"atenci[oó]n|con[ ]+atenci[oó]n[ ]+a|a[ ]+la[ ]+atenci[oó]n[ ]+de|titular|gerente|"
    r"administrador[a]?|supervisor[a]?|jefe|due[ñn][oa]|vendedor[a]?|t[eé]cnico|operador[a]?|"
    r"usuari[oa]|capturista|firma"
)
_ET_DIRECCION = (
    r"(?:direcci[oó]n|domicilio)[ ]+(?:de|del|para)[ ]+(?:env[ií]o|entrega|garant[ií]a|facturaci[oó]n|"
    r"recolecci[oó]n)(?:[ ]+(?:de|del)[ ]+(?:la[ ]+)?(?:garant[ií]a|equipo|cooler|producto))?"
    r"|(?:direcci[oó]n|domicilio)[ ]+(?:fiscal|particular|personal|completo)"
    r"|env[ií]o[ ]+a|enviar[ ]+a"
)
_ETQ_SIGUE = re.compile(
    rf"(?:{_ET_PERSONA_FUERTE}|{_ET_PERSONA_DEBIL}|{_ET_DIRECCION}|tel(?:[eé]fono)?|cel(?:ular)?|correo|"
    r"e-?mail|folio|ticket|serie|modelo|fecha|asunto|tipo[ ]+de[ ]+servicio|direcci[oó]n|domicilio|cliente|"
    r"tienda|pdv|para|cc|enviado|de)[ \t]*:",
    _FLAGS,
)
_CAMPO = re.compile(
    rf"(?:^|(?<=[|;\t])|(?<=[ ]{{2}}))[ \t]*(?:[-*•][ \t]*)?"
    rf"(?P<et>(?P<f>{_ET_PERSONA_FUERTE})|(?P<w>{_ET_PERSONA_DEBIL})|(?P<d>{_ET_DIRECCION})|(?P<s>direcci[oó]n|domicilio))"
    rf"[ \t]*(?::|：|[ \t]-[ \t]|(?=\t))[ \t]*",
    _FLAGS,
)
_PERSONA_EN_TIENDA = re.compile(
    rf"(?P<pre>[ \t]-[ \t]+)(?P<n>[{_LETRA}][{_LETRA}'’.\-]*(?:[ ]+[{_LETRA}][{_LETRA}'’.\-]*){{1,4}})"
    r"(?P<post>[ \t]*,[ \t]*(?i:ubicad[oa]s?[ ]+en)\b)"
)


_DESCRIPTOR_TIENDA = {"tienda", "plaza", "sucursal", "bodega", "centro", "zona", "norte", "sur", "oriente",
                      "poniente", "almacen", "cedis", "cd", "local", "region", "regional", "pdv", "cr"}


def _persona_en_tienda(m: re.Match) -> str:
    n = m.group("n")
    palabras = n.split()
    if any(_plano(w) in _CADENAS or _CONTENIDO.search(w) or _plano(w) in _DESCRIPTOR_TIENDA for w in palabras):
        return m.group(0)
    return m.group("pre") + ID + m.group("post")


_UBICADA = re.compile(
    r"\b(?P<et>(?:est[aá][ ]+)?ubicad[oa]s?[ ]+en|se[ ]+encuentra[ ]+en[ ]+la[ ]+direcci[oó]n)[ \t]+(?!\[)", _FLAGS
)
_SENAS_CALLE = re.compile(
    r"\b\d{5}\b|\b(?:lt|mz|lote|manzana|local|int|no|num)\.?[ ]*\d|(?-i:\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+[ ]+(?:No\.?[ ]*|#[ ]*)?\d+\b)|\b(?:calle|av|avenida|blvd|boulevard|bulevar|col|colonia|carretera|calzada|privada|prolongaci[oó]n|"
    r"fracc|fraccionamiento|km|esquina|esq|entre|s/n|c\.?p)\b",
    _FLAGS,
)
_ABREV = {"col", "av", "blvd", "calz", "c", "cp", "no", "num", "mz", "lt", "esq", "ing", "lic", "sr",
          "sra", "int", "ext", "km", "fracc", "edo", "prol", "pte", "nte", "ote", "depto", "dpto",
          "loc", "ctra", "cd", "mun", "del", "dr", "dra", "pbl", "s", "n", "priv", "andador", "cto"}
_CORTE_DIR = re.compile(
    r"\.(?=[ \t]+[A-ZÁÉÍÓÚÑ¡¿])|[;|\t]|[ \t]+(?:para|favor|solicito|solicitamos|donde|porque|cuyo|"
    r"cuya|ya[ ]que|quien|el[ ]cual|se[ ]|le[ ]|les[ ]|nos[ ]|con[ ]el[ ]|con[ ]la[ ])",
    _FLAGS,
)


def _fin_direccion(r: str) -> int:
    """Longitud del tramo de dirección al comienzo de ``r`` (0 si no hay)."""
    for m in _CORTE_DIR.finditer(r):
        if m.group().startswith("."):
            previo = re.search(r"([A-Za-zÁ-ú]+)$", r[:m.start()])
            if previo and _plano(previo.group(1)) in _ABREV:
                continue
        r = r[:m.start()]
        break
    return len(r.rstrip(" \t,."))


_VACIO = re.compile(r"^[\s\-–—_.:/]*$|^(?:n/?a|s/?d|no aplica|ninguno|ninguna|pendiente|sin dato(?:s)?)\.?$", _FLAGS)


def _campos_linea(linea: str):
    """Redacta el valor de los campos etiquetados de una línea (la etiqueta se conserva).

    Devuelve (línea, pendiente); ``pendiente`` es 'p'/'d' si una etiqueta de persona o
    dirección quedó sin valor y este seguirá en la línea siguiente."""
    linea = _PERSONA_EN_TIENDA.sub(_persona_en_tienda, linea)
    pendiente = None
    out = []
    cur = pos = 0
    while True:
        m = _CAMPO.search(linea, pos)
        mu = _UBICADA.search(linea, pos)
        if mu and (not m or mu.start() < m.start()):
            ini = mu.end()
            n = _fin_direccion(linea[ini:])
            if n and _SENAS_CALLE.search(linea[ini:ini + n]):
                out.append(linea[cur:ini] + DIRECCION)
                cur = pos = ini + n
            else:
                pos = ini
            continue
        if not m:
            break
        ini = m.end()
        resto = linea[ini:]
        if m.group("d") or m.group("s"):
            if not resto.strip():
                pendiente = "d" if m.group("d") else None
            n = _fin_direccion(resto)
            if n and not resto.lstrip().startswith("[") and not _VACIO.match(resto[:n].strip()) \
                    and (m.group("d") or _SENAS_CALLE.search(resto[:n])):
                out.append(linea[cur:ini] + DIRECCION)
                cur = pos = ini + n
                continue
        else:
            if not resto.strip():
                pendiente = "p"
            r = None if resto.lstrip().startswith("[") else _corrida_nombre(resto, bool(m.group("f")))
            if r:
                out.append(linea[cur:ini + r[0]] + ID)
                cur = pos = ini + r[1]
                continue
        pos = max(pos + 1, ini)
    out.append(linea[cur:])
    return "".join(out), pendiente
# ------------------------------------------------------------------ cabeceras (F1, F2)
_ETQ_CAB = re.compile(
    r"(?:^|(?<=[\s>|]))(?P<et>De|DE|From|FROM|Para|PARA|To|TO|Cc|CC|Cco|CCO|Bcc|BCC|"
    r"Enviado(?:[ ]+el)?|ENVIADO|Sent|SENT|Asunto|ASUNTO|Subject|SUBJECT|Fecha|FECHA|Date|DATE|"
    r"Importancia|Prioridad)[ \t]*:[ \t]*"
)
_PERSONA_CAB = {"de", "from", "para", "to", "cc", "cco", "bcc"}
_FUNCION = {"favor", "para", "que", "con", "se", "sus", "mi", "nos", "por", "en", "un", "una", "el",
            "al", "lo", "les", "le", "no", "si", "es", "son", "hay", "van", "va", "como", "cuando",
            "y", "e", "o", "u", "buen", "buena", "buenos", "buenas", "dia", "dias", "tarde", "tardes",
            "noche", "noches", "excelente", "feliz", "lindo", "bonito", "semana", "fin", "quedo",
            "quedamos", "estoy", "espero", "pendiente", "atento", "atenta", "nuevamente", "mil",
            "muchas", "mucho", "antemano", "igualmente", "gracias", "saludos", "desde", "hasta", "hoy",
            "ahora", "aqui", "alla", "cualquier", "todo", "todos", "todas", "equipo", "cordial",
            "cordiales", "afectuosos", "adjunto", "adjunta", "te", "ti", "tu", "ud", "usted"}
_NOM_CORREO = re.compile(
    r"(?P<n>\"[^\"\n]{1,80}\"|[^;<>\[\]\n\"\d@]{1,80}?)[ \t]*"
    r"(?P<c><[ \t]*(?:mailto:)?\[CORREO\][ \t]*>|\[mailto:[ ]*\[CORREO\]\])"
)
_NOMBRE_LIBRE = re.compile(rf"[{_LETRA}'’.\-, ]+")


def _es_nombre_libre(core: str) -> bool:
    """Valor de cabecera que parece solo un nombre (admite minúsculas y 'Apellido, Nombre')."""
    c = core.strip().strip("\"“”' ")
    if not c or len(c) > 80 or not _NOMBRE_LIBRE.fullmatch(c) or not re.search(rf"[{_LETRA}]{{2}}", c):
        return False
    palabras = re.findall(rf"[{_LETRA}][{_LETRA}'’.\-]*", c)
    if len(palabras) > 8 or _CONTENIDO.search(c):
        return False
    if any(_plano(p) in _FUNCION or _plano(p) in _CADENAS for p in palabras):
        return False
    return not _EMPRESA.search(c) and _plano(c) not in _NO_NOMBRE


def _parte_cabecera(p: str) -> str:
    lead = p[: len(p) - len(p.lstrip())]
    trail = p[len(p.rstrip()):]
    core = p.strip()
    if not core:
        return p

    def con_correo(m: re.Match) -> str:
        n = m.group("n").strip().lstrip(",;").strip()
        return f"{ID} {m.group('c')}" if _es_nombre_libre(n) else m.group(0)

    core = _NOM_CORREO.sub(con_correo, core)
    if "[" in core or "@" in core:
        return lead + core + trail
    if _es_nombre_libre(core):
        return lead + ID + trail
    if core[0] in "\"“":
        cierre = core.find(core[0] if core[0] == '"' else "”", 1)
        if cierre > 0 and _es_nombre_libre(core[1:cierre]):
            return lead + ID + core[cierre + 1:] + trail
    r = _corrida_nombre(core, False, 4, True)
    if r and r[0] == 0:
        return lead + ID + core[r[1]:] + trail
    return p


def _valor_cabecera(v: str) -> str:
    lead = v[: len(v) - len(v.lstrip())]
    trail = v[len(v.rstrip()):]
    partes = re.split(r"(;|(?<=>)[ \t]*,)", v.strip())
    res = [p if k % 2 else _parte_cabecera(p) for k, p in enumerate(partes)]
    return lead + "".join(res) + trail


def _cabecera_linea(cuerpo: str):
    """Redacta personas en De/Para/Cc... (al inicio o con ≥2 etiquetas a mitad de línea)."""
    ms = list(_ETQ_CAB.finditer(cuerpo))
    if not ms or (len(ms) < 2 and cuerpo[: ms[0].start()].strip()):
        return cuerpo, False
    piezas, cur, pendiente = [], 0, False
    for k, m in enumerate(ms):
        if m.group("et").lower().split()[0] not in _PERSONA_CAB:
            continue
        fin = ms[k + 1].start() if k + 1 < len(ms) else len(cuerpo)
        v = cuerpo[m.end():fin]
        if not v.strip():
            pendiente = k == len(ms) - 1
            continue
        nv = _valor_cabecera(v)
        if nv != v:
            piezas.append(cuerpo[cur:m.end()] + nv)
            cur = fin
    piezas.append(cuerpo[cur:])
    return "".join(piezas), pendiente


_NOM_MAILTO = re.compile(
    rf"(?P<n>\"[^\"\n]{{1,60}}\"|{_NOMBRE})[ ]*(?P<c>[\[<]mailto:[ ]*\[CORREO\][\]>])"
)
_ESCRIBIO = re.compile(
    rf"(?:^|(?<=[\d,]))(?P<sp>[ \t]*)(?P<n>[{_LETRA}][{_LETRA}'’.\- ]{{1,70}}?)"
    r"(?P<mid>[ \t]*(?:<[ \t]*(?:mailto:)?\[CORREO\][ \t]*>|\[CORREO\])?[ \t]*)(?P<w>escribi[óo]|wrote)\b",
    _FLAGS | re.M,
)


_FECHA_PAL = {"ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "sept", "oct", "nov", "dic",
              "jan", "apr", "aug", "dec", "lun", "mie", "jue", "vie", "sab", "dom", "mon", "tue", "wed",
              "thu", "fri", "sat", "sun", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
              "agosto", "septiembre", "octubre", "noviembre", "diciembre", "de", "del", "a", "las", "los",
              "el", "la", "at", "on", "am", "pm", "hrs", "hr", "h"}


def _escribio(m: re.Match) -> str:
    n = m.group("n").strip()
    if not _es_nombre_libre(n) or len(n.split()) > 6:
        return m.group(0)
    if all(_plano(w) in _FECHA_PAL for w in n.split()):
        return m.group(0)  # solo fecha: "El lun, 2 jun escribió:"
    return f"{m.group('sp')}{ID}{m.group('mid') if m.group('mid').strip() else ' '}{m.group('w')}"


# --------------------------------------------------------------------- tablas (F5)
_COL_PERSONA = re.compile(rf"(?:{_ET_PERSONA_FUERTE}|{_ET_PERSONA_DEBIL})", _FLAGS)
_COL_TEL = re.compile(
    r"(?:tel(?:[eé]fono)?s?|cel(?:ular)?|m[oó]vil|whats?[ ]?app|fax|n[uú]mero[ ]+de[ ]+"
    r"(?:contacto|tel[eé]fono|celular))(?:[ ]+(?:de|del)[ ]+\w+(?:[ ]+\w+)?|[ ]+\w+)?", _FLAGS)
_COL_CORREO = re.compile(r"(?:correo|e-?mail|mail)(?:[ ]+\w+(?:[ ]+\w+)?)?", _FLAGS)
_SENS = ("p", "t", "c", "d", "u")
_COL_UBIC = re.compile(r"(?:latitud|longitud|lat|lng|coordenadas?|gps)(?:[ ]+\w+)?", _FLAGS)
_COL_DIR = re.compile(
    r"(?:calle(?:[ ]+y[ ]+n[uú]mero)?|colonia|col\.?|c\.?[ ]?p\.?|c[oó]digo[ ]+postal|direcci[oó]n|domicilio|"
    r"referencias?[ ]+del[ ]+domicilio|"
    r"n[uú]m(?:ero|\.)?[ ]+(?:ext(?:erior)?|int(?:erior)?)|no\.?[ ]+(?:ext|int)(?:erior)?\.?)"
    r"(?:[ ]+(?:de|del)[ ]+(?:env[ií]o|entrega|garant[ií]a|facturaci[oó]n)|[ ]+fiscal|[ ]+particular)*",
    _FLAGS,
)
_COL_GENERICA = re.compile(
    r"(?:folio|ticket|serie|n[uú]mero[ ]+de[ ]+serie|modelo|marca|fecha|hora|estatus|estado|ciudad|"
    r"municipio|tienda|pdv|punto[ ]+de[ ]+venta|cliente|cadena|sucursal|tipo(?:[ ]+de[ ]+servicio)?|"
    r"servicio|observaciones|comentarios|equipo|falla|cantidad|descripci[oó]n|motivo|acci[oó]n|activo|"
    r"prioridad|zona|regi[oó]n|id|no\.?|#|n[uú]mero|solicitud|canal|distribuidor|proveedor|"
    r"referencia|negocio|nombre[ ]+del[ ]+negocio|nombre[ ]+de(?:l|[ ]+la)[ ]+(?:tienda|pdv|punto[ ]+de[ ]+venta|sucursal|equipo|cadena))"
    r"(?:[ ]+\w+){0,2}", _FLAGS)


def _tipo_columna(celda: str):
    """'p' persona, 't' teléfono, 'c' correo, 'd' dirección, 'g' genérica o None."""
    c = celda.strip().strip(":*_ ").strip()
    if not c or len(c) > 40 or re.search(r"\d{3}", c) or "[" in c:
        return None
    for tipo, rx in (("p", _COL_PERSONA), ("t", _COL_TEL), ("c", _COL_CORREO), ("d", _COL_DIR),
                     ("u", _COL_UBIC)):
        if rx.fullmatch(c):
            return tipo
    if _COL_GENERICA.fullmatch(c):
        return "g"
    return None


def _valor_tabla(tipo: str, val: str) -> str:
    v = val.strip()
    if not v or _VACIO.match(v) or (v.startswith("[") and _MARCADOR_SOLO.match(v)):
        return val
    lead = val[: len(val) - len(val.lstrip())]
    trail = val[len(val.rstrip()):]
    if tipo == "p":
        r = _corrida_nombre(v, True)
        return lead + (v[:r[0]] + ID + v[r[1]:] if r else v) + trail
    if tipo == "t":
        return lead + (TELEFONO if len(re.sub(r"\D", "", v)) >= 6 and "[" not in v else v) + trail
    if tipo == "c":
        return lead + (CORREO if "[CORREO]" not in v else v) + trail
    if tipo == "u":
        return lead + (UBICACION if re.search(r"\d", v) else v) + trail
    return lead + DIRECCION + trail


_PARECE_ETIQUETA = re.compile(
    r"^(?:no\.?|n[uú]m(?:ero)?\.?|c[oó]d(?:igo)?\.?|id|folio|ticket|serie|modelo|fecha|estado|municipio|"
    r"ciudad|tipo|referencia|nombre)\b|[()]"
    , _FLAGS)


def _celdas(cuerpo: str):
    sep = "|" if cuerpo.count("|") >= 2 else "\t" if cuerpo.count("\t") >= 1 else None
    if sep is None:
        return None, None
    return sep, cuerpo.split(sep)


def _tablas(cuerpos):
    n = len(cuerpos)
    # 1) tablas con barras / tabuladores
    i = 0
    while i < n:
        sep, celdas = _celdas(cuerpos[i])
        if not celdas:
            i += 1
            continue
        interior = celdas[1:-1] if sep == "|" and not celdas[0].strip() and not celdas[-1].strip() else celdas
        offset = 1 if interior is not celdas else 0
        tipos = [_tipo_columna(c) for c in interior]
        sensibles = [k for k, tp in enumerate(tipos) if tp in _SENS]
        if not sensibles:
            i += 1
            continue
        siguiente_sep = i + 1 < n and re.fullmatch(r"[\s|:\-+]+", cuerpos[i + 1]) and "-" in cuerpos[i + 1]
        todas_etiq = all(tp is not None for tp in tipos)
        if todas_etiq and (len(interior) > 2 or siguiente_sep):
            # fila de encabezado: redacta las columnas sensibles de las filas siguientes
            j = i + 1
            while j < n:
                if re.fullmatch(r"[\s|:\-+]+", cuerpos[j]) and "-" in cuerpos[j]:
                    j += 1
                    continue
                sep2, c2 = _celdas(cuerpos[j])
                if not c2:
                    break
                int2 = c2[1:-1] if offset else c2
                if len(int2) != len(interior):
                    break
                for k in sensibles:
                    int2[k] = _valor_tabla(tipos[k], int2[k])
                cuerpos[j] = sep2.join(([c2[0]] + int2 + [c2[-1]]) if offset else int2)
                j += 1
            i = j
            continue
        # filas clave/valor: | etiqueta | valor | etiqueta | valor |
        if len(interior) >= 2 and len(interior) % 2 == 0 and all(
                _tipo_columna(interior[k]) is not None for k in range(0, len(interior), 2)):
            cambio = False
            for k in range(0, len(interior), 2):
                if tipos[k] in _SENS:
                    nuevo = _valor_tabla(tipos[k], interior[k + 1])
                    cambio |= nuevo != interior[k + 1]
                    interior[k + 1] = nuevo
            if cambio:
                cuerpos[i] = sep.join(([celdas[0]] + interior + [celdas[-1]]) if offset else interior)
        i += 1
    # 2) encabezados y valores en líneas consecutivas (tabla aplanada)
    i = 0
    while i < n:
        j = i
        tipos = []
        while j < n and cuerpos[j].strip() and "|" not in cuerpos[j]:
            tp = _tipo_columna(cuerpos[j])
            if tp is None:
                break
            tipos.append(tp)
            j += 1
        k = len(tipos)
        if k >= 2 and any(tp in _SENS for tp in tipos):
            vals = []
            m = j
            if m < n and not cuerpos[m].strip():
                m += 1
            while (m < n and cuerpos[m].strip() and "|" not in cuerpos[m] and len(cuerpos[m]) <= 80
                   and len(vals) < 12 * k and _tipo_columna(cuerpos[m]) is None):
                vals.append(m)
                m += 1
            if len(vals) >= k and len(vals) % k:
                vals = vals[:k]
            if len(vals) < k:  # "valores" que son etiquetas: formulario etiqueta/valor, no esta tabla
                vals = []
            filas = len(vals) // k if vals else 0
            for f in range(filas):
                for c, tp in enumerate(tipos):
                    if tp in _SENS:
                        idx = vals[f * k + c]
                        cuerpos[idx] = _valor_tabla(tp, cuerpos[idx])
            i = max(m, i + 1) if filas else j
        else:
            i = max(j, i + 1)
    # 3) formulario con una celda por línea: etiqueta, valor, etiqueta, valor...
    for i in range(n - 1):
        c = cuerpos[i]
        if not c.strip() or "|" in c:
            continue
        tp = _tipo_columna(c)
        if tp not in ("p", "t", "d", "u"):
            continue
        if tp == "d" and re.fullmatch(r"\s*(?:direcci[oó]n|domicilio)\s*:?\s*", c, _FLAGS):
            continue  # "Dirección" sola: puede ser la del punto de venta
        sig = cuerpos[i + 1]
        if not sig.strip() or _tipo_columna(sig) is not None or _PARECE_ETIQUETA.search(sig.strip()) \
                or len(sig) > 100:
            continue
        cuerpos[i + 1] = _valor_tabla(tp, sig)
    return cuerpos


# ------------------------------------------------------------------- saludos (F8)
_SALUDO_INI = (
    r"hola|buen(?:os|as)?[ ]+(?:d[ií]as?|tardes?|noches?)|buen[ ]+d[ií]a|estimad[oa]s?|apreciable|"
    r"querid[oa]|que[ ]+tal|hey|hello|dear|hi"
)
_SALUDO = re.compile(
    rf"(?:^|(?<=[.!?¡:>]))(?P<pre>[ \t>]*(?:(?i:{_SALUDO_INI})[ \t,]+)+)(?P<n>[^\n,:;!¡?]{{1,60}}?)"
    r"(?=[ \t]*(?:[,:;!?]|$)|[ \t]*\.[ \t]*$|(?<=[a-záéíóúñ]{3})(?<!Mtro)(?<!Mtra)(?<!Prof)(?<!Profa)\.(?=[ \t]+[A-ZÁÉÍÓÚÑ¡¿]))",
    re.M,
)
_SALUDO_INV = re.compile(
    r"^(?P<pre>[ \t>]*)(?P<n>[^\n,:;!¡?]{1,40}?)(?P<g>[ \t,]+(?i:buen(?:os|as)?[ ]+(?:d[ií]as?|tardes?|noches?)"
    r"|buen[ ]+d[ií]a|hola)\b)",
    re.M,
)
_MENCION = re.compile(rf"(?<![\w.@/])@(?P<n>[{_LETRA}][{_LETRA}'’\-]*(?:[ ]+[{_LETRA}][{_LETRA}'’\-]*){{0,5}})")
_OTROS_SALUDO = {"senor", "senores", "senora", "senoras", "sres", "sras", "caballeros", "damas",
                 "ingenieros", "licenciados", "doctores", "personal", "gerentes", "colaboradores",
                 "compa", "compas", "buen", "buenos", "buenas", "lic", "ing"}


def _span_nombre_saludo(n: str):
    """(inicio, fin) del nombre dentro de ``n`` (sin título), o None."""
    toks = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", n)]
    i = 0
    while i < len(toks) and _plano(toks[i][2]) in _TITULOS:
        i += 1
    rest = toks[i:]
    if not rest or len(rest) > 6 or len(toks) > 7:
        return None
    for k, (_, _, tok) in enumerate(rest):
        plano = _plano(tok)
        if not re.fullmatch(rf"[{_LETRA}][{_LETRA}'’\-]*\.?", tok) or len(plano) < 2 and k == 0:
            return None
        if _PART_RE.match(tok) and 0 < k < len(rest) - 1:
            continue
        if plano in _NO_SALUDO or plano in _OTROS_SALUDO or _CONTENIDO.search(tok):
            return None
        if len(rest) > 1 and not _es_cap(tok) and plano in _FUNCION:
            return None
    caps = [_es_cap(tok) for _, _, tok in rest if not _PART_RE.match(tok)]
    if len(caps) > 1 and any(caps) and not all(caps):
        return None  # "Sucursal Norte necesita servicio": no es un nombre
    return rest[0][0], rest[-1][1]


def _saludos(t: str) -> str:
    def directo(m: re.Match) -> str:
        n = m.group("n")
        sp = _span_nombre_saludo(n)
        if not sp:
            return m.group(0)
        if m.group("pre").rstrip().endswith(",") and not _es_cap(n[sp[0]:sp[0] + 1] or "a"):
            return m.group(0)  # "Buen día, solicito...": la coma separa el saludo de la frase
        return m.group("pre") + n[:sp[0]] + ID + n[sp[1]:]

    def inverso(m: re.Match) -> str:
        n = m.group("n")
        sp = _span_nombre_saludo(n)
        if not sp or n[:sp[0]].strip() or n[sp[1]:].strip():
            return m.group(0)
        return m.group("pre") + ID + m.group("g")

    def mencion(m: re.Match) -> str:
        toks = [(x.start(), x.end(), x.group()) for x in re.finditer(r"\S+", m.group("n"))]
        fin = 0
        for k, (_, e, tok) in enumerate(toks):
            plano = _plano(tok)
            if k > 0 and _PART_RE.match(tok) and k + 1 < len(toks) and _es_cap(toks[k + 1][2]):
                continue
            if plano in _NO_SALUDO or plano in _OTROS_SALUDO or _CONTENIDO.search(tok) or len(plano) < 2:
                break
            if k > 0 and not _es_cap(tok):
                break
            fin = e
        if not fin:
            return m.group(0)
        return "@" + ID + m.group("n")[fin:]

    t = _SALUDO.sub(directo, t)
    t = _SALUDO_INV.sub(inverso, t)
    return _MENCION.sub(mencion, t)


# ------------------------------------------------------------------------ nombres
def _nombres(t: str) -> str:
    t = _NOM_MAILTO.sub(lambda m: f"{ID} {m.group('c')}", t)
    t = _ANTES_CORREO.sub(f"{ID} <{CORREO}>", t)
    t = _ESCRIBIO.sub(_escribio, t)
    lineas = t.split("\n")
    partes = [_quote_split(ln) for ln in lineas]
    cuerpos = _tablas([c for _, c in partes])
    pendiente = None  # 'cab' | 'p' | 'd': el valor de la etiqueta sigue en la línea siguiente
    blancos = 0
    out = []
    for (pref, _), cuerpo in zip(partes, cuerpos):
        if pendiente and not cuerpo.strip():
            blancos += 1
            if blancos > 1:
                pendiente = None
        elif pendiente:
            sin_etiqueta = (not _ETQ_CAB.match(cuerpo) and not _CAMPO.match(cuerpo)
                            and _tipo_columna(cuerpo) is None and re.search(rf"[{_LETRA}]{{2}}", cuerpo))
            if sin_etiqueta and len(cuerpo) <= 120:
                if pendiente == "cab":
                    cuerpo = _valor_cabecera(cuerpo)
                elif pendiente == "p":
                    r = _corrida_nombre(cuerpo, True)
                    if r and not cuerpo.lstrip().startswith("["):
                        cuerpo = cuerpo[:r[0]] + ID + cuerpo[r[1]:]
                elif not _VACIO.match(cuerpo.strip()) and not cuerpo.lstrip().startswith("["):
                    cuerpo = DIRECCION
            pendiente = None
            blancos = 0
        cuerpo, pend_cab = _cabecera_linea(cuerpo)
        cuerpo, pend = _campos_linea(cuerpo)
        if pend_cab:
            pendiente = "cab"
        elif pend:
            pendiente = pend
        out.append(pref + cuerpo)
    return _saludos("\n".join(out))


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
    r"quedo[ ]+(?:atent[oa]|(?:al[ ]+)?pendiente)(?:[ ]+(?:a|de)[ ]+(?:sus|tus)[ ]+"
    r"(?:comentarios|[oó]rdenes|indicaciones|respuestas?))?|"
    r"estoy[ ]+(?:al[ ]+)?pendiente|quedamos[ ]+pendientes|(?:un[ ]+)?abrazos?|"
    r"quedamos[ ]+(?:atent[oa]s|al[ ]+pendiente)(?:[ ]+a[ ]+(?:sus|tus)[ ]+"
    r"(?:comentarios|[oó]rdenes|indicaciones|respuestas?))?|"
    r"(?:muchas[ ]+|mil[ ]+)?gracias(?:[ ]+de[ ]+antemano)?(?:[ ]+por[ ]+(?:su|tu|el)[ ]+"
    r"(?:atenci[oó]n|apoyo|ayuda|respuesta|tiempo|colaboraci[oó]n))?|"
    r"que[ ]+tengas?[ ]+(?:un[ ]+)?(?:excelente|buen|lindo|bonito)[ ]+d[ií]a|"
    r"(?:un[ ]+)?saludos?|slds?|sds|salu2|"
    r"(?:best|kind|warm)[ ]+regards|regards|thanks|thank[ ]+you|sincerely"
)
_DESPEDIDA_CORTA = r"saludos?|gracias|slds?|abrazos?|cordialmente|atentamente|atte\.?"
_DESPEDIDA_RE = re.compile(
    rf"^(?P<lead>[¡!\s]*)(?P<d>(?:{_DESPEDIDAS})(?:[ \t,;.!¡]+(?:y[ ]+)?(?:{_DESPEDIDA_CORTA})\b)*)"
    rf"(?P<punt>[ \t,.;:!¡\-–—]*)(?P<resto>.*)$", _FLAGS
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
_MARCADOR_SOLO = re.compile(
    r"^(?:[ \t,.;:|<>()\-]|\[(?:CORREO|TELEFONO|ID|FIRMA|MONTO|UBICACION|DIRECCION)\])*$"
)
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
    if r == r.lower() and len(r) <= 40 and len([w for w in r.split() if not _PART_RE.match(w)]) <= 4 and _es_nombre_libre(r) \
            and not any(_plano(w) in _NO_SALUDO and not _PART_RE.match(w) for w in r.split()):
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


_TEL_ETQ = re.compile(
    r"(?:^|[\s|/·•,;(])(?:C|T|M|Cel|Tel|Cell|Mob|M[óo]vil|Oficina|Of|Fax|WhatsApp)\.?[ \t]*[:\-]?[ \t]*"
    r"\+?\[TELEFONO\]",
    _FLAGS,
)
_PAL_MAY = rf"[{_MAY}][{_MAY}'’.\-]*"
_NOMBRE_MAY = re.compile(rf"{_PAL_MAY}(?:[ ]+(?:(?:DE|DEL|LA|LAS|LOS|Y)[ ]+)*{_PAL_MAY}){{1,4}}")
_NO_FIRMA_NOMBRE = re.compile(
    r"instalaci|retiro|cambio|equipo|cobertura|enfria|condensa|adicional|datos|contacto|informaci|"
    r"servicio|solicitud|reporte|urgente|importante|aviso|atenci|tienda|cliente",
    _FLAGS,
)


def _linea_firma(cuerpo: str) -> bool:
    c = cuerpo.strip()
    return 0 < len(c) <= 60 and not _es_contenido(c) and not _es_frontera(c) and not _LEGAL.match(c)


def _es_nombre_firma(cuerpo: str) -> bool:
    c = cuerpo.strip()
    if not 4 <= len(c) <= 50 or _es_contenido(c) or _NO_FIRMA_NOMBRE.search(c):
        return False
    if any(_plano(w) in _CADENAS for w in c.split()):
        return False
    return bool(_NOMBRE_MAY.fullmatch(c) or (len(c.split()) >= 2 and _NOMBRE_RE.fullmatch(c)))


_CARGO = re.compile(
    r"\b(?:gerente|subgerente|coordinador[a]?|supervisor[a]?|director[a]?|ejecutiv[oa]|analista|t[eé]cnic[oa]|"
    r"jefe|jefa|encargad[oa]|asesor[a]?|representante|especialista|l[ií]der|administrador[a]?|ingenier[oa]|"
    r"auxiliar|asistente|vendedor[a]?|promotor[a]?|operador[a]?|capturista|regional|ventas)\b",
    _FLAGS,
)


def _linea_nombre_cargo(cuerpo: str) -> bool:
    """"Nombre Apellido" al inicio de una línea corta (puede seguir un cargo: "Pedro Gómez - Jefe de
    Mantenimiento"); sus dos primeras palabras no son de contenido ni de saludo."""
    c = cuerpo.strip()
    toks = c.split()
    if not 2 <= len(toks) <= 12 or len(c) > 80 or _SERIE_TOKEN.search(c) or re.search(r"\d{3}", c):
        return False
    for t in toks[:2]:
        if not re.fullmatch(_PALABRA, t) or _CONTENIDO.search(t) or _plano(t) in _NO_SALUDO \
                or _plano(t) in _CADENAS or _NO_FIRMA_NOMBRE.search(t):
            return False
    return True


def _firmas_contacto(t: str) -> str:
    """F7: bloque nombre + cargo + "C:/T:/Cel" + teléfono, aun sin despedida conocida."""
    lineas = t.split("\n")
    n = len(lineas)
    partes = [_quote_split(ln) for ln in lineas]
    out = []
    i = 0
    while i < n:
        pref, c = partes[i]
        prof = pref.count(">")
        sig_cargo = (i + 1 < n and partes[i + 1][0].count(">") == prof
                     and len(partes[i + 1][1].strip()) <= 60 and _CARGO.search(partes[i + 1][1]))
        if _es_nombre_firma(c) and sig_cargo or (
                _linea_nombre_cargo(c) and _CARGO.search(c) and not _es_frontera(c)):
            fin = i + 1
            while fin < n and partes[fin][0].count(">") == prof and (
                    _linea_firma(partes[fin][1]) or (fin == i + 1 and sig_cargo)):
                fin += 1
            out.append(f"{_pref(pref)}{FIRMA}")
            i = fin
            continue
        if _es_nombre_firma(c):
            j = i + 1
            ok = False
            while j < n and j <= i + 4 and partes[j][0].count(">") == prof and _linea_firma(partes[j][1]):
                if _TEL_ETQ.search(partes[j][1]):
                    ok = True
                    break
                j += 1
            if ok:
                fin = j + 1
                while fin < n and partes[fin][0].count(">") == prof and _linea_firma(partes[fin][1]):
                    fin += 1
                out.append(f"{_pref(pref)}{FIRMA}")
                i = fin
                continue
        out.append(lineas[i])
        i += 1
    return "\n".join(out)


def _firmas(t: str) -> str:
    t = _firmas_contacto(t)
    lineas = t.split("\n")
    n = len(lineas)
    partes = [_quote_split(ln) for ln in lineas]
    salida = []
    i = 0

    def bloque(desde: int, profundidad: int, parar_en_contenido: bool) -> int:
        """Índice (exclusivo) de la última línea del bloque que empieza en ``desde``."""
        fin = desde
        j = desde
        primera = True
        while j < n:
            pref, cuerpo = partes[j]
            if cuerpo.strip() == "":
                j += 1
                continue
            libre = primera and parar_en_contenido and _linea_nombre_cargo(cuerpo)
            primera = False
            if pref.count(">") != profundidad or _es_frontera(cuerpo):
                break
            if cuerpo.strip() == FIRMA:  # bloque ya redactado: lo absorbe y termina
                return j + 1
            if parar_en_contenido and not libre and (
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
                cabeza = f"{m.group('lead')}{m.group('d')}{m.group('punt')}".rstrip()
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
def _pasada(t: str) -> str:
    t = _correos(t)
    t = _ids(t)
    t = _ubicaciones(t)
    t = _montos(t)
    t = _telefonos(t)
    t = _nombres(t)
    t = _firmas(t)
    return re.sub(r"[ \t]+$", "", t, flags=re.M)


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
    # punto fijo: lo redactado en una pasada cambia el contexto de la siguiente (una tabla
    # tapada deja de ser "Folio:"...), así que se repite hasta que no cambie nada; así
    # redact(redact(x)) == redact(x) por construcción
    for _ in range(5):
        previo = t
        t = _pasada(t)
        if t == previo:
            break
    t = re.sub(r"[ \t]+$", "", t, flags=re.M)
    for marca, tok in protegidos:
        t = t.replace(marca, tok)
    return t
