"""Los Excel y correos de tests/fixtures/ salen de build_fixtures.py: si alguien
edita uno a mano (o cambia el script sin regenerar) esta prueba lo delata."""

import re
from pathlib import Path

from tests.fixtures import build_fixtures

FIXTURES = Path(build_fixtures.FIXTURES_DIR)


def test_fixtures_versionados_coinciden_con_el_script():
    assert build_fixtures.check() == [], (
        "Regenera con: python tests/fixtures/build_fixtures.py"
    )


def test_los_fixtures_solo_usan_example_com():
    correo = re.compile(r"[\w.+-]+@([\w-]+\.)+\w+")
    for archivo in FIXTURES.rglob("*.json"):
        for coincidencia in correo.finditer(archivo.read_text(encoding="utf-8")):
            assert coincidencia.group(0).endswith("example.com"), f"{archivo}: {coincidencia.group(0)}"
