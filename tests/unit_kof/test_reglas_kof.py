"""Lectura y reglas de KOF sin el pipeline completo."""

import pandas as pd
import pytest

import src.service as service
from bot.commands import PerfilBot
from bot.perfiles import perfil_kof
from config.customers.kof import columns_names as col
from config.customers.kof import reglas_kof as reglas
from parsers.kof import KOF_INIT, KOF_REPLY
from parsers.kof_parse import lector_adapter
from parsers.kof_parse.business import MOTIVO, TIPO, KOF_BUSINESS
from parsers.kof_parse.process_data import KOF_PROCESS, estatus_os
from parsers.kof_parse.reader import HOJA, columna_canonica, tabla_de_texto, unir_hojas
from tests.fixtures.kof import build_kof
from tests.unit_kof.test_golden_kof import CORREOS, FIXTURES


def _hojas(nombre):
    return lector_adapter.leer_libro(nombre, (FIXTURES / nombre).read_bytes())


def _df(*filas):
    return pd.DataFrame(list(filas))


def test_fixtures_kof_coinciden_con_el_script():
    assert build_kof.check() == [], "Regenera con: python tests/fixtures/kof/build_kof.py"


@pytest.mark.parametrize(
    "encabezado, canonica",
    [
        ("No SERIE", col.SERIE),
        ("No CLIENTE DETALLISTA- CONCATENADO", col.CLIENTE_CONCATENADO),
        ("CEDIS/DISTRIBUIDORA/ SUCURSAL", col.CEDIS),
        ("Folio (.Net)", col.FOLIO),
        ("Serie a retirar", col.SERIE_RETIRO),
        ("SAP a instalar", col.ACTIVO),
        ("OS REPARE", col.OS),
        ("Dirección", col.DIRECCION),
        ("COLUMNA INVENTADA", None),
    ],
)
def test_alias_de_columnas(encabezado, canonica):
    assert columna_canonica(encabezado) == canonica


def test_reporte_falla_lee_hojas_ocultas_y_descarta_basura():
    hojas = _hojas("reporte_falla.xlsx")
    assert [h["visible"] for h in hojas] == [True] + [False] * 7
    df = unir_hojas(hojas)
    # 4 buenas + 1 sin detallista en la visible, 12 en las ocultas; sin basura.
    assert len(df) == 17
    assert (df[HOJA] == "REPORTE").sum() == 5
    assert df[col.SERIE].notna().all()


def test_hojas_repetidas_no_duplican_filas():
    hojas = _hojas("reporte_falla.xlsx")
    copia = dict(hojas[1], hoja="Copia")
    assert len(unir_hojas(hojas + [copia])) == len(unir_hojas(hojas))


def test_hoja_sin_encabezado_kof_se_ignora():
    hoja = {"name": "x.xlsx", "hoja": "H", "visible": True, "fila_encabezado": 1,
            "columnas": ["MODELO", "CEDIS", "OBSERVACIONES"],
            "dataframe": pd.DataFrame([["M", "C", "O"]], columns=["MODELO", "CEDIS", "OBSERVACIONES"], index=[2])}
    assert unir_hojas([hoja]).empty


def test_falla_es_ruta_servicio_de_distribuidor():
    aceptados, rechazados = KOF_BUSINESS.aplicar(unir_hojas(_hojas("reporte_falla.xlsx")))
    assert len(aceptados) == 16
    assert [r[MOTIVO] for r in rechazados] == [reglas.MOTIVO_SIN_DETALLISTA]
    assert {r[TIPO] for r in aceptados} == {reglas.SERVICIO_DISTRIBUIDOR, reglas.VENTA_MATERIAL}


@pytest.mark.parametrize("columna, valor", [(col.FALLA, "VENTA DE EXTENSIÓN"), (col.SOLICITUD, "charolas"), (col.FALLA, "PARRILLA")])
def test_venta_de_material_es_ruta_y_nunca_falla(columna, valor):
    fila = {col.SERIE: "S1", col.ID_CLIENTE: "D1", col.FALLA: "NO ENFRIA", columna: valor}
    (registro,), _ = KOF_BUSINESS.aplicar(_df(fila))
    assert registro[TIPO] == reglas.VENTA_MATERIAL


def test_parrilla_en_observaciones_sigue_siendo_falla():
    fila = {col.SERIE: "S1", col.ID_CLIENTE: "D1", col.FALLA: "NO ENFRIA", col.OBSERVACIONES: "parrilla rota"}
    (registro,), _ = KOF_BUSINESS.aplicar(_df(fila))
    assert registro[TIPO] == reglas.SERVICIO_DISTRIBUIDOR


@pytest.mark.parametrize("movimiento", ["Cobertura", "EQUIPO ADICIONAL", "Instalación"])
def test_cobertura_y_equipo_adicional_son_instalacion(movimiento):
    fila = {col.TIPO_MOVIMIENTO: movimiento, col.SERIE: "S1", col.ID_CLIENTE: "D1"}
    (registro,), _ = KOF_BUSINESS.aplicar(_df(fila))
    assert registro[TIPO] == reglas.INSTALACION


def test_cambio_de_equipo_es_instalacion_mas_retiro():
    fila = {
        col.TIPO_MOVIMIENTO: "Cambio de Equipo", col.ID_CLIENTE: "D1",
        col.SERIE: "NUEVA", col.MODELO: "M-N", col.ACTIVO: "SAP-N",
        col.SERIE_RETIRO: "VIEJA", col.MODELO_RETIRO: "M-V", col.ACTIVO_RETIRO: "SAP-V",
    }
    (instalacion, retiro), _ = KOF_BUSINESS.aplicar(_df(fila))
    assert (instalacion[TIPO], instalacion[col.SERIE], instalacion[col.ACTIVO]) == (reglas.INSTALACION, "NUEVA", "SAP-N")
    assert (retiro[TIPO], retiro[col.SERIE], retiro[col.MODELO], retiro[col.ACTIVO]) == (reglas.RETIRO, "VIEJA", "M-V", "SAP-V")


def test_cambio_sin_serie_a_retirar_rechaza_solo_el_retiro():
    fila = {col.TIPO_MOVIMIENTO: "Cambio de Equipo", col.ID_CLIENTE: "D1", col.SERIE: "NUEVA"}
    aceptados, rechazados = KOF_BUSINESS.aplicar(_df(fila))
    assert [r[TIPO] for r in aceptados] == [reglas.INSTALACION]
    assert [r[MOTIVO] for r in rechazados] == [reglas.MOTIVO_SIN_SERIE_RETIRO]


def test_bitacora_genera_nueve_registros():
    aceptados, rechazados = KOF_BUSINESS.aplicar(unir_hojas(_hojas("bitacora.xlsx")))
    assert len(aceptados) == 9 and not rechazados


@pytest.mark.parametrize(
    "fila, motivo",
    [
        ({col.TIPO_MOVIMIENTO: "Mantenimiento", col.SERIE: "S1", col.ID_CLIENTE: "D1"}, reglas.MOTIVO_MOVIMIENTO),
        ({col.SERIE: "S1", col.ID_CLIENTE: "D1"}, reglas.MOTIVO_SIN_TIPO),
        ({col.FALLA: "NO ENFRIA", col.ID_CLIENTE: "D1"}, reglas.MOTIVO_SIN_SERIE),
        ({col.FALLA: "NO ENFRIA", col.SERIE: "S1"}, reglas.MOTIVO_SIN_DETALLISTA),
    ],
)
def test_rechazos(fila, motivo):
    aceptados, (rechazado,) = KOF_BUSINESS.aplicar(_df(fila))
    assert not aceptados and rechazado[MOTIVO] == motivo


def test_serie_repetida_en_el_archivo_se_rechaza():
    fila = {col.FALLA: "NO ENFRIA", col.SERIE: "S1", col.ID_CLIENTE: "D1"}
    aceptados, rechazados = KOF_BUSINESS.aplicar(_df(fila, dict(fila, **{col.FALLA: "LO CONGELA"})))
    assert len(aceptados) == 1 and [r[MOTIVO] for r in rechazados] == [reglas.MOTIVO_DUPLICADA]


def test_texto_plano_es_proyecto_especial_sin_serie():
    df = tabla_de_texto(CORREOS["init_texto"]["body"])
    (registro,), rechazados = KOF_BUSINESS.aplicar(df)
    assert registro[TIPO] == reglas.PROYECTO_ESPECIAL and not rechazados
    assert registro[col.FOLIO] == "900001"


def test_texto_plano_sin_folio_no_es_solicitud():
    assert tabla_de_texto("Nombre: Tienda\nDirección: Calle 1\nCEDIS: X").empty
    assert tabla_de_texto(CORREOS["init_bitacora"]["body"]).empty


@pytest.mark.parametrize(
    "os_valor, estado",
    [(None, "REJECTED"), ("", "REJECTED"), ("403000001", "ACCEPTED"), ("00403001", "ACCEPTED"),
     ("12345", "PENDING"), ("[RECHAZADO] sin serie", "PENDING")],
)
def test_estatus_os(os_valor, estado):
    assert estatus_os(os_valor) == estado


def test_conciliacion_outbound_por_serie():
    df = KOF_PROCESS.prepare_cooler_update(unir_hojas(_hojas("respuesta_bitacora.xlsx")))
    assert len(df) == 9
    assert set(df["serial_number"]) == {f"KN{n:07d}" for n in range(1, 7)} | {f"KV{n:07d}" for n in (1, 3, 5)}
    assert (df["status"] == "ACCEPTED").sum() == 8


def test_cambio_con_una_os_concilia_instalacion_y_retiro():
    fila = {col.TIPO_MOVIMIENTO: "Cambio de Equipo", col.SERIE: "N", col.SERIE_RETIRO: "V", col.OS: "403123"}
    df = KOF_PROCESS.prepare_cooler_update(_df(fila))
    assert list(df["serial_number"]) == ["N", "V"] and set(df["os"]) == {"403123"}


def test_registro_en_service_y_perfil_del_bot():
    assert service.PARSERS_INIT["kof"] is KOF_INIT and service.PARSERS_REPLY["kof"] is KOF_REPLY
    assert service.PARSERS_INIT["test_kof"] is KOF_INIT and service.PARSERS_REPLY["test_kof"] is KOF_REPLY
    assert service.resolve_test_customer("[kof] Bitácora") == "kof"
    assert isinstance(perfil_kof(object(), object(), object()), PerfilBot)
