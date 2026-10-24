-- Outbound: OS por CASO2 (folio). Un caso cancelado con bot.cancelar no se
-- revive si después llega su OS.
UPDATE {cooler_request_table}
SET
    os = %s,
    status = 'ACCEPTED',
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE cliente = '{cliente}'
  AND folio = %s
  AND status <> 'CANCELLED';
