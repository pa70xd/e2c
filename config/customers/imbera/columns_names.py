# Formato "Lay Out Repare" (Imbera y Torrey). Hoja visible "RUTA".
#
# Dos variantes de encabezado:
#   A) Una sola fila: Modelo; Serie; Falla Reportada & NOTAS ADICIONALES;
#      Fecha Factura; Num. De Distribuidor; N° de Cliente; Municipio;
#      TIPO DE MOVIMIENTO; CANAL.
#   B) Varias filas: una fila de GRUPOS ("DATOS DE DIRECCIÓN", "CASO DE
#      CONTAR CON LOS DATOS", "NOMBRE DE QUIÉN RECIBIRÁ EL SERVICIO") con
#      celdas combinadas y, debajo, la fila de columnas. El lector común
#      elige la fila de columnas (la de grupos no puntúa) y no conserva el
#      grupo: si un nombre se repite entre grupos, el lector lo renombra
#      "NOMBRE_2" y aquí gana el primero.
#
# Las llaves se comparan con parsers.core.lector.normalizar_encabezado
# (mayúsculas, sin acentos, espacios simples, "/" sin espacios).

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

    # Grupo "DATOS DE DIRECCIÓN".
    "CALLE": "CALLE",
    "NUMERO": "NUMERO",
    "COLONIA": "COLONIA",
    "CP": "CP",
    "CODIGO POSTAL": "CP",
    "ESTADO": "ESTADO",

    # Grupo "CASO DE CONTAR CON LOS DATOS".
    "LATITUD": "LATITUD",
    "LONGITUD": "LONGITUD",

    # Grupo "NOMBRE DE QUIÉN RECIBIRÁ EL SERVICIO". PII: nunca se loguea ni
    # se manda a un LLM (solo se persiste y va en la pre-sábana).
    "NOMBRE": "CONTACTO NOMBRE",
    "TELEFONO": "CONTACTO TELEFONO",
    "CORREO": "CONTACTO CORREO",

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

# Fila "basura": no trae ninguno de estos campos (p. ej. la fila de ejemplo
# del layout o una fila con solo el default de una lista desplegable). Se
# descarta en silencio, no cuenta como rechazada.
CAMPOS_FILA_REAL = ("MODELO", "SERIE", "FALLA", "NUM CLIENTE")

# Columnas internas para ubicar la fila en el archivo original.
COL_ARCHIVO = "_ARCHIVO"
COL_FILA_EXCEL = "_FILA_EXCEL"
