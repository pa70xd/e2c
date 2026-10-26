# Formato "Lay Out Repare" (Imbera y Torrey). Hoja visible "RUTA".
#
# Dos variantes de encabezado:
#   A) Una sola fila: Modelo; Serie; Falla Reportada & NOTAS ADICIONALES;
#      Fecha Factura; Num. De Distribuidor; N° de Cliente; Municipio;
#      TIPO DE MOVIMIENTO; CANAL.
#   B) Varias filas: una fila de GRUPOS ("DATOS DE DIRECCIÓN", "CASO DE
#      CONTAR CON LOS DATOS", "NOMBRE DE QUIÉN RECIBIRÁ EL SERVICIO") con
#      celdas combinadas y, debajo, la fila de columnas. Los nombres de
#      columna se repiten entre grupos, por eso el alias se busca primero
#      como "GRUPO | COLUMNA" y luego como "COLUMNA".
#
# Las llaves ya van normalizadas (mayúsculas, sin acentos, espacios
# simples): ver parsers/imbera_parse/lector.py::normalizar.

NAMES_COLUMNS = {
    # --- variante A ---
    "MODELO": "MODELO",
    "SERIE": "SERIE",
    "FALLA REPORTADA & NOTAS ADICIONALES": "FALLA",
    "FALLA REPORTADA": "FALLA",
    "FALLA": "FALLA",
    "FECHA FACTURA": "FECHA FACTURA",
    "NUM. DE DISTRIBUIDOR": "NUM DISTRIBUIDOR",
    "NUM DE DISTRIBUIDOR": "NUM DISTRIBUIDOR",
    "N° DE CLIENTE": "NUM CLIENTE",
    "NO DE CLIENTE": "NUM CLIENTE",
    "NO. DE CLIENTE": "NUM CLIENTE",
    "MUNICIPIO": "MUNICIPIO",
    "TIPO DE MOVIMIENTO": "TIPO DE MOVIMIENTO",
    "CANAL": "CANAL",

    # --- variante B ---
    "MODELO DEL EQUIPO A REPORTAR": "MODELO",
    "SERIE DEL EQUIPO": "SERIE",
    "NUMERO DE DISTRIBUIDOR IMBERA / TORREY": "NUM DISTRIBUIDOR",
    "NUMERO DE DISTRIBUIDOR IMBERA/TORREY": "NUM DISTRIBUIDOR",
    "NUMERO DE CLIENTE QUE REPORTA EL EQUIPO": "NUM CLIENTE",

    "DATOS DE DIRECCION | CALLE": "CALLE",
    "DATOS DE DIRECCION | NUMERO": "NUMERO",
    "DATOS DE DIRECCION | COLONIA": "COLONIA",
    "DATOS DE DIRECCION | CP": "CP",
    "DATOS DE DIRECCION | CODIGO POSTAL": "CP",
    "DATOS DE DIRECCION | MUNICIPIO": "MUNICIPIO",
    "DATOS DE DIRECCION | ESTADO": "ESTADO",

    "CASO DE CONTAR CON LOS DATOS | LATITUD": "LATITUD",
    "CASO DE CONTAR CON LOS DATOS | LONGITUD": "LONGITUD",

    # PII: nunca se loguea ni se manda a un LLM (solo se persiste).
    "NOMBRE DE QUIEN RECIBIRA EL SERVICIO | NOMBRE": "CONTACTO NOMBRE",
    "NOMBRE DE QUIEN RECIBIRA EL SERVICIO | TELEFONO": "CONTACTO TELEFONO",
    "NOMBRE DE QUIEN RECIBIRA EL SERVICIO | CORREO": "CONTACTO CORREO",

    # Respuesta de REPARE (outbound con Excel).
    "OS": "OS",
    "ORDEN DE SERVICIO": "OS",
}

# Columnas canónicas, en el orden en que quedan en la tabla de trabajo.
COLUMNAS = [
    "MODELO", "SERIE", "FALLA", "FECHA FACTURA", "NUM DISTRIBUIDOR",
    "NUM CLIENTE", "MUNICIPIO", "TIPO DE MOVIMIENTO", "CANAL",
    "CALLE", "NUMERO", "COLONIA", "CP", "ESTADO", "LATITUD", "LONGITUD",
    "CONTACTO NOMBRE", "CONTACTO TELEFONO", "CONTACTO CORREO", "OS",
]

# Columnas que nunca se imprimen ni se mandan a un proveedor externo.
COLUMNAS_PII = {"CONTACTO NOMBRE", "CONTACTO TELEFONO", "CONTACTO CORREO", "CALLE", "NUMERO"}

# Una hoja es de DATOS si su encabezado trae estas columnas (después de los
# alias). Las hojas de CATÁLOGO ("LinesByCategori", "ModelsByLines") no las
# traen y se descartan, estén ocultas o no.
ENCABEZADO_DATOS = {"MODELO", "SERIE"}

# Hoja preferida del layout.
HOJA_RUTA = "RUTA"

# Filas que se revisan para encontrar el encabezado (variante B: grupos +
# columnas).
MAX_FILAS_ENCABEZADO = 10

# Fila "basura": no trae ninguno de estos campos (p. ej. la fila de ejemplo
# del layout o una fila con solo el default de una lista desplegable). Se
# descarta en silencio, no cuenta como rechazada.
CAMPOS_FILA_REAL = ("MODELO", "SERIE", "FALLA", "NUM CLIENTE")

# Columnas internas para ubicar la fila en el archivo original.
COL_ARCHIVO = "_ARCHIVO"
COL_FILA_EXCEL = "_FILA_EXCEL"
