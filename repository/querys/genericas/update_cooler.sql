UPDATE {cooler_request_table}
SET
    status = %s,
    ticket_solicitud = %s,
    updated_at = CURRENT_TIMESTAMP
WHERE
    request_code = %s
    AND (
        serie_fabricante = NULLIF(TRIM(%s), '')
        OR serie_dnn_bnf = NULLIF(TRIM(%s), '')
    )
    AND status <> 'CANCELLED'
RETURNING request_code, row_number;
