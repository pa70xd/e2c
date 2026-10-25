"""Pruebas de classifier.redact. Todo sintético: nombres, teléfonos y correos
inventados, dominio example.com, teléfonos 555-01xx."""
import re

import pytest

from classifier.redact import redact

# ------------------------------------------------------------------ correos

@pytest.mark.parametrize("entrada", [
    "juan.perez@example.com",
    "Escribe a ventas+norte@mail.example.com por favor",
    "JUAN_PEREZ@EXAMPLE.COM",
    "mailto:contacto@example.com",
    "<ana.lopez@example.com>",
    "ana.lopez [at] example [dot] com",
    "ana.lopez(arroba)example.com",
    "ana&#64;example.com",
    "ana＠example.com",
])
def test_correos(entrada):
    salida = redact(entrada)
    assert "example" not in salida.lower()
    assert "[CORREO]" in salida


def test_correo_conserva_texto_alrededor():
    assert redact("Hola, escribe a a@example.com para baja") == "Hola, escribe a [CORREO] para baja"


# ---------------------------------------------------------------- teléfonos

@pytest.mark.parametrize("entrada", [
    "5555550101",
    "55 5555 0101",
    "555 555 0101",
    "55-5555-0101",
    "555-555-0101",
    "55.5555.0101",
    "(55) 5555 0101",
    "(555) 555-0101",
    "+52 55 5555 0101",
    "+52 (55) 5555-0101",
    "+525555550101",
    "+52 1 55 5555 0101",
    "52 55 5555 0101",
    "044 555 555 0101",
    "01 55 5555 0101",
    "55 5555 0101 ext. 123",
    "(55) 5555-0101 Ext 45",
    "5555550101 x123",
    "55 5555 0101",
    "５５５５５５０１０１",
])
def test_telefonos(entrada):
    assert redact(f"Tel: {entrada}") == "Tel: [TELEFONO]"


def test_telefono_corto_con_etiqueta():
    assert redact("Tel. 5555-0101") == "Tel. [TELEFONO]"
    assert redact("Cel 555 0101") == "Cel [TELEFONO]"


def test_telefono_en_oracion():
    assert redact("Llamar al 55 5555 0101 con el encargado.") == "Llamar al [TELEFONO] con el encargado."


def test_telefono_prevalece_sobre_serie_si_la_etiqueta_es_de_tel():
    assert redact("serie ABC123456 tel 5555550101") == "serie ABC123456 tel [TELEFONO]"
    assert redact("Folio 5555550102, WhatsApp 5555550101") == "Folio 5555550102, WhatsApp [TELEFONO]"


# ----------------------------------------------------- firmas, nombres, RFC

def test_firma_bloque_tras_despedida():
    entrada = (
        "Favor de dar de baja el equipo ABC123456.\n"
        "\n"
        "Saludos,\n"
        "Juan Pérez García\n"
        "Gerente de Compras\n"
        "Tel 55 5555 0101\n"
        "juan.perez@example.com\n"
    )
    esperado = (
        "Favor de dar de baja el equipo ABC123456.\n"
        "\n"
        "Saludos,\n"
        "[FIRMA]\n"
    )
    assert redact(entrada) == esperado


@pytest.mark.parametrize("despedida", [
    "Saludos", "Saludos cordiales,", "Atentamente", "Atte.", "Cordialmente,", "Slds",
    "Quedo atento", "Quedo atenta a sus comentarios", "Gracias", "Muchas gracias!",
    "Un saludo", "Best regards,", "Gracias por su atención",
])
def test_despedidas_abren_bloque(despedida):
    salida = redact(f"Adjunto el formato.\n{despedida}\nLuis Mora Vega\nCoordinador")
    assert salida.endswith("\n[FIRMA]")
    assert "Luis" not in salida and "Coordinador" not in salida
    assert salida.startswith("Adjunto el formato.\n")


def test_nombre_en_la_linea_de_despedida():
    assert redact("Atte. Ana López Ruiz") == "Atte. [ID]"
    assert redact("Saludos, Pedro Ruiz") == "Saludos, [ID]"


def test_despedida_con_oracion_no_es_firma():
    texto = "Gracias, adjunto la serie ABC123456 para baja\nPDV Tienda La Esperanza"
    assert redact(texto) == texto


def test_firma_no_se_come_el_contenido_del_clasificador():
    entrada = (
        "Gracias\n"
        "Rosa Díaz\n"
        "Retiro del cooler FVC14-E1 serie ABC123456\n"
        "Av. Reforma 100, Col. Centro\n"
    )
    esperado = (
        "Gracias\n"
        "[FIRMA]\n"
        "Retiro del cooler FVC14-E1 serie ABC123456\n"
        "Av. Reforma 100, Col. Centro\n"
    )
    assert redact(entrada) == esperado


def test_delimitador_de_firma():
    assert redact("Baja del equipo.\n--\nMaría Soto\nTel 5555550101") == "Baja del equipo.\n--\n[FIRMA]"


def test_enviado_desde_mi_telefono():
    assert redact("Cancelar folio 1234\nEnviado desde mi iPhone") == "Cancelar folio 1234\n[FIRMA]"


@pytest.mark.parametrize("pie", [
    "Aviso de privacidad: sus datos serán tratados conforme a la ley.",
    "Este correo es confidencial y está dirigido solo a su destinatario.",
    "Este mensaje y sus anexos son confidenciales.",
    "AVISO LEGAL: la información contenida en este correo es privada.",
    "This email is confidential and may be privileged.",
])
def test_pie_legal(pie):
    salida = redact(f"Alta de equipo ABC123456\n\n{pie}\nSegunda línea del aviso con texto.")
    assert salida == "Alta de equipo ABC123456\n\n[FIRMA]"


@pytest.mark.parametrize("rfc", ["ABCD010101AB1", "ABC010101XY9", "ÑAB010101XY9"])
def test_rfc(rfc):
    assert redact(f"Factura a nombre de {rfc}.") == "Factura a nombre de [ID]."


def test_curp_y_rfc_etiquetados():
    assert redact("CURP: PEXJ900101HDFRRN09") == "CURP: [ID]"
    assert redact("rfc: abcd010101ab1") == "rfc: [ID]"


def test_nombre_antes_del_correo_y_cabeceras():
    entrada = (
        "De: Pedro Ruiz <pedro.ruiz@example.com>\n"
        "Para: Ana López; Luis Mora <luis@example.com>\n"
        "Cc: soporte@example.com\n"
        "Asunto: Baja de cooler\n"
    )
    esperado = (
        "De: [ID] <[CORREO]>\n"
        "Para: [ID]; [ID] <[CORREO]>\n"
        "Cc: [CORREO]\n"
        "Asunto: Baja de cooler\n"
    )
    assert redact(entrada) == esperado


def test_nombre_con_etiqueta_de_contacto():
    assert redact("Contacto: María Gómez\nResponsable: Luis Mora") == "Contacto: [ID]\nResponsable: [ID]"


# ---------------------------------------------------------- HTML a texto

def test_html_convertido_a_texto():
    entrada = (
        "Buen día&nbsp;equipo,\n"
        "Solicito RETIRO del cooler serie ABC123456&nbsp;(modelo FVC14-E1).\n"
        "Tienda La Esperanza, Calle Hidalgo 12, Col. Centro, C.P. 06000\n"
        "\n"
        "Atentamente\n"
        "Rosa Díaz | Ventas\n"
        "Tel: (55) 5555-0101 | rosa.diaz@example.com\n"
        "[Aviso de privacidad](https://example.com/aviso)\n"
    )
    salida = redact(entrada)
    for conserva in ("RETIRO", "ABC123456", "FVC14-E1", "Calle Hidalgo 12", "06000"):
        assert conserva in salida
    for fuga in ("Rosa", "5555", "example"):
        assert fuga not in salida
    assert salida.rstrip().endswith("[FIRMA]")


# --------------------------------------------------- falsos positivos

@pytest.mark.parametrize("texto", [
    "Serie ABC123456",
    "S/N: E64190100186",
    "Series: 720231200195 y 000002312062760347",
    "modelo FVC14-E1 E2C115BGN",
    "Modelo CFX-14, serie 000002312062760347",
    "Folio 2024-001234",
    "Folio: 202610250001",
    "Ticket REP-0012345",
    "Serie: 5555550101",
    "No. de serie 5555550101",
    "Activo 5215550101234",
    "Dar de alta cooler ABC123456 en Tienda La Esperanza",
    "Favor de cancelar el cambio de la baja del retiro",
    "Tipo de servicio: mantenimiento correctivo",
    "Calle Hidalgo 12, Col. Centro, C.P. 06000, Ciudad de México",
    "Av. Insurgentes Sur 1234, Col. Del Valle",
    "Fecha 25/10/2026 y 2026-10-25",
    "720231200195",
    "1234567890123",
    "ABC-5555550101",
])
def test_no_se_redacta(texto):
    assert redact(texto) == texto


def test_lista_de_series_bajo_encabezado():
    texto = "Series:\n5555550101\n5555550102"
    assert redact(texto) == texto


def test_rfc_no_confunde_series():
    for serie in ("ABC123456789", "ABCD123456XY1", "AB12345678"):
        assert redact(f"serie {serie}") == f"serie {serie}"


# --------------------------------------------------------------- hilos

def test_hilo_con_texto_citado():
    entrada = (
        "Confirmo la baja del equipo ABC123456.\n"
        "\n"
        "El lun, 5 ene 2026 a las 10:00, Pedro Ruiz <pedro@example.com> escribió:\n"
        "> Buen día, solicito retiro del cooler serie ABC123456\n"
        "> en Tienda La Esperanza, Calle Hidalgo 12.\n"
        "> Cel 55 5555 0101\n"
        ">\n"
        "> Saludos\n"
        "> Pedro Ruiz\n"
        "> Jefe de zona\n"
        "> pedro@example.com\n"
        ">\n"
        "> > Mensaje anterior de luis@example.com\n"
    )
    salida = redact(entrada)
    assert "Confirmo la baja del equipo ABC123456." in salida
    assert "[ID] <[CORREO]> escribió:" in salida
    assert "> Buen día, solicito retiro del cooler serie ABC123456" in salida
    assert "> en Tienda La Esperanza, Calle Hidalgo 12." in salida
    assert "> Saludos\n> [FIRMA]" in salida
    assert "Pedro" not in salida and "5555" not in salida and "example" not in salida


def test_hilo_outlook_de_enviado():
    entrada = (
        "Gracias\n"
        "Ana López\n"
        "\n"
        "De: Pedro Ruiz <pedro@example.com>\n"
        "Enviado: lunes, 5 de enero de 2026 10:00\n"
        "Para: Ana López <ana@example.com>\n"
        "Asunto: RE: Baja ABC123456\n"
        "\n"
        "Se solicita la baja.\n"
    )
    esperado = (
        "Gracias\n"
        "[FIRMA]\n"
        "\n"
        "De: [ID] <[CORREO]>\n"
        "Enviado: lunes, 5 de enero de 2026 10:00\n"
        "Para: [ID] <[CORREO]>\n"
        "Asunto: RE: Baja ABC123456\n"
        "\n"
        "Se solicita la baja.\n"
    )
    assert redact(entrada) == esperado


def test_firma_citada_no_cruza_a_otro_nivel():
    entrada = "> Atentamente\n> Pedro Ruiz\nRespuesta: sí, dar de baja ABC123456\n"
    assert redact(entrada) == "> Atentamente\n> [FIRMA]\nRespuesta: sí, dar de baja ABC123456\n"


def test_cabecera_en_ingles():
    salida = redact("From: Mary Smith <mary@example.com>\nSent: Monday\nTo: Tom Hill\nSubject: Baja")
    assert "Mary" not in salida and "Tom" not in salida and "Subject: Baja" in salida


# ------------------------------------------------- idempotencia y propiedad

CORPUS = [
    "Saludos,\nJuan Pérez\nTel 55 5555 0101\njuan@example.com",
    "Hola\n\nAtte. Ana López\nAviso de privacidad: texto\nmás texto",
    "El lun, 5 ene 2026, Pedro Ruiz <p@example.com> escribió:\n> Gracias\n> Pedro\n> 5555550101",
    "De: A B <a@example.com>\nPara: C D\nCc: e@example.com\nAsunto: x",
    "Serie: 5555550101 modelo FVC14-E1 ABC123456",
    "RFC ABCD010101AB1 CURP PEXJ900101HDFRRN09 tel +52 55 5555 0101 ext 12",
    "Gracias\n--\nEnviado desde mi iPhone\nAviso de privacidad",
    "Quedo atenta\n\nRosa Díaz\nVentas\n\nCalle Hidalgo 12\n",
    "Contacto: María Gómez\nTel. 5555-0101\nSaludos, Luis Mora\nCoordinador",
    "",
    "texto sin pii",
]


@pytest.mark.parametrize("texto", CORPUS)
def test_idempotencia(texto):
    una = redact(texto)
    assert redact(una) == una


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
TEL_RE = re.compile(r"(?<!\d)(?:\+?52)?[\s().-]*\d{2,3}[\s().-]*\d{3,4}[\s.-]*\d{4}(?!\d)")


@pytest.mark.parametrize("texto", CORPUS)
def test_ningun_correo_ni_telefono_sobrevive(texto):
    salida = redact(texto)
    assert not EMAIL_RE.search(salida)
    assert not [m for m in TEL_RE.finditer(salida)
                if len(re.sub(r"\D", "", m.group())) >= 10
                and not re.search(r"(?i)serie|s/n|folio", salida[: m.start()].split("\n")[-1])]


def test_propiedad_combinatoria():
    prefijos = ["", "Tel: ", "Cel. ", "Llamar al ", "WhatsApp ", "(", "Contacto - "]
    formatos = [
        "55{a}{b}", "55 {a} {b}", "(55) {a}-{b}", "+52 55 {a} {b}", "55-{a}-{b}",
        "55.{a}.{b}", "52 55 {a} {b}",
    ]
    nombres = ["Ana", "Luis Mora", "María del Carmen López"]
    dominios = ["example.com", "mail.example.com", "corp.example.com"]
    for i, pre in enumerate(prefijos):
        for j, fmt in enumerate(formatos):
            numero = fmt.format(a=str(5500 + i * 7 + j)[-4:].zfill(4)[:3] + "5", b=f"01{i}{j}"[:4])
            nombre = nombres[(i + j) % 3]
            dom = dominios[(i + j) % 3]
            texto = f"Buen día. {pre}{numero}\nSaludos\n{nombre}\n{nombre.split()[0].lower()}@{dom}"
            salida = redact(texto)
            assert not EMAIL_RE.search(salida), salida
            assert "5501" not in salida.replace("[TELEFONO]", ""), (texto, salida)
            assert nombre not in salida, salida
            assert redact(salida) == salida


def test_idempotencia_y_fugas_con_texto_aleatorio():
    import random
    rnd = random.Random(7)
    piezas = [
        "Saludos", "Gracias,", "Atte.", "Juan Pérez", "Tel:", "5555550101", "55 5555 0101",
        "a@example.com", "\n", "\n\n", "> ", "> > ", "De: Ana López <b@example.com>",
        "Aviso de privacidad", "ABC123456", "baja", "Serie", "Folio", "--", "El lun escribió:",
        "Enviado desde mi iPhone", "[FIRMA]", "[ID]", "(55)", "ext. 3", "+52", "Atentamente",
        "Contacto: Luis Mora\n", "ABCD010101AB1", "+52 55 5555 0101",
    ]
    for _ in range(3000):
        texto = "".join(rnd.choice(piezas) + rnd.choice([" ", "\n", ""])
                        for _ in range(rnd.randint(1, 14)))
        salida = redact(texto)
        assert redact(salida) == salida, repr(texto)
        assert not EMAIL_RE.search(salida), repr(texto)
