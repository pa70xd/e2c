def unir_tablas(tables: list[dict], duck_conn) -> str:
    if not tables:
        return None

    tabla_destino = tables[0]["table"]

    # Obtener columnas de la primera tabla
    columnas = duck_conn.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{tabla_destino}'
        ORDER BY ordinal_position
    """).fetchall()

    columnas = [c[0] for c in columnas]

    selects = [f'SELECT * FROM "{tabla_destino}"']

    for tabla in tables[1:]:
        nombre = tabla["table"]

        cols = duck_conn.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{nombre}'
            ORDER BY ordinal_position
        """).fetchall()

        cols = [c[0] for c in cols]

        # Si la estructura cambia, regresar la primera tabla sin modificar
        if cols != columnas:
            return tabla_destino

        selects.append(f'SELECT * FROM "{nombre}"')

    union_sql = "\nUNION ALL\n".join(selects)

    duck_conn.execute(f"""
        CREATE OR REPLACE TABLE "{tabla_destino}" AS
        {union_sql}
    """)

    return tabla_destino
