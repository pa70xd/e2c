-- D2D respaldo (la serie no coincide): primer caso sin conciliar con el mismo cliente, ACTIVO y FALLA.
-- Guarda la serie que trae la respuesta (si trae una).
UPDATE {cooler_request_table}
SET
    serie_fabricante = COALESCE(%(serie)s, serie_fabricante),
    os = %(os)s,
    status = %(status)s,
    rejection_reason = %(motivo)s,
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE id = (
    SELECT id
    FROM {cooler_request_table}
    WHERE cliente = '{cliente}'
      AND request_code = %(request_code)s
      AND id_cliente = %(cliente)s
      AND serie_dnn_bnf IS NOT DISTINCT FROM %(activo)s
      AND UPPER(tipo_servicio) = UPPER(%(falla)s)
      AND status <> 'CANCELLED'
      AND (os IS NULL OR TRIM(os) = '')
    ORDER BY row_number
    LIMIT 1
)
RETURNING request_code;
