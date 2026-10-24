UPDATE {cooler_request_table}
SET
    status = %s,
    ticket_solicitud = %s,
    updated_at = CURRENT_TIMESTAMP
WHERE
    request_code = %s
    AND (serie_fabricante = %s or serie_dnn_bnf = %s)
    AND status <> 'CANCELLED'
