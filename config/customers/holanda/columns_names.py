# Alias de columnas -> nombre canónico del layout de Holanda
# ("Casos REPARE DDMMAAAA.xlsx"); los encabezados varían semana a semana.

NAMES_COLUMNS = {
    "TE": "TE",

    "ORIGEN": "ORIGEN",

    "FECHA": "FECHA",

    "CASO2": "CASO2",
    "CASO": "CASO2",

    "SAP": "SAP",

    "NOMBRE DEL CLIENTE": "NOMBRE DEL CLIENTE",
    "NOMBRE DEL CLIENTE ": "NOMBRE DEL CLIENTE",

    "NOMBRE NEGOCIO": "NOMBRE NEGOCIO",
    "NOMBRE NEGOCIO ": "NOMBRE NEGOCIO",

    "TELEFONO": "TELEFONO",
    "TELEFONO ": "TELEFONO",

    "CALLE Y NUMERO": "CALLE Y NUMERO",
    "CALLE Y NUMERO ": "CALLE Y NUMERO",

    "COLONIA": "COLONIA",

    "MUNICIPIO": "MUNICIPIO",
    "MUNICIPIO ": "MUNICIPIO",

    "CP": "CP",

    "ESTADO": "ESTADO",
    "ESTADO ": "ESTADO",

    "LATITUD": "LATITUD",
    "LATITUD ": "LATITUD",

    "LONGITUD": "LONGITUD",
    "LONGITUD ": "LONGITUD",

    "SEGMENTO": "SEGMENTO",

    "CANAL": "CANAL",

    "AGRUPADOR": "AGRUPADOR",

    "REGION": "REGION",
    "REGION ": "REGION",

    "AGENCIA": "AGENCIA",

    "RUTA": "RUTA",

    "AGENCIA SATELITE": "AGENCIA SATELITE",

    "TIPO DE QUEJA": "TIPO DE QUEJA",
    "TIPO DE QUEJA ": "TIPO DE QUEJA",

    "CONGELADOR": "CONGELADOR",
    "CONGELADOR ": "CONGELADOR",

    "MODELO": "MODELO",
    "MODELO ": "MODELO",

    "SERIE": "SERIE",

    "OXXO": "OXXO",

    "CLASIFICADOR DE CASO": "CLASIFICADOR DE CASO",
    "CLASIFICADOR DE CASO ": "CLASIFICADOR DE CASO",

    "SIN SAP / SINC ONGELADOR": "SIN SAP / SIN CONGELADOR",
    "SIN SAP / SINC ONGELADOR ": "SIN SAP / SIN CONGELADOR",
    "SIN SAP / SIN CONGELADOR": "SIN SAP / SIN CONGELADOR",

    "PROVEEDOR": "PROVEEDOR",
    "PROVEEDOR ": "PROVEEDOR",

    "OS": "OS",
    "MERMA": "MERMA",
}

# Las 30 columnas del layout que Holanda envía y que se le regresa
# (control interno, confirmado con Abraham: el "Casos REPARE...xlsx" SÍ es
# lo que ve el cliente; OS/MERMA se agregan después de cargar al CRM y no
# las genera el parser en la etapa 1).
SABANA_COLUMNS = [
    "TE", "ORIGEN", "FECHA", "CASO2", "SAP",
    "NOMBRE DEL CLIENTE", "NOMBRE NEGOCIO", "TELEFONO",
    "CALLE Y NUMERO", "COLONIA", "MUNICIPIO", "CP", "ESTADO",
    "LATITUD", "LONGITUD", "SEGMENTO", "CANAL", "AGRUPADOR",
    "REGION", "AGENCIA", "RUTA", "AGENCIA SATELITE",
    "TIPO DE QUEJA", "CONGELADOR", "MODELO", "SERIE", "OXXO",
    "CLASIFICADOR DE CASO", "SIN SAP / SIN CONGELADOR", "PROVEEDOR",
]

# Columnas mínimas para procesar el archivo (DEC-78: más permisivo que
# Danone). TE y ORIGEN no son obligatorias: la llave del caso es CASO2 y
# ORIGEN se infiere de su sufijo (SUFIJO_ORIGEN).
EXPECTED_COLUMNS = {
    "FECHA", "CASO2",
    "NOMBRE DEL CLIENTE", "NOMBRE NEGOCIO",
    "MODELO", "SERIE",
}

# Si llega otro Origen, la fila se rechaza en vez de adivinar el formato de
# Fecha/Telefono.
ORIGENES_CONOCIDOS = {"HELADIO", "GDR"}

# Sufijo de CASO2 (C + dígitos + H/G) -> Origen. H y G son secuencias
# independientes: CASO2 siempre se guarda y compara completo, con sufijo.
SUFIJO_ORIGEN = {
    "H": "HELADIO",
    "G": "GDR",
}

# Columnas internas que agrega el reader para ubicar cada fila en el archivo
# original (y pintar ahí las rechazadas). No vienen del layout.
COL_ARCHIVO = "_ARCHIVO"
COL_FILA_EXCEL = "_FILA_EXCEL"

# Si el encabezado llega vacío en estas posiciones (0-indexado), se asume
# OS/MERMA (visto en archivos reales).
FALLBACK_POSICIONAL = {
    32: "OS",
    33: "MERMA",
}
