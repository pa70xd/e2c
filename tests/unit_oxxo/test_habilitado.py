import pytest

from parsers.oxxo_parse.habilitado import clientes_habilitados, habilitado


@pytest.fixture(autouse=True)
def _sin_variable(monkeypatch):
    monkeypatch.delenv("E2C_CLIENTES_HABILITADOS", raising=False)


def test_apagado_por_defecto():
    assert not habilitado("oxxo")
    assert not habilitado("oxxo_garantias")
    assert clientes_habilitados() == frozenset()


@pytest.mark.parametrize("valor,oxxo,garantias", [
    ("oxxo", True, False),
    ("oxxo_garantias", False, True),
    ("oxxo,oxxo_garantias", True, True),
    (" OXXO , Oxxo_Garantias ", True, True),
    ("danone,holanda", False, False),
    ("oxxo_garantias,,", False, True),
    ("", False, False),
])
def test_lista_separada_por_comas(monkeypatch, valor, oxxo, garantias):
    monkeypatch.setenv("E2C_CLIENTES_HABILITADOS", valor)
    assert habilitado("oxxo") is oxxo
    assert habilitado("oxxo_garantias") is garantias


def test_se_lee_en_cada_llamada(monkeypatch):
    assert not habilitado("oxxo")
    monkeypatch.setenv("E2C_CLIENTES_HABILITADOS", "oxxo")
    assert habilitado("oxxo")
