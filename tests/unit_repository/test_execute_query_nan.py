"""``execute_query`` convierte NaN / pd.NA / NaT en None antes de ejecutar."""

import numpy as np
import pandas as pd
import pytest
from psycopg2.extras import Json

from infrastructure.database import postgres

# El harness reemplaza postgres.execute_query por un bloqueo en cada prueba:
# se guarda la función real al importar (get_connection sí se parchea abajo).
EXECUTE_QUERY = postgres.execute_query


class _Cursor:
    description = None

    def __init__(self, registro):
        self.registro = registro

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, query, params):
        self.registro.append(params)


class _Conn:
    def __init__(self, registro):
        self.registro = registro

    def cursor(self, *a, **k):
        return _Cursor(self.registro)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def ejecutar(monkeypatch):
    registro = []
    monkeypatch.setattr(postgres, "get_connection", lambda: _Conn(registro))

    def _ejecutar(params):
        EXECUTE_QUERY("SELECT %s", params)
        return registro[-1]

    return _ejecutar


def test_nan_na_nat_pasan_a_none_en_tupla(ejecutar):
    assert ejecutar((float("nan"), pd.NA, pd.NaT, np.float64("nan"), np.float32("nan"))) == (None,) * 5


def test_lista_y_dict_de_parametros(ejecutar):
    assert ejecutar([1, float("nan"), "a"]) == [1, None, "a"]
    assert ejecutar({"a": float("nan"), "b": pd.NA, "c": 2}) == {"a": None, "b": None, "c": 2}


def test_anidados(ejecutar):
    assert ejecutar(([1.0, float("nan")], ("x", pd.NaT))) == ([1.0, None], ("x", None))


def test_valores_normales_no_cambian(ejecutar):
    import datetime as dt
    from decimal import Decimal

    j = Json({"a": 1})
    fecha = dt.datetime(2026, 1, 1)
    params = (0, 0.0, -1.5, float("inf"), "", "nan", b"x", True, False, fecha, Decimal("1.2"), j)
    salida = ejecutar(params)
    assert salida == params and salida[-1] is j and salida[3] == float("inf")


def test_none_y_params_vacios(ejecutar):
    assert ejecutar(()) == ()
    assert ejecutar((None, 1)) == (None, 1)
