"""Reglas de negocio de KOF (wiki de Solkos).

Ruta, con tres subtipos:
  * Servicio de distribuidor: reportes por falla (NO ENFRIA, LO CONGELA...).
  * Venta de material (extensión, charolas o parrillas): es ruta y NUNCA se
    reporta como falla (~90 % es "venta de extensión").
  * Proyectos especiales (instalaciones eléctricas): texto plano, sin serie,
    con el ID de servicio "áreas generales".
Movimiento: instalaciones, retiros, traslados y reubicaciones. Cobertura,
Equipo Adicional y Cambio de Equipo son instalación; Cambio de Equipo además
genera el retiro del equipo anterior.
"""

CUSTOMER = "kof"
CBU = "KOF"
PRIORIDAD = "HIGH"

SABANA_MOVIMIENTO = "MOVIMIENTO"
SABANA_RUTA = "RUTA"

# Tipo de servicio que se guarda en cooler_request.tipo_servicio.
INSTALACION = "INSTALACION"
RETIRO = "RETIRO"
TRASLADO = "TRASLADO"
REUBICACION = "REUBICACION"
SERVICIO_DISTRIBUIDOR = "SERVICIO DE DISTRIBUIDOR"
VENTA_MATERIAL = "VENTA DE MATERIAL"
PROYECTO_ESPECIAL = "PROYECTO ESPECIAL"

TIPOS_RUTA = (SERVICIO_DISTRIBUIDOR, VENTA_MATERIAL, PROYECTO_ESPECIAL)
TIPOS_MOVIMIENTO = (INSTALACION, RETIRO, TRASLADO, REUBICACION)

CAMBIO_DE_EQUIPO = "CAMBIO DE EQUIPO"

# "Tipo de Movimiento" normalizado -> tipos que genera (en orden).
MOVIMIENTOS = {
    "COBERTURA": (INSTALACION,),
    "EQUIPO ADICIONAL": (INSTALACION,),
    "INSTALACION": (INSTALACION,),
    CAMBIO_DE_EQUIPO: (INSTALACION, RETIRO),
    "CAMBIO DE EQUIPOS": (INSTALACION, RETIRO),
    "RETIRO": (RETIRO,),
    "TRASLADO": (TRASLADO,),
    "REUBICACION": (REUBICACION,),
}

# Venta de material: se busca en FALLA y SOLICITUD DE SERVICIO (no en
# OBSERVACIONES, donde una "parrilla rota" sí es falla).
VENTA_MATERIAL_REGEX = r"\b(EXTENSION(ES)?|CHAROLAS?|PARRILLAS?)\b"

# TODO(kof): ID de servicio exacto de "áreas generales" en la sábana de ruta.
# La wiki solo dice "el ID de servicio áreas generales"; se deja el texto tal
# cual hasta que operación confirme el código.
ID_SERVICIO_AREAS_GENERALES = "AREAS GENERALES"

# TODO(kof): sufijo "R" de la serie en reubicaciones. La wiki dice que existe,
# pero no si KOF ya lo manda en la serie o si REPARE debe agregarlo, ni si se
# quita para conciliar. Hoy la serie se guarda tal como llega.
SUFIJO_REUBICACION = "R"

# Formato de texto plano (proyectos especiales): líneas "CLAVE: valor".
# TODO(kof): las claves reales del correo en texto plano no están documentadas;
# se aceptan los mismos alias de columns_names.py y se exige el folio.
MIN_CLAVES_TEXTO_PLANO = 3

# Motivos de rechazo (van en el Excel de resultado).
MOTIVO_SIN_SERIE = "[RECHAZADO] Serie vacía"
MOTIVO_SIN_SERIE_RETIRO = "[RECHAZADO] Serie del equipo a retirar vacía"
MOTIVO_SIN_DETALLISTA = "[RECHAZADO] ID de detallista vacío"
MOTIVO_MOVIMIENTO = "[RECHAZADO] Tipo de movimiento no reconocido"
MOTIVO_SIN_TIPO = "[RECHAZADO] Sin tipo de movimiento ni falla"
MOTIVO_DUPLICADA = "[RECHAZADO] Serie duplicada en el archivo"
