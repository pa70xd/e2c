"""Los catálogos movidos a config/data/*.json son idénticos a los módulos .py originales.

El original se obtiene con ``git show`` desde el commit base (antes del refactor).
"""
import importlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASE_COMMIT = "55acb2fbf04ee4aa091b99e295fef7c87657b6e6"

CASOS = [
    ("config/config_general/distribuidoras.py", "config.config_general.distribuidoras", "distribuidoras.json"),
    ("config/customers/danone/model_line_cat.py", "config.customers.danone.model_line_cat", "danone_model_line_cat.json"),
]


def _original(tmp_path, ruta):
    git = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:{ruta}"], cwd=REPO, capture_output=True
    )
    if git.returncode != 0:
        pytest.skip(f"commit base no disponible: {git.stderr.decode(errors='replace')[:200]}")
    destino = tmp_path / ("orig_" + Path(ruta).name)
    destino.write_bytes(git.stdout)
    spec = importlib.util.spec_from_file_location("orig_" + destino.stem, destino)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _publicos(mod):
    return {n: v for n, v in vars(mod).items() if not n.startswith("__")}


def assert_identico(a, b, ruta="raiz"):
    """Igualdad profunda estricta: mismos tipos (list != tuple, 1 != True) y mismo orden."""
    assert type(a) is type(b), f"{ruta}: {type(a)} != {type(b)}"
    if isinstance(a, dict):
        assert list(a.keys()) == list(b.keys()), f"{ruta}: claves/orden distintos"
        for k in a:
            assert type(k) is type(next(x for x in b if x == k)), f"{ruta}: tipo de clave {k!r}"
            assert_identico(a[k], b[k], f"{ruta}[{k!r}]")
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b), f"{ruta}: longitud"
        for i, (x, y) in enumerate(zip(a, b)):
            assert_identico(x, y, f"{ruta}[{i}]")
    else:
        assert a == b, f"{ruta}: {a!r} != {b!r}"


@pytest.mark.parametrize("ruta,modulo,_json", CASOS)
def test_mismos_nombres_tipos_y_valores(tmp_path, ruta, modulo, _json):
    orig = _publicos(_original(tmp_path, ruta))
    nuevo = _publicos(importlib.import_module(modulo))
    assert set(orig) == set(nuevo)
    for nombre in orig:
        assert orig[nombre] == nuevo[nombre], nombre
        assert_identico(orig[nombre], nuevo[nombre], nombre)


@pytest.mark.parametrize("ruta,modulo,_json", CASOS)
def test_modulo_no_depende_del_cwd(tmp_path, monkeypatch, ruta, modulo, _json):
    esperado = _publicos(importlib.import_module(modulo))
    monkeypatch.chdir(tmp_path)
    recargado = _publicos(importlib.reload(importlib.import_module(modulo)))
    assert esperado == recargado


@pytest.mark.parametrize("ruta,modulo,nombre_json", CASOS)
def test_json_es_utf8_y_conserva_acentos(nombre_json, ruta, modulo):
    crudo = (REPO / "config/data" / nombre_json).read_bytes()
    crudo.decode("utf-8")
    assert b"\\u00" not in crudo  # sin escapes: acentos literales
    assert json.loads(crudo) == json.loads(crudo.decode("utf-8"))


def test_acentos_presentes():
    from config.config_general.distribuidoras import CATALOG_DISTRIBUIDORAS as d
    assert any("Ñ" in v or "Ó" in v or "ñ" in v for v in d.values())
