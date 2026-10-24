# Reglas de negocio de Holanda (data/email-to-case/holanda.md en la wiki).
#
# DUDAS PARA JULIO (abiertas):
#   1. Mapeo layout -> pre-sábana (implementado en HOLANDA_SABANA._select).
#      Confirmado: CASO2 -> Folio y Ticket_Solicitud; TE, CONGELADOR,
#      CANAL y ESTADO no se mapean; Numero_Activo vacío; Canal fijo.
#      Por validar:
#        SAP                  -> Numero_Cliente
#        NOMBRE DEL CLIENTE   -> Nombre_Contacto_PDV  (trae razones
#                                sociales, p. ej. "CADENA COML OXXO S A DE
#                                C V": ¿contacto en PDV o titular?)
#        TIPO DE QUEJA +
#        CLASIFICADOR DE CASO -> Observaciones (el Clasificador siempre
#                                vale "Temas de congelador": ¿se quita?)
#   2. Llave del caso = CASO2 (implementado; TE y Origen pueden no venir,
#      Origen se infiere del sufijo H/G). Por confirmar: que un CASO2
#      nunca se reutiliza ni se corrige, y si la ausencia de TE/Origen es
#      recurrente.
#
# PENDIENTE (no implementado a propósito):
#   - "CONFIRMAR MODELO": falta saber contra qué catálogo se valida.
#   - Excepción de Yadira Espinosa (ver REMITENTES_SIN_DATOS_OBLIGATORIOS).
#   - MERMA: la columna MERMA de la respuesta del operador trae el id de
#     merma generado por el espejo de la pre-sábana (SUFIJO_MERMA). El
#     outbound todavía no la lee ni la guarda.

# Asunto del hilo de Holanda (correo real del 29-sep-2026: "Casos REPARE ").
# Por ahora solo se procesan correos con este asunto; se compara sin
# mayúsculas, sin espacios sobrantes, sin prefijos RE:/RV:/FW:/FWD: y sin
# etiquetas entre corchetes (p. ej. "[holanda]" del modo de prueba).
ASUNTO_HOLANDA = "casos repare"

# Identificador del cliente en las tablas compartidas: email_request usa
# `customer` en minúsculas y cooler_request usa `cliente` en mayúsculas.
CUSTOMER = "holanda"
CLIENTE_COOLER = "HOLANDA"

# Remitentes autorizados a mandar solicitudes sin CASO ni SAP (Yadira
# Espinosa). Vacío hasta tener su correo real: mientras tanto sus
# solicitudes se rechazan como cualquier otra sin CASO/SAP.
REMITENTES_SIN_DATOS_OBLIGATORIOS = {
    # "yadira.espinosa@unilever.com",  # TODO: confirmar el correo real con Julio/Leticia
}

# Pre-sábana (ver HOLANDA_SABANA):
#   - Canal: siempre este valor del catálogo CommercialChannels del
#     template, sin importar el CANAL que mande Holanda.
#   - Espejo de merma: cada solicitud se repite con este sufijo pegado a la
#     Serie; esa fila genera el id de merma.
CANAL_HOLANDA = "SC | Sin Canal"
SUFIJO_MERMA = "M"

# Valor canónico de la marca de duplicado (en los archivos reales el
# operador escribe "DUPLICADO", "SERIE DUPLICADA" o "DUPLICADA"). Un equipo
# es duplicado mientras tenga otro caso sin OS.
MARCA_DUPLICADO = "DUPLICADO"
