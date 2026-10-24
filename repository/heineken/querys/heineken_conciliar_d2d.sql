-- D2D: OS del operador por request_code + serie.
UPDATE {cooler_request_table}
SET
    os = %(os)s,
    status = %(status)s,
    rejection_reason = %(motivo)s,
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE cliente = '{cliente}'
  AND request_code = %(request_code)s
  AND serie_fabricante = %(serie)s
  AND status <> 'CANCELLED'
RETURNING request_code;
