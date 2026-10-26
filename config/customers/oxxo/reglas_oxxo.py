# Reglas de Oxxo (dos buzones, dos clientes de REPARE).
#
#   cliente.oxxo@    -> "oxxo"           mantenimiento (OS de ruta, texto plano)
#   cliente.oxogar@  -> "oxxo_garantias" garantías (texto plano y Excel)
#
# Identificadores en las tablas compartidas: email_request.customer va en
# minúsculas y cooler_request.cliente en mayúsculas (igual que Holanda).

CUSTOMER_MANTENIMIENTO = "oxxo"
CUSTOMER_GARANTIAS = "oxxo_garantias"

CLIENTE_COOLER_MANTENIMIENTO = "OXXO"
CLIENTE_COOLER_GARANTIAS = "OXXO_GARANTIAS"

# Un folio de garantía puede existir como mantenimiento y viceversa: la
# búsqueda de duplicados y escalaciones mira los dos clientes.
CLIENTES_COOLER = (CLIENTE_COOLER_MANTENIMIENTO, CLIENTE_COOLER_GARANTIAS)

# Oxxo ya tiene una PoC automatizada fuera de este repo. Si las dos procesan
# el mismo buzón se duplican las OS, así que estos parsers solo corren si el
# nombre del cliente está en esta variable (lista separada por comas).
VAR_CLIENTES_HABILITADOS = "E2C_CLIENTES_HABILITADOS"

# Ticket de mantenimiento: exactamente 8 dígitos. Cualquier otra cosa se
# trata como campo faltante y el correo va a revisión (no se inventa).
LONGITUD_TICKET = 8

# Prioridad que se guarda en cooler_request.prioridad (la de la plantilla va
# en gestion_observaciones; los demás clientes solo usan MEDIA o NULL).
PRIORIDAD_COOLER = "MEDIA"

# Tipo de servicio de las OS de garantía.
TIPO_SERVICIO_GARANTIA = "GARANTIA"

# Motivos (códigos sin PII) de las filas que van a revisión.
MOTIVO_SIN_TICKET = "falta_ticket"
MOTIVO_TICKET_INCONSISTENTE = "ticket_inconsistente"
MOTIVO_SIN_FOLIO = "falta_folio"
MOTIVO_ESCALACION = "escalacion_garantia"
MOTIVO_SIN_EXCEL = "falta_excel"
MOTIVO_EXCEL_ILEGIBLE = "excel_ilegible"
MOTIVO_CONTEO_OS = "conteo_os_distinto"
