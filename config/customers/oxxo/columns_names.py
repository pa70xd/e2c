# Layout "Lay Out Repare" de los Excel de garantías de Oxxo (mismo formato
# que Imbera; puede ser una línea de cuartos fríos). Encabezado normalizado
# (sin acentos, mayúsculas, espacios colapsados) -> nombre canónico.
#
# Pendiente: cuando parsers/core/lector.py llegue a la base, el lector común
# resuelve los alias y este archivo se reduce a los nombres canónicos.

NAMES_EXCEL = {
    "FOLIO": "FOLIO",
    "NUMERO DE CASO/FOLIO": "FOLIO",
    "NUMERO DE CASO": "FOLIO",
    "TICKET": "FOLIO",

    "ID CLIENTE": "ID CLIENTE",
    "NO CLIENTE DETALLISTA": "ID CLIENTE",
    "NO. CLIENTE DETALLISTA": "ID CLIENTE",
    "DETERMINANTE": "ID CLIENTE",
    "CR": "ID CLIENTE",
    "CR TIENDA": "ID CLIENTE",

    "FECHA DE SOLICITUD": "FECHA",
    "FECHA SOLICITUD": "FECHA",
    "FECHA": "FECHA",

    "MODELO": "MODELO",
    "SERIE": "SERIE",
    "NO SERIE": "SERIE",
    "NUMERO SERIE": "SERIE",
    "SERIE FABRICANTE": "SERIE",
    "SERIE DEL FABRICANTE": "SERIE",

    "TIPO DE SERVICIO": "TIPO DE SERVICIO",
    "SOLICITUD DE SERVICIO": "TIPO DE SERVICIO",
    "TIPO DE MOVIMIENTO": "TIPO DE SERVICIO",

    "FALLA": "FALLA",
    "FALLA REPORTADA": "FALLA",
    "DIAGNOSTICO Y/O FALLA": "FALLA",
    "OBSERVACIONES": "FALLA",

    "REGION": "REGION",
    "PLAZA": "PLAZA",
    "RAZON SOCIAL": "RAZON SOCIAL",
    "NOMBRE PUNTO DE VENTA": "RAZON SOCIAL",
    "NOMBRE TIENDA": "RAZON SOCIAL",
    "DIRECCION": "DIRECCION",
    "CALLE Y NUMERO": "DIRECCION",
    "COLONIA": "COLONIA",
    "MUNICIPIO": "MUNICIPIO",
    "CP": "CP",
    "CODIGO POSTAL": "CP",
    "TELEFONO": "TELEFONO",
    "NUM. TEL": "TELEFONO",
}

# Con estos dos (o más) alias reconocidos se considera que una fila es el
# encabezado. Se busca en las primeras filas de la hoja.
MIN_ALIAS_ENCABEZADO = 2
FILAS_BUSQUEDA_ENCABEZADO = 10

# Un Excel con más filas que esto se rechaza a revisión (no es un layout
# de solicitud, es otra cosa).
MAX_FILAS_EXCEL = 500
