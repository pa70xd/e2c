from config.data import loader as _loader

catalog = _loader.load_json("danone_model_line_cat.json")
del _loader
