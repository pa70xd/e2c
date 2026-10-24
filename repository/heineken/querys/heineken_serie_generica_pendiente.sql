-- Reenvío D2D: serie genérica ya generada para el mismo cliente, ACTIVO y FALLA que sigue pendiente.
SELECT serie_fabricante AS serie
FROM {cooler_request_table}
WHERE cliente = '{cliente}'
  AND request_code = %(request_code)s
  AND id_cliente = %(cliente)s
  AND serie_dnn_bnf IS NOT DISTINCT FROM %(activo)s
  AND UPPER(tipo_servicio) = UPPER(%(falla)s)
  AND status = 'PENDING'
  AND (serie_fabricante LIKE 'HEI%%' OR serie_fabricante LIKE 'MOB%%')
  AND NOT (serie_fabricante = ANY(%(usadas)s))
ORDER BY row_number
LIMIT 1;
