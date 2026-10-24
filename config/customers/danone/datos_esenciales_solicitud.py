datos_esenciales = [
    "ID CLIENTE",
    "FECHA DE SOLICITUD",
    "MODELO",
    "# SERIE DEL FABRICANTE",
    "# SERIE DANONE/BNF",
    "CANAL",
    "REGIÓN",
    "CEDIS",
    "RAZÓN SOCIAL",
    "Dirección",
    "CP",
    "Ciudad",
    "Colonia",
    "LATITUD",
    "LONGITUD",
    "RUTA",
    "TELÉFONO 1",
    "COMENTARIOS",
    "CBU",
]

datos_no_esenciales = [
    'TELÉFONO 2',
    "TIPO DE SERVICIO",

]


TIPOS_SERVICIO_VALIDOSs = [
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
    "ONE DANONE": "DANONE",
    "DANONE": "DANONE",
    "EDP": "DANONE",
    "ONE COOLER": "DANONE",

    "BONAFONT": "BONAFONT",
    "BNF": "BONAFONT",
}

def get_cbu_name(name: str) -> str | None:
    return CBU_NAMES.get(name.strip().upper())

def get_cbu_names_valid():
    return list(CBU_NAMES.keys())