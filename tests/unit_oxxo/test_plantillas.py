"""Variaciones de las plantillas de Oxxo (acentos, mayúsculas, espacios,
líneas extra, campos faltantes). Todo inventado."""

import unicodedata

import pytest

from parsers.oxxo_parse.plantillas import (
    contar_os_solicitadas,
    es_asunto_excel_garantias,
    es_asunto_mantenimiento,
    es_asunto_seguimiento,
    limpiar_asunto,
    normalizar_telefono,
    parse_mantenimiento,
    parse_seguimiento,
    parsear_fecha,
)

CUERPO_MANT = """Buen día,
La tienda OXXO 50EJE NORTE TIENDA EJEMPLO UNO, ubicada en Calle Ficticia 100, Colonia Ejemplo, nos reportó lo siguiente
Motivo: El equipo no enfría
Representante Propietario: Persona Ejemplo Uno
Prestador de Servicio: REPARE - Norte
Categoria: Refrigeración
Falla especifica: Cuarto frío sin temperatura. El número de ticket es: 10000001. Prioridad: ALTA
"""


def _sin_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c))


# ------------------------------------------------------------ mantenimiento

def test_mantenimiento_campos():
    d = parse_mantenimiento("Abierto-Asignado ----> 10000001", CUERPO_MANT)
    assert d.ticket == "10000001"
    assert d.motivo_revision is None
    assert d.cr == "50EJE"
    assert d.tienda == "NORTE TIENDA EJEMPLO UNO"
    assert d.direccion == "Calle Ficticia 100, Colonia Ejemplo"
    assert d.motivo == "El equipo no enfría"
    assert d.propietario == "Persona Ejemplo Uno"
    assert d.region == "Norte"
    assert d.categoria == "Refrigeración"
    assert d.falla == "Cuarto frío sin temperatura"
    assert d.prioridad == "ALTA"


@pytest.mark.parametrize("variacion", ["mayusculas", "sin_acentos", "espacios", "lineas_extra", "crlf", "nfd"])
def test_mantenimiento_tolera_variaciones(variacion):
    cuerpo = CUERPO_MANT
    if variacion == "mayusculas":
        cuerpo = cuerpo.upper()
    elif variacion == "sin_acentos":
        cuerpo = _sin_acentos(cuerpo)
    elif variacion == "espacios":
        cuerpo = cuerpo.replace(": ", " :   ").replace("Motivo", "  MOTIVO ").replace(" ", "  ")
    elif variacion == "lineas_extra":
        cuerpo = "\n\n" + cuerpo.replace("\n", "\n\n") + "\n--\nFirma Ejemplo\n"
    elif variacion == "crlf":
        cuerpo = cuerpo.replace("\n", "\r\n")
    elif variacion == "nfd":
        cuerpo = unicodedata.normalize("NFD", cuerpo)
    d = parse_mantenimiento("ABIERTO - ASIGNADO  ---->   10000001", cuerpo)
    assert d.ticket == "10000001"
    assert d.cr == "50EJE"
    assert d.prioridad == "ALTA"
    assert d.region and d.region.lower() == "norte"
    assert d.motivo and "enfr" in d.motivo.lower()


def test_mantenimiento_conserva_acentos_del_valor():
    d = parse_mantenimiento("Abierto-Asignado ----> 10000001", CUERPO_MANT)
    assert d.categoria == "Refrigeración"
    assert d.motivo == "El equipo no enfría"


def test_mantenimiento_ticket_solo_en_cuerpo():
    d = parse_mantenimiento("Abierto-Asignado ---->", CUERPO_MANT)
    assert d.ticket == "10000001"


def test_mantenimiento_ticket_solo_en_asunto():
    cuerpo = CUERPO_MANT.replace("El número de ticket es: 10000001. ", "")
    d = parse_mantenimiento("RE: Abierto-Asignado ----> 10000001", cuerpo)
    assert d.ticket == "10000001"


@pytest.mark.parametrize("asunto,cuerpo,motivo", [
    ("Abierto-Asignado ---->", CUERPO_MANT.replace("10000001", "(pendiente)"), "falta_ticket"),
    ("Abierto-Asignado ----> 1000001", CUERPO_MANT.replace("10000001", "1000001"), "falta_ticket"),
    ("Abierto-Asignado ----> 100000012", CUERPO_MANT.replace("10000001", "100000012"), "falta_ticket"),
    ("Abierto-Asignado ----> 10000002", CUERPO_MANT, "ticket_inconsistente"),
])
def test_mantenimiento_sin_ticket_va_a_revision(asunto, cuerpo, motivo):
    d = parse_mantenimiento(asunto, cuerpo)
    assert d is not None
    assert d.ticket is None
    assert d.motivo_revision == motivo


def test_mantenimiento_no_es_la_plantilla():
    assert parse_mantenimiento("Cerrado ----> 10000001", "Sin relación") is None


def test_mantenimiento_sin_encabezado_de_tienda_conserva_ticket():
    cuerpo = "Motivo: Falla\nEl número de ticket es: 10000001\nPrioridad: media"
    d = parse_mantenimiento("Abierto-Asignado ----> 10000001", cuerpo)
    assert d.ticket == "10000001"
    assert d.cr is None and d.tienda is None and d.direccion is None
    assert d.prioridad == "MEDIA"


# ------------------------------------------------------------ garantías

CUERPO_SEG = """Fecha de generación de folio: 02/03/2026 09:30
Descripción Servicio (Plaza): NORTE
CR Tienda: 50EJE
Nombre de quien reporta: Persona Ejemplo Dos
Teléfono de contacto: 55 5501 0002
Correo Electrónico: persona.dos@example.com
Equipo: Cuarto frío
Marca/Fabricante del Equipo: Marca Ejemplo
Modelo: MOD-EJ-01
Numero Serie: SERIE-EJ-0001
Diagnostico y/o Falla: Compresor no arranca
Direccion de Envío de Garantía: Calle Ficticia 200
Folio Referencia Mantenimiento: 10000001
Mensaje de Seguimiento: se cumplió el tiempo y no se ha atendido
"""


def test_seguimiento_campos():
    d = parse_seguimiento("Seguimiento a Folio: gar-0001", CUERPO_SEG)
    assert d.folio == "GAR-0001"
    assert d.motivo_revision is None
    assert d.fecha.isoformat() == "2026-03-02T09:30:00"
    assert d.plaza == "NORTE"
    assert d.cr == "50EJE"
    assert d.reporta == "Persona Ejemplo Dos"
    assert d.telefono == "5555010002"
    assert d.equipo == "Cuarto frío"
    assert d.marca == "Marca Ejemplo"
    assert d.modelo == "MOD-EJ-01"
    assert d.serie == "SERIE-EJ-0001"
    assert d.diagnostico == "Compresor no arranca"
    assert d.direccion_envio == "Calle Ficticia 200"
    assert d.folio_mantenimiento == "10000001"
    assert d.mensaje == "se cumplió el tiempo y no se ha atendido"


def test_seguimiento_no_conserva_el_correo_del_solicitante():
    d = parse_seguimiento("Seguimiento a Folio: GAR-0001", CUERPO_SEG)
    assert "persona.dos@example.com" not in repr(d)


@pytest.mark.parametrize("variacion", ["mayusculas", "sin_acentos", "espacios", "lineas_extra", "orden", "valor_abajo"])
def test_seguimiento_tolera_variaciones(variacion):
    cuerpo = CUERPO_SEG
    if variacion == "mayusculas":
        cuerpo = cuerpo.upper()
    elif variacion == "sin_acentos":
        cuerpo = _sin_acentos(cuerpo)
    elif variacion == "espacios":
        cuerpo = cuerpo.replace(": ", "  :    ")
    elif variacion == "lineas_extra":
        cuerpo = "\n\n" + cuerpo.replace("\n", "\n\n\n") + "\n\n--\nFirma Ejemplo"
    elif variacion == "orden":
        cuerpo = "\n".join(reversed(cuerpo.strip().split("\n")))
    elif variacion == "valor_abajo":
        cuerpo = cuerpo.replace("Modelo: ", "Modelo:\n")
    d = parse_seguimiento("SEGUIMIENTO  A  FOLIO :  GAR-0001", cuerpo)
    assert d.folio == "GAR-0001"
    assert d.cr == "50EJE"
    assert d.serie and d.serie.upper() == "SERIE-EJ-0001"
    assert d.modelo and d.modelo.upper() == "MOD-EJ-01"
    assert d.telefono == "5555010002"
    assert d.folio_mantenimiento == "10000001"
    assert d.mensaje and "cumpli" in d.mensaje.lower()


def test_seguimiento_mensaje_en_varias_lineas():
    cuerpo = CUERPO_SEG.replace(
        "Mensaje de Seguimiento: se cumplió el tiempo y no se ha atendido",
        "Mensaje de Seguimiento: se cumplió el tiempo\ny no se ha atendido\n\nSaludos\nPersona Ejemplo",
    )
    d = parse_seguimiento("Seguimiento a Folio: GAR-0001", cuerpo)
    assert d.mensaje == "se cumplió el tiempo y no se ha atendido"


def test_seguimiento_con_prefijos_y_etiquetas_en_asunto():
    d = parse_seguimiento("RE: [externo] Seguimiento a Folio: gar-0001", CUERPO_SEG)
    assert d.folio == "GAR-0001"


def test_seguimiento_folio_solo_en_cuerpo():
    d = parse_seguimiento("Seguimiento a Folio", "Folio: GAR-0009\n" + CUERPO_SEG)
    assert d.folio == "GAR-0009"


@pytest.mark.parametrize("asunto,cuerpo,motivo", [
    ("Seguimiento a Folio:", CUERPO_SEG, "falta_folio"),
    ("Seguimiento a Folio: ??", CUERPO_SEG, "falta_folio"),
    ("Seguimiento a Folio: GAR-0001", "Folio: GAR-0002\n" + CUERPO_SEG, "folio_inconsistente"),
])
def test_seguimiento_sin_folio_va_a_revision(asunto, cuerpo, motivo):
    d = parse_seguimiento(asunto, cuerpo)
    assert d.folio is None
    assert d.motivo_revision == motivo


def test_seguimiento_no_es_la_plantilla():
    assert parse_seguimiento("Otro asunto", CUERPO_SEG) is None


# ------------------------------------------------------------ utilidades

@pytest.mark.parametrize("asunto,esperado", [
    ("Abierto-Asignado ----> 10000001", True),
    ("RE: ABIERTO - ASIGNADO --> 10000001", True),
    ("Abierto-Cancelado ----> 10000001", False),
])
def test_asunto_mantenimiento(asunto, esperado):
    assert es_asunto_mantenimiento(asunto) is esperado


@pytest.mark.parametrize("asunto,esperado", [
    ("Solicitud de Orden de Servicio Oxxo Tienda Ejemplo", True),
    ("RE: Solicitud de generación de OS para cliente Ejemplo - OXO", True),
    ("Re: SOLICITUD DE GENERACION DE OS PARA CLIENTE EJEMPLO - OXO", True),
    ("Solicitud de cotización", False),
])
def test_asunto_excel(asunto, esperado):
    assert es_asunto_excel_garantias(asunto) is esperado


def test_asunto_seguimiento():
    assert es_asunto_seguimiento("RV: Seguimiento a Folio: X1")
    assert not es_asunto_seguimiento("Seguimiento general")


def test_limpiar_asunto():
    assert limpiar_asunto("  RE:  FW: [x] Solicitud   de Generación ") == "Solicitud de Generacion"


@pytest.mark.parametrize("cuerpo,esperado", [
    ("Les comparto las 4 OS", 4),
    ("4 os adjuntas", 4),
    ("Adjunto 12 OS de garantía", 12),
    ("4 OS ... confirmo las 4 OS", 4),
    ("4 OS y luego 5 OS", None),
    ("Sin cantidad", None),
    ("POSTES de 4", None),
])
def test_contar_os(cuerpo, esperado):
    assert contar_os_solicitadas(cuerpo) == esperado


@pytest.mark.parametrize("valor,esperado", [
    ("55 5501 0002", "5555010002"),
    ("(55) 5501-0002", "5555010002"),
    ("+52 55 5501 0002", "5555010002"),
    ("+521 55 5501 0002", "5555010002"),
    ("5501", None),
    (None, None),
])
def test_telefono(valor, esperado):
    assert normalizar_telefono(valor) == esperado


@pytest.mark.parametrize("valor,iso", [
    ("02/03/2026", "2026-03-02T00:00:00"),
    ("02/03/2026 09:30", "2026-03-02T09:30:00"),
    ("2026-03-02 09:30:15", "2026-03-02T09:30:15"),
    ("2026-03-02T09:30:15", "2026-03-02T09:30:15"),
])
def test_fecha(valor, iso):
    assert parsear_fecha(valor).isoformat() == iso


def test_fecha_invalida():
    assert parsear_fecha("mañana") is None
