"""parsers/core/lector.py: lector común de adjuntos (archivos sintéticos)."""

import pytest

from parsers.core.lector import (
    AdjuntoIlegible,
    es_adjunto_soportado,
    leer_adjunto,
    normalizar_encabezado,
)
from tests.fixtures.lector import build_lector_fixtures as fx

DIR = fx.DIR


def _leer(nombre, vocab, claves=(), **kw):
    return leer_adjunto(nombre, (DIR / nombre).read_bytes(), vocab, claves=claves, **kw)


def test_normalizar_encabezado():
    assert normalizar_encabezado("DELEGACION/\nMUNICIPIO/\nCIUDAD") == "DELEGACION/MUNICIPIO/CIUDAD"
    assert normalizar_encabezado("CEDIS/DISTRIBUIDORA/\nSUCURSAL") == normalizar_encabezado("Cedis/Distribuidora/ Sucursal")
    assert normalizar_encabezado("  No   Serie ") == "NO SERIE"
    assert normalizar_encabezado("Dirección") == "DIRECCION"
    assert normalizar_encabezado(None) == ""


def test_extensiones_soportadas():
    assert all(es_adjunto_soportado(n) for n in ("a.xlsx", "a.XLS", "a.xlsm", "a.ods"))
    assert not es_adjunto_soportado("a.csv")
    assert not es_adjunto_soportado("~$a.xlsx")


def test_archivos_versionados_coinciden_con_el_script():
    for nombre, fn in fx.ARCHIVOS.items():
        if nombre.endswith(".xls"):
            pytest.importorskip("xlwt")
        viejo = _leer(nombre, fx.VOCAB_KOF + fx.VOCAB_RUTA, hojas_ocultas="siempre")
        nuevo = leer_adjunto(nombre, fn(), fx.VOCAB_KOF + fx.VOCAB_RUTA, "siempre")
        assert [(t.hoja, t.columnas, t.df.values.tolist()) for t in viejo] == [
            (t.hoja, t.columnas, t.df.values.tolist()) for t in nuevo
        ]


# --- encabezado --------------------------------------------------------------

@pytest.mark.parametrize("fila", [1, 4])
def test_encabezado_en_cualquier_fila(fila):
    (t,) = _leer(f"encabezado_fila{fila}.xlsx", fx.VOCAB_RUTA)
    assert t.fila_encabezado == fila
    assert t.columnas == ["FOLIO", "NO SERIE", "MODELO", "CALLE"]
    assert t.df.iloc[0]["FOLIO"] == "F-9"
    assert list(t.df.index) == [fila + 1]  # fila original de la hoja


def test_encabezado_agrupado_se_salta_a_la_fila_de_nombres():
    (t,) = _leer("ruta.xlsx", fx.VOCAB_RUTA, fx.CLAVES_RUTA)
    assert t.hoja == "RUTA"
    assert t.fila_encabezado == 2
    assert "DATOS DE DIRECCION" not in t.columnas
    assert t.columnas[:4] == ["FOLIO", "NO SERIE", "MODELO", "CALLE"]


def test_sin_vocabulario_coincidente_no_devuelve_tablas():
    assert _leer("ruta.xlsx", ["NADA", "QUE VER"]) == []


def test_encabezado_con_saltos_de_linea_se_normaliza():
    t = _leer("kof.xlsx", fx.VOCAB_KOF, fx.CLAVES_KOF)[0]
    assert "DELEGACION/MUNICIPIO/CIUDAD" in t.columnas
    assert "CEDIS/DISTRIBUIDORA/SUCURSAL" in t.columnas


# --- hojas ocultas -----------------------------------------------------------

def test_kof_oculta_con_mismo_encabezado_si_se_lee():
    tablas = _leer("kof.xlsx", fx.VOCAB_KOF, fx.CLAVES_KOF)
    assert [t.hoja for t in tablas] == ["REPORTE"] + [f"DIA{k}" for k in range(1, 8)]
    assert [t.oculta for t in tablas] == [False] + [True] * 7
    assert sum(len(t.df) for t in tablas) == 1 + 7 * 2


def test_catalogos_ocultos_no_son_datos():
    tablas = _leer("ruta.xlsx", fx.VOCAB_RUTA, fx.CLAVES_RUTA)
    assert [t.hoja for t in tablas] == ["RUTA"]


def test_modo_nunca_ignora_ocultas():
    tablas = _leer("kof.xlsx", fx.VOCAB_KOF, fx.CLAVES_KOF, hojas_ocultas="nunca")
    assert [t.hoja for t in tablas] == ["REPORTE"]


def test_modo_siempre_lee_ocultas_con_encabezado():
    tablas = _leer("kof.xlsx", fx.VOCAB_KOF + ["CLAVE", "DESCRIPCION"], hojas_ocultas="siempre")
    assert len(tablas) == 9  # incluye el catálogo veryHidden cuyo encabezado sí está en el vocabulario


def test_oculta_con_encabezado_distinto_se_ignora_en_si_coinciden():
    tablas = _leer("kof.xlsx", fx.VOCAB_KOF + ["CLAVE", "DESCRIPCION"])
    assert "CATALOGO" not in [t.hoja for t in tablas]


def test_modo_invalido():
    with pytest.raises(ValueError):
        _leer("kof.xlsx", fx.VOCAB_KOF, hojas_ocultas="a_veces")


# --- filas basura ------------------------------------------------------------

def test_filas_basura_se_descartan_y_se_cuentan(capsys):
    (t,) = _leer("ruta.xlsx", fx.VOCAB_RUTA, fx.CLAVES_RUTA)
    assert t.descartes == {"vacias": 1, "una_celda": 1, "encabezado_repetido": 1, "sin_clave": 1}
    assert t.df["FOLIO"].tolist() == ["F-1", "F-2"]
    out = capsys.readouterr().out
    assert "descartes=" in out and "Calle Dos 2" not in out and "F-1" not in out


def test_celdas_vacias_son_none_y_texto_sin_espacios():
    (t,) = _leer("ruta.xlsx", fx.VOCAB_RUTA, fx.CLAVES_RUTA)
    assert t.df.loc[3, "TELEFONO"] == "5550100"
    assert t.df.loc[7, "NO SERIE"] is None


def test_sin_claves_solo_aplica_regla_de_una_celda():
    (t,) = _leer("ruta.xlsx", fx.VOCAB_RUTA)
    assert t.descartes["sin_clave"] == 0 and len(t.df) == 3


# --- formatos ----------------------------------------------------------------

def test_xlsm_por_extension():
    contenido = (DIR / "ruta.xlsx").read_bytes()
    (t,) = leer_adjunto("ruta.xlsm", contenido, fx.VOCAB_RUTA)
    assert t.hoja == "RUTA"


def test_ods_visible_y_ocultas():
    tablas = _leer("penafiel.ods", fx.VOCAB_RUTA, fx.CLAVES_RUTA)
    assert [(t.hoja, t.oculta) for t in tablas] == [("DSD", False), ("DSD_OCULTA", True)]
    assert tablas[1].df["FOLIO"].tolist() == ["F-2"]
    assert [t.hoja for t in _leer("penafiel.ods", fx.VOCAB_RUTA, hojas_ocultas="nunca")] == ["DSD"]


def test_base64():
    import base64
    contenido = base64.b64encode((DIR / "ruta.xlsx").read_bytes())
    assert contenido.startswith(b"UEs")
    assert len(leer_adjunto("ruta.xlsx", contenido, fx.VOCAB_RUTA)) == 1


def test_extension_no_soportada_y_archivo_corrupto():
    with pytest.raises(ValueError):
        leer_adjunto("datos.csv", b"a,b", fx.VOCAB_RUTA)
    with pytest.raises(AdjuntoIlegible):
        leer_adjunto("roto.xlsx", b"no es un excel", fx.VOCAB_RUTA)
    with pytest.raises(AdjuntoIlegible):
        leer_adjunto("roto.ods", b"no es un ods", fx.VOCAB_RUTA)


def test_xls_visible_y_oculta():
    # Bug encontrado en la Fase 4: .xls estaba en las listas de extensiones pero
    # xlrd no estaba en requirements.txt, así que nunca se podía abrir.
    tablas = _leer("ruta.xls", fx.VOCAB_RUTA, fx.CLAVES_RUTA, hojas_ocultas="siempre")
    assert [(t.hoja, t.oculta) for t in tablas] == [("RUTA", False), ("CATALOGO", True)]
    assert tablas[0].df["FOLIO"].tolist() == ["F-1", "F-2"]
    assert [t.hoja for t in _leer("ruta.xls", fx.VOCAB_RUTA, hojas_ocultas="nunca")] == ["RUTA"]
    # La oculta tiene otro encabezado: en "si_coinciden" no se lee.
    assert [t.hoja for t in _leer("ruta.xls", fx.VOCAB_RUTA)] == ["RUTA"]


# --- faltantes: None, nunca NaN (pandas 3 los vuelve NaN en iterrows) --------

def _es_nan(v):
    return isinstance(v, float)


def test_celdas_vacias_son_none_en_todas_las_formas_de_iterar():
    for nombre, vocab, claves in [("ruta.xlsx", fx.VOCAB_RUTA, fx.CLAVES_RUTA), ("kof.xlsx", fx.VOCAB_KOF, fx.CLAVES_KOF)]:
        for t in _leer(nombre, vocab, claves):
            valores = {
                "iterrows": [v for _, f in t.df.iterrows() for v in f],
                "itertuples": [v for f in t.df.itertuples(index=False) for v in f],
                "records": [v for f in t.df.to_dict("records") for v in f.values()],
                "filas": [v for f in t.filas() for k, v in f.items() if k != "_fila"],
                "iloc": [v for i in range(len(t.df)) for v in t.df.iloc[i].tolist()],
                "values": [v for f in t.df.values.tolist() for v in f],
            }
            for forma, vs in valores.items():
                assert not any(_es_nan(v) for v in vs), f"{nombre}/{t.hoja}: NaN en {forma}"
                assert all(v is None or isinstance(v, str) for v in vs), forma
            assert None in valores["iterrows"] or nombre == "kof.xlsx"


def test_iterrows_conserva_none_y_el_indice_de_fila():
    (t,) = _leer("ruta.xlsx", fx.VOCAB_RUTA, fx.CLAVES_RUTA)
    (idx, fila) = list(t.df.iterrows())[1]
    assert idx == 7 and fila.name == 7
    assert fila["NO SERIE"] is None and fila["FOLIO"] == "F-2"


def test_none_sobrevive_a_filtrar_y_copiar():
    (t,) = _leer("ruta.xlsx", fx.VOCAB_RUTA, fx.CLAVES_RUTA)
    sub = t.df[t.df["FOLIO"] == "F-2"].copy()
    assert [v for _, f in sub.iterrows() for v in f if v is None]
    assert t.df.drop(columns=["CALLE"]).to_dict("records")[1]["NO SERIE"] is None


def test_filas_trae_la_fila_original():
    (t,) = _leer("ruta.xlsx", fx.VOCAB_RUTA, fx.CLAVES_RUTA)
    assert [f["_fila"] for f in t.filas()] == [3, 7]
    assert t.filas()[1]["NO SERIE"] is None


def test_tabla_vacia_tambien_es_iterable():
    (t,) = _leer("encabezado_fila1.xlsx", fx.VOCAB_RUTA, hojas_ocultas="nunca")
    vacio = t.df.iloc[0:0]
    assert list(vacio.iterrows()) == [] and t.df.to_dict("records")
