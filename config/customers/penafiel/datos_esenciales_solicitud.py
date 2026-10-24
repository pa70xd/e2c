# datos_esenciales = [
#     # "MODELO",
#     "SERIE",
#     "TIPO DE SERVICIO",
#     "RAZON SOCIAL",
#     # "DIRECCION",
#     "CP",
#     # "CIUDAD",
#     # "COLONIA",
#     "LATITUD",
#     "LONGITUD",
#     "TELEFONO 1",
#     # "TELEFONO 2",
#     # "COMENTARIOS",
#     # "CANAL",
# ]

# datos_no_esenciales = [
#     "MODELO",
#     # "SERIE",
#     # "TIPO DE SERVICIO",
#     # "RAZON SOCIAL",
#     "DIRECCION",
#     # "CP",
#     "CIUDAD",
#     "COLONIA",
#     # "LATITUD",
#     # "LONGITUD",
#     # "TELEFONO 1",
#     # "TELEFONO 2",
#     "COMENTARIOS",
#     "CANAL"

# ]


TIPOS_SERVICIO_VALIDOS = [
    "INSTALACION",
    "INSTALACIONES",
    "ALTA",
    "ALTAS",
    "INSTALACIÓN",

    "RUTA",
    "RUTAS",
    "REPARACION",
    "REPARACIÓN",


    "MOVIMIENTO",
    "MOVIMIENTOS",
    "TRASLADOS",

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
] 



CBU_NAMES = {
    "PENAFIEL": "PENAFIEL",
    "penafiel": "PENAFIEL",
    "penañafiel": "PENAFIEL",
    "peñafiel": "PENAFIEL",
}

def get_cbu_name(name: str) -> str | None:
    return CBU_NAMES.get(name.strip().upper())

def get_cbu_names_valid():
    return list(CBU_NAMES.keys())