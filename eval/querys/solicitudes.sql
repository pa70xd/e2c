-- Solo lectura. Cabecera de las solicitudes pedidas (sin datos personales).
SELECT
    request_code,
    customer,
    status,
    total_coolers,
    pending_coolers,
    completed_coolers,
    failed_coolers,
    created_at
FROM {email_request_table}
WHERE request_code = ANY(%s)
