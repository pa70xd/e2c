-- Series de Heineken con un caso abierto (sin OS).
SELECT DISTINCT serie_fabricante AS serie
FROM {cooler_request_table}
WHERE cliente = '{cliente}'
  AND serie_fabricante = ANY(%s)
  AND (os IS NULL OR TRIM(os) = '');
