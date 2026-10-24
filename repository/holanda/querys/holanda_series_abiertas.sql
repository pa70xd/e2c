-- Equipos de Holanda con un caso abierto (sin OS). Llave del equipo:
-- Congelador (serie_dnn_bnf) o, si no hay, Serie (serie_fabricante) -- la
-- misma expresión que HOLANDA_BUSINESS._SQL_LLAVE_EQUIPO en DuckDB.
SELECT DISTINCT llave
FROM (
    SELECT
        COALESCE(
            NULLIF(TRIM(serie_dnn_bnf), ''),
            NULLIF(TRIM(serie_fabricante), '')
        ) AS llave,
        os
    FROM {cooler_request_table}
    WHERE cliente = '{cliente}'
) equipos
WHERE llave = ANY(%s)
  AND (os IS NULL OR TRIM(os) = '');
