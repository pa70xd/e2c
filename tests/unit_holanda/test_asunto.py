"""``es_asunto_holanda``: asuntos inventados, con y sin fecha."""

import pytest

from parsers.holanda import es_asunto_holanda


@pytest.mark.parametrize("asunto", [
    "Casos REPARE",
    "Casos REPARE ",
    "casos repare",
    "CASOS REPARE",
    "Casos REPARE 04052026",
    "RE: Casos REPARE 04052026",
    "RV: Casos REPARE 04052026",
    "FW: Casos REPARE 04052026",
    "Fwd: RE: Casos REPARE 04052026",
    "re: casos repare 04052026",
    "Casos REPARE 04/05/2026",
    "Casos REPARE 04-05-26",
    "Casos REPARE 2",
    "Casos   REPARE   04052026",
    "[holanda] Casos REPARE 04052026",
    "RE: [externo] Casos REPARE",
])
def test_acepta(asunto):
    assert es_asunto_holanda(asunto)


@pytest.mark.parametrize("asunto", [
    None,
    "",
    "Casos",
    "REPARE",
    "Otro tema distinto",
    "Reporte de Casos REPARE",
    "Casos REPARE semana 18",
    "Casos REPARE 04052026 urgente",
    "Casos REPARE urgente",
    "Casos REPARE04052026",
    "Casos REPARES 04052026",
    "Fwd: Revisar Casos REPARE 04052026",
    "Casos REPARE 04052026 x",
    "Casos REPARE -",
])
def test_rechaza(asunto):
    assert not es_asunto_holanda(asunto)
