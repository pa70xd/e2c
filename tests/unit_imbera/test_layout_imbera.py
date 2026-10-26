"""Unidades del flujo común Imbera/Torrey: lector del layout, clasificación
por contenido, conciliación desde texto y fixtures sincronizados."""

import io

import pytest
from openpyxl import Workbook

from parsers.imbera_parse import conciliacion
from parsers.imbera_parse.clasificacion import clasificar, limpiar_asunto
from parsers.imbera_parse.layout import leer_layout
from tests.fixtures.imbera import build

FILA = ["MOD-V100", "SER-0001", "No enfría", "", "D-1", "C-1", "MONTERREY", "RUTA", "TRADICIONAL"]


def _xlsx(hojas):
    """hojas: [(titulo, estado, filas)]"""
    wb = Workbook()
    wb.remove(wb.active)
    for titulo, estado, filas in hojas:
        ws = wb.create_sheet(titulo)
        for fila in filas:
            ws.append(fila)
        ws.sheet_state = estado
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


# ---------------------------------------------------------------- lector

def test_fixtures_versionados_coinciden_con_el_script():
    assert build.check() == [], "Regenera con: python -m tests.fixtures.imbera.build"


def test_hojas_ocultas_de_catalogo_no_son_datos():
    contenido = _xlsx([
        ("RUTA", "visible", [build.HEADERS_A, FILA]),
        ("LinesByCategori", "hidden", [["Categoria", "Linea"], ["REFRIGERACION", "VERTICAL"]]),
        ("ModelsByLines", "veryHidden", [["Linea", "Modelo"], ["VERTICAL", "MOD-V100"]]),
    ])
    df = leer_layout(contenido, "excel_1")
    assert df["SERIE"].tolist() == ["SER-0001"]


def test_hoja_oculta_con_encabezado_de_datos_si_se_lee():
    contenido = _xlsx([
        ("RUTA", "visible", [build.HEADERS_A, FILA]),
        ("RUTA_2", "hidden", [build.HEADERS_A, ["MOD-H200", "SER-0002"] + FILA[2:]]),
    ])
    df = leer_layout(contenido, "excel_1")
    assert df["SERIE"].tolist() == ["SER-0001", "SER-0002"]


def test_solo_catalogos_no_es_layout():
    contenido = _xlsx([("Hoja1", "visible", [["Categoria", "Linea"], ["A", "B"]])])
    assert leer_layout(contenido, "excel_1") is None


def test_fila_basura_se_descarta():
    contenido = _xlsx([("RUTA", "visible", [build.HEADERS_A, FILA, build.FILA_BASURA_A])])
    assert len(leer_layout(contenido, "excel_1")) == 1


def test_variante_b_grupos_y_pii(tmp_path):
    ruta = tmp_path / "b.xlsx"
    build.layout_b(ruta, [build._fila_b(1, "TOR-V300", "SER-1", "No enfría", "RECIBE EJEMPLO")])
    df = leer_layout(ruta.read_bytes(), "excel_1")
    fila = df.iloc[0]
    assert (fila["MODELO"], fila["SERIE"], fila["NUM DISTRIBUIDOR"], fila["NUM CLIENTE"]) == (
        "TOR-V300", "SER-1", "D-3001", "C-4001",
    )
    assert (fila["CP"], fila["LATITUD"], fila["CONTACTO NOMBRE"]) == ("64000", "25.6701", "RECIBE EJEMPLO")
    assert fila["_FILA_EXCEL"] == "4"


# ---------------------------------------------------------- clasificación

@pytest.mark.parametrize("asunto, esperado", [
    (
        "SOLICITUD DE SERVICIO -- JUMEX MONTERREY -- INSTALACION -- IMB-261026_1",
        ("movimiento", "JUMEX", "MONTERREY", "IMB-261026_1", "INSTALACION"),
    ),
    (
        "RE: ORDEN DE SERVICIO PISA -- GUADALAJARA -- REP-251026_2",
        ("ruta", "PISA", "GUADALAJARA", "REP-251026_2", None),
    ),
    (
        "SOLICITUD DE GARANTIA OS98765 COMERCIAL EJEMPLO",
        ("garantia", "COMERCIAL EJEMPLO", None, None, None),
    ),
    (
        "SOLICITUD DE OS PARA DISTRIBUIDORA EJEMPLO PUEBLA",
        ("ruta", "DISTRIBUIDORA EJEMPLO PUEBLA", None, None, None),
    ),
    ("REPORTE VITRINA MOD-V100", ("ruta", None, None, None, None)),
])
def test_asuntos_conocidos(asunto, esperado):
    c = clasificar(asunto, "")
    assert (c.tipo, c.subcliente, c.plaza, c.folio, c.movimiento) == esperado


def test_subcliente_desde_el_cuerpo():
    c = clasificar("Reporte de equipo", "Equipo de Electrolit en sucursal centro")
    assert c.subcliente == "ELECTROLIT"


def test_variantes_de_ruta():
    assert clasificar("REPORTE VITRINA X", "Folio de la app: 778899").variante_ruta == "folio_app"
    assert clasificar("REPORTE VITRINA X", "").variante_ruta == "distribuidora"
    assert clasificar("Proyecto especial OXXO", "").variante_ruta == "proyecto_especial"


@pytest.mark.parametrize("adjuntos, buzones, cuerpo, senal", [
    (["factura 123.pdf"], [], "", "factura_pdf"),
    (["placa_equipo.jpg"], [], "", "foto_placa"),
    ([], [], "Llegó un equipo nuevo dañado", "equipo_nuevo_danado"),
    ([], ["garantias@cliente.example.com"], "", "buzon_garantias"),
])
def test_senales_de_garantia(adjuntos, buzones, cuerpo, senal):
    c = clasificar("Reporte", cuerpo, adjuntos, buzones)
    assert c.garantia and senal in c.senales_garantia


def test_sin_senales_no_es_garantia():
    c = clasificar("ORDEN DE SERVICIO JUMEX -- MTY -- REP-010126_1", "Equipo no enfría", ["foto.jpg"])
    assert not c.garantia


def test_seguimiento():
    assert clasificar("RE: Seguimiento reporte REP-201026_3", "").tipo == "seguimiento"


def test_limpiar_asunto():
    assert limpiar_asunto("RE: Fw: orden de servicio jumex--mty---REP-1") == "ORDEN DE SERVICIO JUMEX -- MTY -- REP-1"


# -------------------------------------------------- conciliación de texto

FILAS = [
    {"row_number": 1, "serie_fabricante": "SER-A", "serie_dnn_bnf": None, "status": "PENDING"},
    {"row_number": 2, "serie_fabricante": "SER-B", "serie_dnn_bnf": None, "status": "PENDING"},
    {"row_number": 3, "serie_fabricante": "SER-C", "serie_dnn_bnf": None, "status": "ACCEPTED"},
]


def test_extraer_os_varias():
    assert conciliacion.extraer_os("Comparto órdenes generadas: 403111, 403112 y 403113") == [
        "403111", "403112", "403113",
    ]


def test_texto_por_serie():
    r = conciliacion.conciliar_texto("SER-B orden generada: 900001", FILAS)
    assert (r.tipo, r.asignaciones) == ("os", [(2, "900001")])


def test_texto_una_os_una_pendiente():
    r = conciliacion.conciliar_texto("Comparto orden generada: 900002", FILAS[:1] + FILAS[2:])
    assert r.asignaciones == [(1, "900002")]


def test_texto_ambiguo_no_asigna():
    r = conciliacion.conciliar_texto("Comparto orden generada: 900003", FILAS)
    assert (r.tipo, r.asignaciones) == ("ambiguo", [])


def test_serie_de_fila_aceptada_no_cuenta():
    r = conciliacion.conciliar_texto("SER-C orden generada: 900004", FILAS[2:])
    assert r.tipo == "ambiguo"


def test_estatus_sin_os():
    assert conciliacion.es_estatus_sin_os("El equipo está en espera de pieza")
    assert not conciliacion.es_estatus_sin_os("En espera de pieza. Orden generada: 900005")
    assert conciliacion.conciliar_texto("Gracias", FILAS).tipo == "no_os"
