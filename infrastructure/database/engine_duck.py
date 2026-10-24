import duckdb


class DuckEngine:

    @staticmethod
    def get():
        return duckdb.connect(":memory:")