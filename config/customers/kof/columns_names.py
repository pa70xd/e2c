"""Columnas de KOF (Coca-Cola FEMSA).

KOF manda unos 10 formatos distintos. Cada encabezado se normaliza (mayúsculas,
sin acentos, espacios simples y sin espacios junto a ``/`` o ``-``) y se busca
aquí; lo que no está se descarta.

Estructuras conocidas:
  * "Reportes por falla de enfriador": MODELO; No SERIE; FALLA;
    DELEGACION/MUNICIPIO/CIUDAD; No CLIENTE DETALLISTA- CONCATENADO;
    ID DISTRIBUIDOR; ID DETALLISTA; CEDIS/DISTRIBUIDORA/ SUCURSAL;
    OBSERVACIONES; SOLICITUD DE SERVICIO; ACTIVO/PLACA; OS REPARE.
  * Bitácora de movimientos: "Folio (.Net)", "Tipo de Movimiento" y columnas
    separadas de serie, modelo y SAP para el equipo a instalar y a retirar.
    TODO(kof): los nombres exactos de la bitácora no están documentados; los
    alias de abajo son los observados en la estructura descrita y se amplían
    cuando lleguen los formatos reales.
"""

# Columnas canónicas del parser.
FOLIO = "FOLIO"
TIPO_MOVIMIENTO = "TIPO MOVIMIENTO"
FALLA = "FALLA"
SOLICITUD = "SOLICITUD"
MODELO = "MODELO"
SERIE = "SERIE"
ACTIVO = "ACTIVO"
MODELO_RETIRO = "MODELO RETIRO"
SERIE_RETIRO = "SERIE RETIRO"
ACTIVO_RETIRO = "ACTIVO RETIRO"
ID_CLIENTE = "ID CLIENTE"
CLIENTE_CONCATENADO = "CLIENTE CONCATENADO"
ID_DISTRIBUIDOR = "ID DISTRIBUIDOR"
CEDIS = "CEDIS"
PLAZA = "PLAZA"
CIUDAD = "CIUDAD"
RAZON_SOCIAL = "RAZON SOCIAL"
DIRECCION = "DIRECCION"
CP = "CP"
COLONIA = "COLONIA"
TELEFONO = "TELEFONO"
OBSERVACIONES = "OBSERVACIONES"
FECHA = "FECHA DE SOLICITUD"
OS = "OS"

NAMES_COLUMNS = {
    # Folio de KOF
    "FOLIO (.NET)": FOLIO,
    "FOLIO(.NET)": FOLIO,
    "FOLIO .NET": FOLIO,
    "FOLIO NET": FOLIO,
    "FOLIO": FOLIO,

    "TIPO DE MOVIMIENTO": TIPO_MOVIMIENTO,
    "TIPO MOVIMIENTO": TIPO_MOVIMIENTO,

    "FALLA": FALLA,
    "FALLAS": FALLA,
    "SOLICITUD DE SERVICIO": SOLICITUD,

    # Equipo (a instalar en la bitácora)
    "MODELO": MODELO,
    "MODELO A INSTALAR": MODELO,
    "MODELO INSTALAR": MODELO,
    "NO SERIE": SERIE,
    "NO. SERIE": SERIE,
    "SERIE": SERIE,
    "SERIE A INSTALAR": SERIE,
    "SERIE INSTALAR": SERIE,
    "ACTIVO/PLACA": ACTIVO,
    "ACTIVO": ACTIVO,
    "PLACA": ACTIVO,
    "SAP": ACTIVO,
    "SAP A INSTALAR": ACTIVO,
    "SAP INSTALAR": ACTIVO,

    # Equipo a retirar (Cambio de Equipo)
    "MODELO A RETIRAR": MODELO_RETIRO,
    "MODELO RETIRAR": MODELO_RETIRO,
    "SERIE A RETIRAR": SERIE_RETIRO,
    "SERIE RETIRAR": SERIE_RETIRO,
    "SAP A RETIRAR": ACTIVO_RETIRO,
    "SAP RETIRAR": ACTIVO_RETIRO,

    # Punto de venta
    "ID DETALLISTA": ID_CLIENTE,
    "NO CLIENTE DETALLISTA": ID_CLIENTE,
    "ID CLIENTE": ID_CLIENTE,
    "NO CLIENTE DETALLISTA-CONCATENADO": CLIENTE_CONCATENADO,
    "ID DISTRIBUIDOR": ID_DISTRIBUIDOR,
    "CEDIS/DISTRIBUIDORA/SUCURSAL": CEDIS,
    "CEDIS": CEDIS,
    "PLAZA": PLAZA,
    "DELEGACION/MUNICIPIO/CIUDAD": CIUDAD,
    "MUNICIPIO": CIUDAD,
    "CIUDAD": CIUDAD,
    "NOMBRE": RAZON_SOCIAL,
    "NOMBRE DEL CLIENTE": RAZON_SOCIAL,
    "RAZON SOCIAL": RAZON_SOCIAL,
    "DIRECCION": DIRECCION,
    "DOMICILIO": DIRECCION,
    "CP": CP,
    "CODIGO POSTAL": CP,
    "COLONIA": COLONIA,
    "TELEFONO": TELEFONO,
    "OBSERVACIONES": OBSERVACIONES,
    "COMENTARIOS": OBSERVACIONES,
    "FECHA": FECHA,
    "FECHA DE SOLICITUD": FECHA,

    # OS de REPARE (conciliación outbound)
    "OS REPARE": OS,
    "OS": OS,
}

# Una fila es encabezado si reconoce al menos estas columnas y alguna llave.
MIN_COLUMNAS_ENCABEZADO = 3
LLAVES_ENCABEZADO = {SERIE, TIPO_MOVIMIENTO, FOLIO, FALLA}
# Filas revisadas para buscar el encabezado.
FILAS_BUSQUEDA_ENCABEZADO = 15
