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


def test_conservar_serie_de_10_digitos():
    assert redact("Cancelar 5555550199 hoy") == "Cancelar [TELEFONO] hoy"
    assert redact("Cancelar 5555550199 hoy", conservar=["5555550199"]) == "Cancelar 5555550199 hoy"


def test_conservar_no_protege_otros_telefonos():
    salida = redact("5555550199 y llamar al 5555550101", conservar=["5555550199"])
    assert salida == "5555550199 y llamar al [TELEFONO]"


def test_conservar_solo_token_exacto_y_en_firma():
    salida = redact("Baja\nSaludos\nJuan Pérez\n5555550199", conservar=("5555550199",))
    assert "Juan" not in salida
    assert redact("tel 55555501990", conservar=["5555550199"]) == "tel 55555501990"
    assert redact("tel 5555550101", conservar=["5555550199"]) == "tel [TELEFONO]"
    assert redact("x", conservar=[]) == "x"


def test_conservar_es_idempotente():
    t = "Serie 5555550199 Tel 5555550101 a@example.com"
    una = redact(t, conservar=["5555550199"])
    assert una == "Serie 5555550199 Tel [TELEFONO] [CORREO]"
    assert redact(una, conservar=["5555550199"]) == una


# ======================================================================
# redact v2 (F1-F9). Todo inventado: nombres de fantasía, example.com, 555-01xx.
# ======================================================================

# ------------------------------------------------ F1 cabeceras citadas
@pytest.mark.parametrize("entrada, esperado", [
    ('De: "perez lopez, juan" <jp@example.com>\nAsunto: Baja',
     "De: [ID] <[CORREO]>\nAsunto: Baja"),
    ('De: "perez lopez, juan"\nEnviado: lunes', "De: [ID]\nEnviado: lunes"),
    ('Para: "garcia, ana"\nCC: "ruiz mora, luis"', "Para: [ID]\nCC: [ID]"),
    ("De: perez lopez, juan <jp@example.com>", "De: [ID] <[CORREO]>"),
    ("De:\nJuan Pérez\nEnviado: lunes 4 de mayo\nAsunto: Baja",
     "De:\n[ID]\nEnviado: lunes 4 de mayo\nAsunto: Baja"),
    ("Para:\nana ruiz; luis mora\nAsunto: x", "Para:\n[ID]; [ID]\nAsunto: x"),
    ("De: JUAN PEREZ LOPEZ\nEnviado: lunes", "De: [ID]\nEnviado: lunes"),
    ("Cc: Pérez López, Juan; Ruiz Mora, Ana\nAsunto: x", "Cc: [ID]; [ID]\nAsunto: x"),
    ("De: Juan Pérez <a@example.com>, Ana Ruiz <b@example.com>",
     "De: [ID] <[CORREO]>, [ID] <[CORREO]>"),
    ("> De: Juan Pérez\n> Enviado: lunes", "> De: [ID]\n> Enviado: lunes"),
])
def test_f1_cabeceras(entrada, esperado):
    assert redact(entrada) == esperado


def test_f1_cabecera_a_mitad_de_linea():
    salida = redact("Gracias. De: Juan Pérez Enviado: lunes 4 de mayo Para: ana ruiz; Luis Mora "
                    "Asunto: Baja de cooler")
    assert salida == ("Gracias. De: [ID] Enviado: lunes 4 de mayo Para: [ID]; [ID] "
                      "Asunto: Baja de cooler")


def test_f1_una_sola_etiqueta_a_mitad_de_linea_no_se_toca():
    texto = "El equipo es de: Tienda Centro para: retiro"
    assert redact(texto) == texto


# --------------------------------------------- F2 mailto / escribió
@pytest.mark.parametrize("entrada, esperado", [
    ("Juan Pérez [mailto:jperez@example.com]", "[ID] [mailto:[CORREO]]"),
    ("Pérez López, Juan [mailto:j@example.com]", "[ID] [mailto:[CORREO]]"),
    ("De: perez lopez, juan [mailto:j@example.com]\nEnviado: x", "De: [ID] [mailto:[CORREO]]\nEnviado: x"),
    ("Para: Juan Pérez; Ana Ruiz", "Para: [ID]; [ID]"),
    ("El lun, 4 may 2026, Juan Pérez escribió:", "El lun, 4 may 2026, [ID] escribió:"),
    ("El 4 may 2026 a las 10:30, Juan Pérez <j@example.com> escribió:",
     "El 4 may 2026 a las 10:30, [ID] <[CORREO]> escribió:"),
    ("El lun, 4 may 2026, juan perez escribió:", "El lun, 4 may 2026, [ID] escribió:"),
    ("On Mon, May 4, 2026 at 10:30, Mary Smith <m@example.com> wrote:",
     "On Mon, May 4, 2026 at 10:30, [ID] <[CORREO]> wrote:"),
    ("Juan Pérez escribió:", "[ID] escribió:"),
])
def test_f2_mailto_y_escribio(entrada, esperado):
    assert redact(entrada) == esperado


@pytest.mark.parametrize("texto", [
    "El lun, 2 jun escribió:",
    "El lun 4 de mayo de 2026 a las 10:30 escribió:",
    "El mar, 3 jun escribió:\n> Serie SF-1001",
])
def test_f2_escribio_solo_con_fecha_no_se_toca(texto):
    assert redact(texto) == texto


# --------------------------------------------- F3 correos con espacios
@pytest.mark.parametrize("entrada", [
    "juan. perez@ example. com",
    "juan.perez@ example.com",
    "juan. perez@example.com",
    "ana. lopez@ mail. example. com. mx",
    "ana.lopez @example.com",
    "ana.lopez@ example. com",
])
def test_f3_correo_con_espacios(entrada):
    assert redact(f"Correo: {entrada} fin") == "Correo: [CORREO] fin"


def test_f3_no_se_come_la_oracion_vecina():
    assert redact("Atte. ana@example.com") == "Atte. [CORREO]"
    assert redact("Escribe a a@example.com. Gracias") == "Escribe a [CORREO]. Gracias"
    assert redact("Cancelar el equipo. Escribe a a@example.com") == "Cancelar el equipo. Escribe a [CORREO]"


# ------------------------------------------------- F4 campos etiquetados
@pytest.mark.parametrize("entrada, esperado", [
    ("Nombre de quien reporta: Juan Pérez", "Nombre de quien reporta: [ID]"),
    ("Nombre de quien reporta: juan perez", "Nombre de quien reporta: [ID]"),
    ("Representante Propietario: MARIA LOPEZ RUIZ", "Representante Propietario: [ID]"),
    ("Contacto: Luis Mora Tel 5555550101", "Contacto: [ID] Tel [TELEFONO]"),
    ("Contacto: Luis Mora / 5555550101", "Contacto: [ID] / [TELEFONO]"),
    ("Responsable: pedro gomez", "Responsable: [ID]"),
    ("Solicitante: Ana Ruiz | Folio: 12345678", "Solicitante: [ID] | Folio: 12345678"),
    ("- Nombre del contacto: Rosa Díaz", "- Nombre del contacto: [ID]"),
    ("Nombre completo: Rosa Díaz Soto", "Nombre completo: [ID]"),
    ("Nombre: Itzel Quiroz", "Nombre: [ID]"),
    ("Contacto:\nItzel Quiroz\nFolio: 12345678", "Contacto:\n[ID]\nFolio: 12345678"),
    ("Dirección de Envío de Garantía: Calle Hidalgo 12, Col. Centro, CP 06000",
     "Dirección de Envío de Garantía: [DIRECCION]"),
    ("Dirección de envío: Av. Reforma 100, Col. Juárez | Folio: 12345678",
     "Dirección de envío: [DIRECCION] | Folio: 12345678"),
    ("Dirección fiscal: Calle Sur 3, Col. Norte", "Dirección fiscal: [DIRECCION]"),
    ("Dirección de entrega:\nCalle Sur 3, Col. Norte", "Dirección de entrega:\n[DIRECCION]"),
    ("El cooler está ubicada en Av. Reforma 100, Col. Juárez. Favor de retirar.",
     "El cooler está ubicada en [DIRECCION]. Favor de retirar."),
    ("Equipo ubicado en Calle Hidalgo 12 Col. Centro CP 06000", "Equipo ubicado en [DIRECCION]"),
])
def test_f4_campos_etiquetados(entrada, esperado):
    assert redact(entrada) == esperado


@pytest.mark.parametrize("texto", [
    "Cliente: OXXO",
    "Nombre de la tienda: OXXO La Esperanza",
    "Nombre del Cliente: OXXO",
    "Nombre del Cliente: Jumex S.A. de C.V.",
    "Nombre: KOF",
    "Tipo de servicio: INSTALACIÓN",
    "Atención: Mantenimiento correctivo",
    "Solicita: revisión del cooler",
    "Reporta: falla en el compresor",
    "Contacto: tienda",
    "Responsable: mantenimiento",
    "Contacto: pendiente",
    "Dirección: Calle Hidalgo 12, Col. Centro, C.P. 06000",
    "Dirección del PDV: Calle Sur 3",
    "Domicilio: Av Norte 4",
    "El cooler está ubicado en la tienda OXXO Centro",
    "Ubicado en el pasillo 3",
])
def test_f4_no_se_redacta(texto):
    assert redact(texto) == texto


@pytest.mark.parametrize("texto", [
    "Atención: El dominio <empresa>.com.mx va a expirar",
    "Atención: El dominio empresa.com.mx va a expirar. Favor de renovar",
    "Atención: El Dominio Empresa.com.mx va a expirar",
    "Atención: El Dominio Empresa va a expirar",
    "ATENCIÓN: El dominio OXXO.com.mx va a vencer",
])
def test_falso_positivo_atencion_dominio(texto):
    assert redact(texto) == texto
    assert "[ID]" not in redact(texto)


def test_f4_atencion_con_nombre_si_se_redacta():
    assert redact("Atención: Juan Pérez, favor de revisar") == "Atención: [ID], favor de revisar"
    assert redact("Atención: María del Carmen López") == "Atención: [ID]"


# ------------------------------------------------------- F5 tablas
def test_f5_tabla_con_barras_clave_valor():
    entrada = (
        "| Nombre del Cliente | Juan Pérez |\n"
        "| Teléfono | 5555550101 |\n"
        "| Correo | j@example.com |\n"
        "| Calle | Hidalgo 12 |\n"
        "| Colonia | Centro |\n"
        "| CP | 06000 |\n"
        "| Folio | 12345678 |\n"
        "| Tienda | OXXO Centro |\n"
    )
    esperado = (
        "| Nombre del Cliente | [ID] |\n"
        "| Teléfono | [TELEFONO] |\n"
        "| Correo | [CORREO] |\n"
        "| Calle | [DIRECCION] |\n"
        "| Colonia | [DIRECCION] |\n"
        "| CP | [DIRECCION] |\n"
        "| Folio | 12345678 |\n"
        "| Tienda | OXXO Centro |\n"
    )
    assert redact(entrada) == esperado


def test_f5_tabla_con_barras_encabezado_y_filas():
    entrada = (
        "| Nombre | Teléfono | Calle | Folio | Serie |\n"
        "|---|---|---|---|---|\n"
        "| Juan Pérez | 5555550101 | Hidalgo 12 | 12345678 | E64190100186 |\n"
        "| ana ruiz | 5555550102 | Sur 3 | 12345679 | E64190100187 |\n"
    )
    esperado = (
        "| Nombre | Teléfono | Calle | Folio | Serie |\n"
        "|---|---|---|---|---|\n"
        "| [ID] | [TELEFONO] | [DIRECCION] | 12345678 | E64190100186 |\n"
        "| [ID] | [TELEFONO] | [DIRECCION] | 12345679 | E64190100187 |\n"
    )
    assert redact(entrada) == esperado


def test_f5_tabla_aplanada_n_encabezados_n_valores():
    entrada = (
        "Nombre del Cliente\nTeléfono\nCorreo\nCalle\nFolio\n"
        "Juan Pérez\n5555550101\nj@example.com\nHidalgo 12\n12345678\n"
    )
    esperado = (
        "Nombre del Cliente\nTeléfono\nCorreo\nCalle\nFolio\n"
        "[ID]\n[TELEFONO]\n[CORREO]\n[DIRECCION]\n12345678\n"
    )
    assert redact(entrada) == esperado


def test_f5_tabla_aplanada_dos_columnas_y_texto_despues():
    entrada = "Contacto\nFolio\nitzel quiroz\n12345678\n\nSolicito retiro del cooler FVC14-E1"
    esperado = "Contacto\nFolio\n[ID]\n12345678\n\nSolicito retiro del cooler FVC14-E1"
    assert redact(entrada) == esperado


def test_f5_tabla_con_tabuladores():
    entrada = "Nombre\tTeléfono\tFolio\nJuan Pérez\t5555550101\t12345678"
    assert redact(entrada) == "Nombre\tTeléfono\tFolio\n[ID]\t[TELEFONO]\t12345678"


def test_f5_tabla_de_series_no_se_toca():
    texto = (
        "| Folio | Serie | Modelo | Tipo de servicio |\n|---|---|---|---|\n"
        "| 12345678 | E64190100186 | FVC14-E1 | INSTALACIÓN |\n"
        "| 12345679 | 720231200195 | CFX-14 | RETIRO |\n"
    )
    assert redact(texto) == texto
    plano = "Folio\nSerie\nModelo\n12345678\nE64190100186\nFVC14-E1"
    assert redact(plano) == plano


def test_f5_nombre_de_cliente_cadena_no_se_redacta():
    entrada = "| Nombre del Cliente | OXXO |\n| Teléfono | 5555550101 |"
    assert redact(entrada) == "| Nombre del Cliente | OXXO |\n| Teléfono | [TELEFONO] |"


# ----------------------------------------------- F6 ubicaciones
@pytest.mark.parametrize("entrada, esperado", [
    ("19.4326, -99.1332", "[UBICACION]"),
    ("Coordenadas 19.4326,-99.1332 de la tienda", "Coordenadas [UBICACION] de la tienda"),
    ("26.06, -98.34", "[UBICACION]"),
    ("Latitud: 26.06", "Latitud: [UBICACION]"),
    ("Longitud: -98.34", "Longitud: [UBICACION]"),
    ("Latitud: 26.06 Longitud: -98.34", "Latitud: [UBICACION] Longitud: [UBICACION]"),
    ("lat 19.4326 lng -99.1332", "lat [UBICACION] lng [UBICACION]"),
    ("GPS: 19.4326, -99.1332", "GPS: [UBICACION]"),
    ("https://maps.google.com/?q=19.4326,-99.1332", "[UBICACION]"),
    ("https://www.google.com/maps/place/Tienda+Centro/@19.43,-99.13,17z", "[UBICACION]"),
    ("ver goo.gl/maps/abc123 por favor", "ver [UBICACION] por favor"),
    ("https://maps.app.goo.gl/xYz123", "[UBICACION]"),
    ("maps.google.com.mx/maps?q=x", "[UBICACION]"),
    ("19°25'57\"N 99°07'59\"W", "[UBICACION]"),
])
def test_f6_ubicaciones(entrada, esperado):
    assert redact(entrada) == esperado


@pytest.mark.parametrize("texto", [
    "Medidas 1.5, 2.5 metros",
    "Voltaje 110.5, 220.5",
    "Precio unitario 12.50",
    "Versión 2.3.1",
    "Folio 12345678 serie E64190100186",
    "Latitud del mapa",
    "lat 5 piezas",
])
def test_f6_no_se_redacta(texto):
    assert redact(texto) == texto


# --------------------------------------------------- F7 firmas sin despedida
@pytest.mark.parametrize("despedida", [
    "¡Quedo pendiente, saludos!", "¡SALUDOS!", "Quedo pendiente", "¡Saludos!", "Quedo pendiente de sus comentarios",
    "Estoy al pendiente", "Gracias y saludos", "Saludos, gracias", "Un abrazo",
])
def test_f7_despedidas_nuevas(despedida):
    salida = redact(f"Adjunto el formato.\n{despedida}\nLuis Mora Vega\nCoordinador\nTel 5555550101")
    assert salida.endswith("\n[FIRMA]")
    assert "Luis" not in salida and "Coordinador" not in salida and "5555" not in salida
    assert salida.startswith("Adjunto el formato.\n")


def test_f7_despedida_con_nombre_en_minusculas():
    assert redact("Atte. juan perez") == "Atte. [ID]"
    assert redact("Saludos, ana ruiz") == "Saludos, [ID]"


@pytest.mark.parametrize("texto", [
    "Saludos desde la tienda, solicito baja",
    "Gracias por avisar",
    "Saludos y buen día",
    "Gracias, quedo atento",
])
def test_f7_despedida_con_prosa_no_se_destruye(texto):
    assert redact(texto) == texto


def test_f7_bloque_con_nombre_en_mayusculas_cargo_y_telefono():
    entrada = (
        "Se solicita revisión.\n"
        "JUAN PEREZ LOPEZ\n"
        "Gerente de Operaciones\n"
        "C: 5555550101\n"
        "T: 5555550102 ext 3\n"
        "j@example.com\n"
        "\n"
        "Retiro cooler FVC14-E1 serie E64190100186\n"
    )
    esperado = (
        "Se solicita revisión.\n"
        "[FIRMA]\n"
        "\n"
        "Retiro cooler FVC14-E1 serie E64190100186\n"
    )
    assert redact(entrada) == esperado


def test_f7_bloque_con_nombre_normal_y_cel():
    entrada = "Quedamos.\nAna Ruiz Soto\nCoordinadora de Zona\nCel. 5555550101\n"
    assert redact(entrada) == "Quedamos.\n[FIRMA]\n"


def test_f7_bloque_citado():
    entrada = "> JUAN PEREZ LOPEZ\n> Gerente\n> C: 5555550101\n> Retiro de cooler FVC14-E1"
    salida = redact(entrada)
    assert "JUAN" not in salida and "Gerente" not in salida
    assert "Retiro de cooler FVC14-E1" in salida


@pytest.mark.parametrize("texto", [
    "NO ENFRIA\nCONDENSACION\nTel: 5555550101",
    "COBERTURA\nEQUIPO ADICIONAL\nCel 5555550101",
    "CAMBIO DE EQUIPO\nINSTALACIÓN\nT: 5555550101",
])
def test_f7_tipos_de_servicio_no_son_firma(texto):
    salida = redact(texto)
    for palabra in ("NO ENFRIA", "CONDENSACION", "COBERTURA", "EQUIPO ADICIONAL", "CAMBIO DE EQUIPO",
                    "INSTALACIÓN"):
        if palabra in texto:
            assert palabra in salida


# -------------------------------------------------------- F8 saludos
@pytest.mark.parametrize("entrada, esperado", [
    ("Buen día Juan,\nsolicito baja", "Buen día [ID],\nsolicito baja"),
    ("Buenos días Juan Pérez:", "Buenos días [ID]:"),
    ("Buenas tardes María del Carmen López Ruiz,", "Buenas tardes [ID],"),
    ("Juan buenos días\nsolicito baja", "[ID] buenos días\nsolicito baja"),
    ("Juan Pérez buenas tardes", "[ID] buenas tardes"),
    ("Estimada Ana:\nsolicito baja", "Estimada [ID]:\nsolicito baja"),
    ("Estimado Sr. Pérez:", "Estimado Sr. [ID]:"),
    ("Hola Pedro López, gracias", "Hola [ID], gracias"),
    ("Hola, buen día Luis,", "Hola, buen día [ID],"),
    ("Hola luis!", "Hola [ID]!"),
    ("@Juan Pérez revisa por favor", "@[ID] revisa por favor"),
    ("@María del Carmen López, ayuda", "@[ID], ayuda"),
    ("@juan puedes revisar", "@[ID] puedes revisar"),
    ("> Buen día Juan,\n> solicito baja", "> Buen día [ID],\n> solicito baja"),
])
def test_f8_saludos(entrada, esperado):
    assert redact(entrada) == esperado


@pytest.mark.parametrize("texto", [
    "Buen día equipo,",
    "Buen día a todos,",
    "Buen día, solicito la baja del cooler",
    "Buen día, tienda Sucursal Norte necesita servicio",
    "Buen día, favor de cancelar el cambio",
    "Hola, buen día",
    "Hola KOF,",
    "Hola OXXO:",
    "Hola Soporte,",
    "Estimados Señores:",
    "Estimado cliente:",
    "Estimado equipo de soporte,",
    "Buenos días compañeros",
    "Buen día Mesa de Ayuda,",
    "Gracias buenos días",
    "Equipo buenos días",
    "Solicito baja buenos días",
    "Hola, necesito retirar el cooler FVC14-E1",
    "Buen día Jumex,",
    "@todos favor de revisar",
    "Escribe a soporte@example.com",
])
def test_f8_no_se_redacta(texto):
    salida = redact(texto)
    assert "[ID]" not in salida, salida
    assert salida == texto.replace("soporte@example.com", "[CORREO]")


# --------------------------------------------------------- F9 montos
@pytest.mark.parametrize("entrada, esperado", [
    ("$ 5,000", "[MONTO]"),
    ("$5,000", "[MONTO]"),
    ("$5,000.00 MXN", "[MONTO]"),
    ("$ 5,000.00 M.N.", "[MONTO]"),
    ("Costo $1,234.50 USD aprox", "Costo [MONTO] aprox"),
    ("$500", "[MONTO]"),
    ("$ 12,345,678.90", "[MONTO]"),
    ("MXN $5,000", "[MONTO]"),
    ("cuesta 5,000 pesos", "cuesta [MONTO]"),
    ("Total: $1 500 MXN y $200", "Total: [MONTO] y [MONTO]"),
])
def test_f9_montos(entrada, esperado):
    assert redact(entrada) == esperado


@pytest.mark.parametrize("texto", [
    "Folio 12345678", "ticket 12345678", "serie E64190100186", "IMB-070526_4960", "REP-080526_5926",
    "2 equipos y 3 coolers", "5 pesos de diferencia de peso",
])
def test_f9_no_se_redacta(texto):
    assert "[MONTO]" not in redact(texto) or "pesos" in texto


# --------------------------- identificadores y servicios nunca se tocan
def test_ids_series_y_servicios_sobreviven():
    texto = (
        "IMB-070526_4960 REP-080526_5926 ticket 12345678 folio 87654321\n"
        "Serie E64190100186 modelo FVC14-E1 y CFX-14\n"
        "Tipo de servicio: INSTALACIÓN, RETIRO, CAMBIO DE EQUIPO, COBERTURA, EQUIPO ADICIONAL\n"
        "Falla: NO ENFRIA / CONDENSACION\n"
        "Cliente: OXXO / Jumex / KOF\n"
        "PDV Tienda La Esperanza, Calle Hidalgo 12, Col. Centro, C.P. 06000\n"
    )
    assert redact(texto) == texto


def test_nombre_de_tienda_con_nombre_de_persona():
    """Criterio: el nombre de tienda que contiene un nombre de persona se conserva si va
    como dato de punto de venta (sin etiqueta de persona ni saludo/firma a su alrededor)."""
    texto = "PDV Abarrotes Juan Pérez, Calle Sur 3\nTienda Doña María #123\nSucursal Pedro López"
    assert redact(texto) == texto
    assert redact("Contacto: Abarrotes Juan Pérez") == "Contacto: [ID]"  # etiqueta de persona: se redacta


# ---------------------------------------- propiedad: ningún nombre sobrevive
NOMBRES_INVENTADOS = [
    "Juan Pérez", "María del Carmen López Ruiz", "Ana Ruiz", "Luis Mora Vega", "Rosa Díaz",
    "Pedro Gómez Lara", "Itzel Quiroz", "Ximena Valdivia", "Hortensia Bermúdez Soto", "Gaspar Olvera",
]


def _formas(n):
    w = n.split()
    if len(w) > 3:
        ap, no = " ".join(w[-2:]), " ".join(w[:-2])
    elif len(w) > 1:
        ap, no = " ".join(w[1:]), w[0]
    else:
        ap = no = w[0]
    return {"n": n, "lower": n.lower(), "upper": n.upper(),
            "coma": f"{ap}, {no}", "comalow": f"{ap}, {no}".lower()}


TODAS = {"n", "lower", "upper", "coma", "comalow"}
PLANTILLAS = {
    # cabeceras
    "cab_correo": ("De: {v} <x@example.com>\nPara: Z\nAsunto: Baja", TODAS),
    "cab_comillas": ('De: "{v}" <x@example.com>\nAsunto: Baja', TODAS),
    "cab_comillas_sin_correo": ('De: "{v}"\nEnviado: lunes\nAsunto: x', TODAS),
    "cab_nombre_en_la_linea_siguiente": ("De:\n{v}\nEnviado: lunes\nAsunto: x", TODAS),
    "cab_para": ("Para: {v}; Ana Ruiz\nAsunto: x", TODAS),
    "cab_cc": ("Cc: Z <z@example.com>; {v}\nAsunto: x", TODAS),
    "cab_mitad_de_linea": ("Hola equipo. De: {v} Enviado: lunes 4 de mayo Para: x@example.com Asunto: Baja", TODAS),
    "cab_ingles": ("From: {v}\nSent: Monday\nSubject: x", {"n", "upper"}),
    "mailto": ("{v} [mailto:x@example.com]", {"n", "upper", "coma"}),
    "mailto_en_cabecera": ("De: {v} [mailto:x@example.com]\nEnviado: x", TODAS),
    "escribio": ("El lun, 4 may 2026, {v} escribió:\n> hola", {"n", "lower", "upper"}),
    "escribio_con_correo": ("El 4 may 2026 a las 10:30, {v} <x@example.com> escribió:", {"n", "lower", "upper"}),
    # saludos
    "saludo_buen_dia": ("Buen día {v},\nsolicito baja", {"n", "lower"}),
    "saludo_nombre_primero": ("{v} buenos días\nsolicito baja", {"n", "lower"}),
    "saludo_mencion": ("@{v} revisa por favor", {"n"}),
    "saludo_estimada": ("Estimada {v}:\nsolicito baja", {"n"}),
    "saludo_hola": ("Hola {v}, buen día", {"n"}),
    # firmas
    "firma_saludos": ("Gracias.\nSaludos,\n{v}\nGerente de tienda", {"n", "lower", "upper"}),
    "firma_quedo_pendiente": ("¡Quedo pendiente, saludos!\n{v}\nCoordinador", {"n", "lower", "upper"}),
    "firma_gritada": ("¡SALUDOS!\n{v}\nCoordinador\nC: 5555550101", {"n", "upper"}),
    "firma_sin_despedida": ("Revisen el equipo.\n{v}\nGerente de Operaciones\nC: 5555550101\nT: 5555550102\n\nRetiro FVC14-E1", {"n", "upper"}),
    "firma_atte": ("Atte. {v}", {"n", "lower", "upper"}),
    # campos
    "campo_quien_reporta": ("Nombre de quien reporta: {v}", {"n", "lower", "upper", "coma"}),
    "campo_representante": ("Representante Propietario: {v}", {"n", "lower", "upper", "coma"}),
    "campo_contacto": ("Contacto: {v}", {"n", "lower", "upper"}),
    "campo_responsable_con_tel": ("Responsable: {v} Tel 5555550101", {"n", "lower", "upper"}),
    "campo_valor_en_la_linea_siguiente": ("Nombre de quien reporta:\n{v}\nTeléfono: 5555550101", {"n", "lower", "upper"}),
    # tablas
    "tabla_clave_valor": ("| Nombre del Cliente | {v} |\n| Folio | 12345678 |", TODAS),
    "tabla_encabezado": ("| Contacto | Folio |\n|---|---|\n| {v} | 12345678 |", TODAS),
    "tabla_aplanada": ("Nombre del Cliente\nTeléfono\nFolio\n{v}\n5555550101\n12345678", TODAS),
    "tabla_aplanada_2": ("Contacto\nFolio\n{v}\n12345678", {"n", "lower", "upper"}),
}


@pytest.mark.parametrize("nombre", NOMBRES_INVENTADOS)
def test_propiedad_ninguna_palabra_del_nombre_sobrevive(nombre):
    formas = _formas(nombre)
    palabras = [w for w in re.findall(r"\w+", nombre) if w.lower() not in ("del", "de", "la")]
    fallos = []
    for clave, (plantilla, permitidas) in PLANTILLAS.items():
        for forma in sorted(permitidas):
            texto = plantilla.replace("{v}", formas[forma])
            salida = redact(texto)
            fugas = [w for w in palabras if re.search(rf"(?i)\b{re.escape(w)}\b", salida)]
            if fugas or redact(salida) != salida:
                fallos.append((clave, forma, fugas, salida))
    assert not fallos, fallos


def test_propiedad_el_contenido_del_clasificador_sobrevive():
    """Con cualquier nombre en cabecera/firma/saludo, folio, serie, modelo y acción quedan."""
    cuerpo = "Solicito RETIRO folio 12345678 serie E64190100186 modelo FVC14-E1 tienda OXXO Centro"
    for nombre in NOMBRES_INVENTADOS:
        texto = (f"De: {nombre} <x@example.com>\nEnviado: lunes\nAsunto: Baja\n\n"
                 f"Buen día {nombre.split()[0]},\n{cuerpo}\n\nSaludos,\n{nombre}\nGerente\nC: 5555550101")
        salida = redact(texto)
        assert cuerpo in salida, salida
        assert nombre.split()[0] not in salida.replace("Gerente", "")


# --------------------------- idempotencia y fugas con piezas v2 al azar
def test_idempotencia_con_piezas_v2_al_azar():
    import random
    rnd = random.Random(11)
    piezas = [
        'De: "perez lopez, juan"', "De:\n", "Juan Pérez\n", "Enviado: lunes", "Para: Ana Ruiz; Luis Mora",
        "Juan Pérez [mailto:j@example.com]", "El lun, 4 may 2026, Juan Pérez escribió:", "juan. perez@ example. com",
        "Nombre de quien reporta: Ana Ruiz", "Contacto:\n", "Dirección de Envío de Garantía: Calle Sur 3 Col. Norte",
        "ubicada en Av. Reforma 100.", "| Nombre | Teléfono |\n|---|---|\n| Ana Ruiz | 5555550101 |",
        "Nombre\nTeléfono\nFolio\nAna Ruiz\n5555550101\n12345678", "19.4326, -99.1332", "Latitud: 26.06",
        "https://maps.google.com/?q=1,2", "¡SALUDOS!", "¡Quedo pendiente, saludos!", "JUAN PEREZ LOPEZ\nGerente\nC: 5555550101",
        "Buen día Juan,", "Juan buenos días", "@Juan Pérez", "Estimada Ana:", "$ 5,000", "$5,000.00 MXN",
        "Atención: El dominio x.com.mx va a expirar", "Gracias,", "Atte.", "Saludos", "\n", "\n\n", "> ",
        "Folio 12345678", "IMB-070526_4960", "[ID]", "[FIRMA]", "[UBICACION]", "[MONTO]", "[DIRECCION]",
        "Aviso de privacidad", "--", "Tel:", "5555550101", "a@example.com",
    ]
    for _ in range(3000):
        texto = "".join(rnd.choice(piezas) + rnd.choice([" ", "\n"]) for _ in range(rnd.randint(1, 12)))
        salida = redact(texto)
        assert redact(salida) == salida, repr(texto)
        assert not EMAIL_RE.search(salida), repr(texto)


@pytest.mark.parametrize("texto", [
    "De: Juan Pérez [mailto:j@example.com]\nPara: Ana Ruiz; Luis Mora\nContacto: Itzel Quiroz\n"
    "Nombre\nTeléfono\nJuan Pérez\n5555550101\nBuen día Juan,\n¡SALUDOS!\nJUAN PEREZ\nC: 5555550101",
    "| Nombre | Teléfono |\n|---|---|\n| Ana Ruiz | 5555550101 |\nLatitud: 26.06 $ 5,000 ubicada en Calle Sur 3",
])
def test_idempotencia_v2_corpus(texto):
    una = redact(texto)
    assert redact(una) == una


def test_conservar_sigue_funcionando_con_v2():
    t = "Contacto: Ana Ruiz\nSerie 5555550199 Tel 5555550101 $ 5,000"
    assert redact(t, conservar=["5555550199"]) == "Contacto: [ID]\nSerie 5555550199 Tel [TELEFONO] [MONTO]"
