import re

CREATE_REQUESTS = [

    # =========================
    # Solicitudes directas
    # =========================
    r"\bfavor de (?:realizar|crear|generar|programar|agendar|atender).*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",
    r"\bsolicit[oa].*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",
    r"\bme apoya(?:n)? con.*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",
    r"\bpuede(?:n|s)? apoyar.*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",
    r"\bnos apoya(?:n)? con.*(?:servicios|instalaciones|retiros|reubicaciones)\b",
    r"\bme ayuda(?:n)? con.*(?:servicios|instalaciones|retiros|reubicaciones)\b",
    r"\bapoya(?:n)? favor\b.*(?:instalaci[oó]n|instalaciones|retiro|retiros)\b",
    r"\bfavor\b.*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",
    r"\b(?:ayudan|ayuda|apoyan|apoya).*(?:instalaci[oó]n|instalacio)(?: de equipos)?\b",
    r"\bayudan(?: estos)? avisos\b",
    r"\bayudan(?: con)? .*?(?:instalaci[oó]n|instalacio)(?: de equipos)?\b",    
    r"\bservicios\s+repare\b",

    r"\b(?:(?:1ra|1era|2da|2da|3ra|3era|primera|segunda|tercera)\s+)?carga\s+de\s+servicios\b",
    r"\b(?:programaci[oó]n|programar)\s+(?:los\s+)?servicios\b",
    r"\bme\s+ayudan\s+con\s+la\s+programaci[oó]n\s+de\s+servicios\b",
    r"\bnos\s+ayudan\s+con\s+la\s+programaci[oó]n\s+de\s+servicios\b",
    r"\bsolicitud\s+de\s+servicios\s+repare\b",
    r"\bsolicitud\s+servicios\s+repare\b",
    r"\bsolicitud\s+para\s+servicios\s+repare\b",
    r"\bservicios\s+de\s+repare\b",
    r"\bservicios\s+para\s+repare\b",
    r"\bcomparto\s+(?:la\s+)?carga\s+de\s+servicios\b",
    r"\bcompartimos\s+(?:la\s+)?carga\s+de\s+servicios\b",

    # Carga de servicio
    r"\bsu\s+apoyo\s+con\s+la\s+carga\s+del\s+siguiente\s+servicio\b",
    r"\bapoyo\s+con\s+la\s+carga\s+del\s+(?:siguiente\s+)?servicio\b",
    r"\bcarga(?:r)?\s+(?:del\s+)?(?:siguiente\s+)?servicio\b",

    # Solicitudes directas
    r"\bfavor\s+de\s+(?:realizar|crear|generar|programar|agendar|atender).*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",
    r"\bsolicit[oa].*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",
    r"\bme\s+apoya(?:n)?\s+con.*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",


    # =========================
    # Urgencias
    # =========================
    r"\burge(?:n)?\b.*(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios)\b",
    r"(?:instalaci[oó]n|instalaciones|retiro|retiros|reubicaci[oó]n|reubicaciones|servicios).*\burge(?:n)?\b",

    # =========================
    # Atención / Programación
    # =========================
    r"\batenci[oó]n\b.*(?:instalaciones|retiros|servicios)\b",
    r"\bme apoya(?:n)? con la atenci[oó]n de los servicios\b",
    r"\batenci[oó]n de los servicios\b",
    r"\bprogramar\b.*(?:servicios|instalaciones|retiros)\b",
    r"\bprogramaci[oó]n de servicios\b",
    r"\bme ayuda(?:n)? con la programaci[oó]n de servicios\b",
    r"\bfavor de programar(?: los)? servicios\b",
    r"\bsolicito(?: la)? programaci[oó]n\b",
    r"\bsolicito(?: la)? atenci[oó]n\b",

    # =========================
    # Carga de servicios
    # =========================
    r"\bcarga de servicios\b",
    r"\b1ra carga de servicios\b",
    r"\bprimera carga de servicios\b",
    r"\bcomparto.*carga de servicios\b",
    r"\bfavor de cargar(?: los)? servicios\b",
    r"\bcargar(?: los)? servicios\b",
    r"\bsolicitud de servicios\b",

    # =========================
    # Ordenes de servicio
    # =========================
    r"\bgenerar(?: las)? orden(?:es)? de servicio\b",
    r"\bcrear(?: las)? orden(?:es)? de servicio\b",
    r"\bdar de alta(?: las)? orden(?:es)? de servicio\b",
    r"\borden(?:es)? de servicio\b",
    r"\borden(?:es)? solicitadas\b",
    r"\bos solicitadas\b",
    r"\bcrear(?: las)? os\b",
    r"\bgenerar(?: las)? os\b",
    r"\benv[ií]o os solicitadas\b",
    r"\benv[ií]o(?: las)? orden(?:es)?(?: de servicio)?\b",
    r"\bcomparto(?: la| las)? orden(?:es)?(?: de servicio)?\b",
    r"\bcomparto la\(s\) orden\(es\) de servicio\b",

    # =========================
    # Altas
    # =========================
    r"\balta(?: de)? servicios\b",
    r"\balta(?: de)? instalaciones\b",

    # =========================
    # Adjuntos
    # =========================
    r"\badjunto.*(?:instalaciones|retiros|servicios).*(?:para|a)\b",
    r"\barchivo.*(?:instalaciones|servicios).*(?:atender|programar|cargar)\b",
    r"\badjunto.*(?:archivo|formato|excel|listado|relaci[oó]n)\b",
    r"\bse adjunta\b.*(?:archivo|formato|excel|servicios)\b",

    # =========================
    # Servicios generales
    # =========================
    r"\blos siguientes servicios\b",
    r"\blos ayudan avisos\b",
    r"\bestos servicios\b",
    r"\bcomparto.*servicios\b",
    r"\benv[ií]o.*servicios\b",
    r"\bservicios para su atenci[oó]n\b",

    # Movimiento / reubicación de equipos
    r"\bsolicito que se muevan los siguientes equipos\b",
    r"\bsolicito que se muevan\b",
    r"\bmover(?: los)? siguientes equipos\b",
    r"\bmover(?: el| los)? equipos\b",
    r"\bmovimiento de equipos\b",
    r"\bmover equipos\b",
    r"\bsolicito(?: el)? movimiento\b",
    r"\bsolicito(?: la)? reubicaci[oó]n\b",
    r"\breubicar(?: los)? equipos\b",
    r"\bcambio de ubicaci[oó]n\b",
]


MOVEMENTS = [

    # Instalación
    r"\binstalaci[oó]n(?:es)?\b",
    r"\binstalar\b",
    r"\binstale(?:n)?\b",

    # Retiro
    r"\bretiros?\b",
    r"\bretirar\b",
    r"\bretire(?:n)?\b",

    # Reubicación
    r"\breubicaci[oó]n(?:es)?\b",
    r"\breubicar\b",
    r"\breubique(?:n)?\b",

    # Movimiento
    r"\bmovimiento(?:s)?\b",
    r"\bmover\b",
    r"\bmueva(?:n)?\b",
    r"\bse mueva(?:n)?\b",

    # Traslado
    r"\btraslado(?:s)?\b",
    r"\btrasladar\b",
    r"\btraslade(?:n)?\b",

    # Cambio de ubicación
    r"\bcambio de ubicaci[oó]n\b",
    r"\bcambiar de ubicaci[oó]n\b",

    # Servicios
    r"\balta(?:s)?\b",
    r"\borden(?:es)? de servicio\b",
    r"\bservicios\b",
    r"\bavisos?\b(?!\s+(?:de\s+)?privacidad)",
    r"\bmueva(?:n)?(?: los)? siguientes equipos\b",
]

IGNORE_REQUESTS = [
    r"\bseguimiento\b",
    r"\bestatus\b",
    r"\bstatus\b",
    r"\bconsulta\b",
    r"\bconsulto\b",
    r"\binformo\b",
    r"\bse realiz[oó]\b",
    r"\bse atendi[oó]\b",
    r"\bcompletad[oa]\b",
    r"\bfinalizad[oa]\b",
    r"\bcancelad[oa]\b",
    r"\bcerrad[oa]\b",
    r"\bevidencia\b",
    r"\bvalidaci[oó]n\b",
]


DIC_SABANAS_MOV = {
    "MOVIMIENTOS": [
        "INSTALACIÓN",
        "RETIRO",
        "REUBICACION",
        "MOVIMIENTO",
        "MOVIMIENTOS",

        "REUBICACION",
        "REUBICACIÓN",
        "REUBICACIONES",

        "RETIRO",
        "RETIROS",
        "RECOLECCION",
        "RECOLECCIÓN",
        "RECOLECCIONES",
        "BAJA",
        "BAJAS",
        "DESINSTALACION",
        "DESINSTALACIONES",

        "INSTALACION",
        "INSTALACIONES",
        "ALTA",
        "ALTAS",
        "INSTALACIÓN",

    ],
    "RUTA": [
        "REPARACION",
        "RUTA",
        "RUTAS",
        "REPARACION",
        "REPARACIÓN",
    ]
}








