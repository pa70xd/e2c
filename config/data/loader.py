"""Carga de catálogos en JSON ubicados junto a este módulo.

La ruta se resuelve con ``Path(__file__)``, nunca con el cwd.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent


def load_json(name):
    """Lee ``config/data/<name>`` (UTF-8) y devuelve el objeto JSON tal cual."""
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)
