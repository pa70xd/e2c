-- Ruta: OS del operador por ORDEN (folio); sin ORDEN, el caso más reciente de esa serie sin ORDEN.
UPDATE {cooler_request_table}
SET
    os = %(os)s,
    status = %(status)s,
    rejection_reason = %(motivo)s,
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE id = (
    SELECT id
    FROM {cooler_request_table}
    WHERE cliente = '{cliente}'
      AND status <> 'CANCELLED'
      AND (
        (CAST(%(orden)s AS TEXT) IS NOT NULL AND folio = %(orden)s)
        OR (CAST(%(orden)s AS TEXT) IS NULL AND folio IS NULL AND serie_fabricante = %(serie)s)
      )
    ORDER BY created_at DESC
    LIMIT 1
)
RETURNING request_code;
