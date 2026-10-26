"""Los fixtures de Oxxo salen de tests/fixtures/oxxo/build_oxxo.py."""

import re

from tests.fixtures.oxxo import build_oxxo


def test_fixtures_versionados_coinciden_con_el_script():
    assert build_oxxo.check() == [], "Regenera con: python tests/fixtures/oxxo/build_oxxo.py"


def test_los_correos_solo_usan_example_com():
    texto = (build_oxxo.OUT / "correos.json").read_text(encoding="utf-8")
    for m in re.finditer(r"[\w.+-]+@([\w-]+\.)+\w+", texto):
        assert m.group(0).endswith("example.com"), m.group(0)
