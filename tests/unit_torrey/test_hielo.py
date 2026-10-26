import pytest

from parsers.torrey import PERFIL_TORREY
from parsers.torrey_parse.hielo import cliente_os_hielo


@pytest.mark.parametrize("fila, esperado", [
    ({"MODELO": "TOR-HL50", "FALLA": "Máquina de hielo no produce"}, "IMBERA"),
    ({"MODELO": "FABRICA DE HIELO 500", "FALLA": ""}, "IMBERA"),
    ({"MODELO": "ICE MAKER X", "FALLA": ""}, "IMBERA"),
    ({"MODELO": "TOR-V300", "FALLA": "No enfría, se forma hielo en el evaporador"}, None),
    ({"MODELO": "TOR-V300", "FALLA": ""}, None),
])
def test_cliente_os_hielo(fila, esperado):
    assert cliente_os_hielo(fila) == esperado


def test_perfil_torrey():
    assert PERFIL_TORREY.customer == "torrey"
    assert PERFIL_TORREY.cliente_os == "TORREY"
    assert PERFIL_TORREY.siempre_garantia
