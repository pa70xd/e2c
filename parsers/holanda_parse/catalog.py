"""Distribuidora de Holanda por CP, contra la misma tabla de Postgres que
usan Danone y Bonafont (cp_ruta + distribuidoras_repare, vía
DB_POSTGRE.get_distribuidora_ruta). Más simple que la de Danone: Holanda
es solo ruta (nunca cp_mov) y tiene una sola marca fija (sin CBU)."""

from repository.danone.consultas_postgre import DB_POSTGRE

db = DB_POSTGRE()

# Valor de `descr_gpo_precios` en distribuidoras_repare para Holanda
# (verificado: encuentra distribuidoras "DIST HOLANDA ...").
MARCA_HOLANDA = "HOLANDA"


class HOLANDA_CATALOG:

    def __init__(self, duckConn):
        self.duckConn = duckConn

    def calcula_distribuidora(self, table):
        """Agrega y llena DISTRIBUIDORA_GEN y CLIENTE por CP (una consulta
        por CP distinto dentro del lote)."""

        self.duckConn.execute(f'''
            ALTER TABLE "{table}"
            ADD COLUMN IF NOT EXISTS "DISTRIBUIDORA_GEN" VARCHAR
        ''')
        self.duckConn.execute(f'''
            ALTER TABLE "{table}"
            ADD COLUMN IF NOT EXISTS "CLIENTE" VARCHAR
        ''')

        rows = self.duckConn.execute(f'''
            SELECT rowid, "CP"
            FROM "{table}"
            WHERE "CP" IS NOT NULL
              AND TRIM(CAST("CP" AS VARCHAR)) != ''
        ''').fetchall()

        cache = {}

        for rowid, cp in rows:

            cp = str(cp).strip()

            if cp not in cache:

                try:
                    resultado = db.get_distribuidora_ruta(cp, MARCA_HOLANDA)
                except Exception as e:
                    print(f"Error consultando distribuidora para CP {cp}: {e}")
                    resultado = None

                cache[cp] = (
                    resultado.get("distribuidora_id") if resultado else None,
                    resultado.get("nombre_resp_pago") if resultado else None,
                )

            distribuidora_gen, cliente = cache[cp]

            self.duckConn.execute(f'''
                UPDATE "{table}"
                SET
                    "DISTRIBUIDORA_GEN" = ?,
                    "CLIENTE" = ?
                WHERE rowid = ?
            ''', [distribuidora_gen, cliente, rowid])

        return table
