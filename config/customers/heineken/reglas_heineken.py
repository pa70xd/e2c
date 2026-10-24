# Reglas de negocio de Heineken (cliente.hnk@).
#
# PENDIENTE:
#   - D2D: texto de canal -> cooler_request.canal y puesto D23xx -> cbu (abierto a observaciones).
#   - Ruta: si "NUMERO DE CASO / FOLIO" llega llena, ¿va a Folio en lugar de ORDEN?

CUSTOMER = "heineken"
CLIENTE_COOLER = "HEINEKEN"

FLUJO_D2D = "D2D"
FLUJO_RUTA = "RUTA"

# Palabras que debe contener el asunto (normalizado) para cada flujo.
ASUNTO_D2D = ("PRECARGA", "D2D")
ASUNTO_RUTA = ("MANTENIMIENTO FERGUEZ",)

SERIE_GENERICA = "ASIGNAR SERIE GENERICA"
MARCA_DUPLICADO = "DUPLICADO"

# Valores que el cliente usa como "vacío".
VALORES_VACIOS = {"0", "NA", "N/A", "-"}

CANAL_SIN_CANAL = "SC | Sin Canal"

# ---- D2D ----
SOLICITUD_D2D = "MOVIMIENTO"

# Texto de canal -> puesto de trabajo (región Oriente, sucursal 7203).
CANAL_A_PUESTO = {
    "CANAL MODERNO": "D2362",
    "PUNTO DE VENTA": "D2363",
    "CENTRO DE CONSUMO": "D2364",
}

# Puesto de trabajo -> distribuidora (catálogo de template_movimientos).
PUESTO_A_DISTRIBUIDORA = {
    "D2362": "502307 | HEINEKEN ORIENTE CM",
    "D2363": "502308 | HEINEKEN ORIENTE PV",
    "D2364": "502309 | HEINEKEN ORIENTE CC",
}

# FALLA -> (categoría, línea, tipo de servicio, id de servicio, tipo de actividad, actividad, prefijo de serie genérica)
SERVICIOS_D2D = {
    "ENTREGA DE ENF": ("12 | ENFRIADOR", None, "1003 | MOVIMIENTOS", "3207 | D2D INSTALACION",
                       "2001 | INSTALACION", "3001 | INSTALACION DE EQUIPO", "HEI"),
    "RETIRO DE ENF": ("12 | ENFRIADOR", None, "1003 | MOVIMIENTOS", "3217 | D2D RETIRO",
                      "2002 | MOVIMIENTO", "3002 | RETIRO DE EQUIPO", "HEI"),
    "RETIRO POR CAMBIO": ("12 | ENFRIADOR", None, "1003 | MOVIMIENTOS", "3217 | D2D RETIRO",
                          "2002 | MOVIMIENTO", "3002 | RETIRO DE EQUIPO", "HEI"),
    "CAMBIO DE ENF": ("12 | ENFRIADOR", None, "1003 | MOVIMIENTOS", "3217 | D2D RETIRO",
                      "2002 | MOVIMIENTO", "3002 | RETIRO DE EQUIPO", "HEI"),
    "RETIRO DE MOB": ("1B | MOBILIARIO", "OTROS", "1003 | MOVIMIENTOS", "3B17 | D2D RETIRO",
                      "2002 | MOVIMIENTO", "3002 | RETIRO DE EQUIPO", "MOB"),
}

# ---- Ruta ----
TIPO_MOVIMIENTO_RUTA = "REPARACION MERCADO"
DISTRIBUIDORA_RUTA = "500166 | D1604 | DIST. CM VALLEJO REHAB. - COACALCO"
