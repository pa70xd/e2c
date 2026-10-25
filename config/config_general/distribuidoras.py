from config.data import loader as _loader

CATALOG_DISTRIBUIDORAS = _loader.load_json("distribuidoras.json")
del _loader
