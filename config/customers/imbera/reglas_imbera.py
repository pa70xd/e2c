"""Reglas de negocio de Imbera (buzón cliente.imbera@) y lo común con
Torrey (wiki de Solkos, Fase 4).

Imbera es un buzón MULTI-CLIENTE: llegan sub-clientes (Jumex,
laboratorios como PISA o Electrolit, distribuidores, comercializadores)
mezclados con solicitudes propias de Imbera. El cliente real se lee del
CONTENIDO (asunto, cuerpo, Excel), no de la cuenta que envía.

Lo que hace la etapa 1 (este parser):
  * Leer el "Lay Out Repare", detectar el sub-cliente, MARCAR si la
    solicitud es de garantía y registrar las filas.
  * NO valida la garantía (plazos, SAP): eso es la etapa 2.

TODO (no inventado, pendiente de negocio):
  1. Cómo se nombra al sub-cliente en la base. Hoy: cooler_request.cliente
     = cliente de la OS (IMBERA/TORREY) y el sub-cliente detectado, tal
     cual, en cooler_request.cbu (misma analogía que Holanda con Origen).
  2. Criterio exacto de garantía. Hoy: cualquier SEÑAL_GARANTIA marca la
     fila; la lista de señales usadas queda en gestion_observaciones.
  3. Qué clientes son "institucionales" (únicos con instalación). La lista
     está vacía: mientras no se defina, la instalación NO se restringe.
  4. Formato de la OS de REPARE para Imbera/Torrey (Danone usa el prefijo
     403). Hoy cualquier OS numérica concilia la fila como ACCEPTED.
  5. Señales de garantía sin leer el archivo: cualquier PDF cuenta como
     factura y la foto de la placa solo se reconoce por el nombre
     ("placa"). La solicitud por teléfono no pasa por este parser.
"""

import re

CUSTOMER = "imbera"
CLIENTE_OS = "IMBERA"

# ---------------------------------------------------------------------------
# Folio del asunto: IMB-ddmmaa_n (solicitud de servicio) y REP-ddmmaa_n
# (orden de servicio). Se guarda en cooler_request.folio.
# ---------------------------------------------------------------------------
PATRON_FOLIO = re.compile(r"\b((?:IMB|REP)-\d{6}_\d+)\b", re.IGNORECASE)

# OS que trae el asunto de una garantía ("SOLICITUD DE GARANTIA OS123 X").
PATRON_OS_ASUNTO = re.compile(r"\bOS\s*-?\s*(\d{4,})\b", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Asuntos conocidos -> (tipo, grupo con el cliente). Se evalúan sobre el
# asunto sin RE:/RV:/FW:, normalizado (mayúsculas, sin acentos, "--" con
# espacios simples).
# ---------------------------------------------------------------------------
ASUNTOS = (
    # SOLICITUD DE SERVICIO -- <CLIENTE> <PLAZA> -- INSTALACION -- IMB-ddmmaa_n
    ("movimiento", re.compile(
        r"^SOLICITUD DE SERVICIO\s*-+\s*(?P<cliente>.+?)\s*-+\s*(?P<movimiento>INSTALACION|RETIRO|TRASLADO)\b")),
    # ORDEN DE SERVICIO <CLIENTE> -- <PLAZA> -- REP-ddmmaa_n
    ("ruta", re.compile(
        r"^ORDEN DE SERVICIO\s+(?P<cliente>.+?)\s*-+\s*(?P<plaza>.+?)\s*-+\s*REP-")),
    # SOLICITUD DE GARANTIA OS<n> <comercializador>
    ("garantia", re.compile(
        r"^SOLICITUD DE GARANTIA\s+OS\s*-?\s*\d+\s+(?P<cliente>.+)$")),
    # SOLICITUD DE OS PARA <distribuidor> <plaza>
    ("ruta", re.compile(
        r"^SOLICITUD DE OS PARA\s+(?P<cliente>.+)$")),
    # REPORTE VITRINA <modelo>
    ("ruta", re.compile(r"^REPORTE VITRINA\s+(?P<modelo>.+)$")),
)

# Sub-clientes conocidos (se buscan como palabra en asunto, cuerpo y en las
# columnas CANAL / FALLA del Excel). El primero que aparezca gana. TODO:
# catálogo real de sub-clientes y su nombre en la base (ver TODO 1).
SUBCLIENTES = {
    "JUMEX": "JUMEX",
    "PISA": "PISA",
    "ELECTROLIT": "ELECTROLIT",
}

# Cuando no se reconoce el sub-cliente.
SUBCLIENTE_DESCONOCIDO = None

# ---------------------------------------------------------------------------
# Ruta: tres variantes.
#   * folio_app: viene de la app, siempre con número de folio.
#   * proyecto_especial: proyectos especiales.
#   * distribuidora: distribuidora o detallista (el resto).
# ---------------------------------------------------------------------------
PATRON_FOLIO_APP = re.compile(r"\bFOLIO(?:\s+DE\s+LA\s+APP|\s+APP)?\s*[:#]?\s*(\d{3,})\b")
PATRON_PROYECTO_ESPECIAL = re.compile(r"\bPROYECTOS?\s+ESPECIAL(?:ES)?\b")

# ---------------------------------------------------------------------------
# Garantía (solo se MARCA; la valida la etapa 2).
# ---------------------------------------------------------------------------
PATRON_GARANTIA = re.compile(r"\bGARANTIAS?\b")
PATRON_EQUIPO_NUEVO_DANADO = re.compile(
    r"\bEQUIPOS?\s+NUEVOS?\b.{0,40}\b(DA[NÑ]ADOS?|GOLPEADOS?|ROTOS?|NO ENFRIA|NO FUNCIONA)\b"
)
PATRON_FOTO_PLACA = re.compile(r"PLACA", re.IGNORECASE)
PATRON_FACTURA = re.compile(r"FACTURA", re.IGNORECASE)
EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".heic", ".webp")
# Parte local de un buzón de garantías (remitente o destinatario).
PATRON_BUZON_GARANTIAS = re.compile(r"^garantias?[._-]?|[._-]garantias?@", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Movimientos: solo INSTALACION (y solo para institucionales). No hay
# retiros ni traslados por garantía.
# ---------------------------------------------------------------------------
MOVIMIENTO_INSTALACION = "INSTALACION"
# Se rechazan: Imbera/Torrey no atienden retiros ni traslados.
MOVIMIENTOS_NO_ATENDIDOS = {"RETIRO", "TRASLADO"}
MOVIMIENTOS = {MOVIMIENTO_INSTALACION} | MOVIMIENTOS_NO_ATENDIDOS
CLIENTES_INSTITUCIONALES: set[str] = set()  # TODO 3

# ---------------------------------------------------------------------------
# Correos sin alta.
# ---------------------------------------------------------------------------
# Seguimiento / consulta de estatus (cliente -> REPARE, sin Excel).
PATRON_SEGUIMIENTO = re.compile(
    r"\b(SEGUIMIENTO|ESTATUS|STATUS|AVANCE|QUEJA)\b"
)
# REPARE -> distribuidor con estatus, sin OS: no_os (no concilia nada).
PATRON_ESTATUS_REPARE = re.compile(
    r"\b(EN ESPERA DE (LA )?PIEZAS?|ESPERA DE PIEZAS?|EN PROCESO|EN RUTA|PROGRAMAD[OA])\b"
)

# ---------------------------------------------------------------------------
# Conciliación outbound desde TEXTO ("Comparto orden generada: 123456").
# ---------------------------------------------------------------------------
PATRON_OS_TEXTO = re.compile(
    r"\bORDEN(?:ES)?\s+(?:DE\s+SERVICIO\s+)?GENERADAS?\s*[:#]?\s*((?:\d{5,}\s*(?:,|Y|/)?\s*)+)"
)
PATRON_NUMERO_OS = re.compile(r"\d{5,}")

PRIORIDAD = "MEDIUM"
