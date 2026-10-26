-- Outbound con Excel (Imbera/Torrey): OS por serie dentro de la solicitud.
-- Una fila cancelada (bot.cancelar) no se revive.
UPDATE {cooler_request_table}
SET
    os = %s,
    status = 'ACCEPTED',
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE request_code = %s
  AND (
      serie_fabricante = NULLIF(TRIM(%s), '')
      OR serie_dnn_bnf = NULLIF(TRIM(%s), '')
  )
  AND status NOT IN ('CANCELLED', 'REJECTED')
RETURNING request_code, row_number;
