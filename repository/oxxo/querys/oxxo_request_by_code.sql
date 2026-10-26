-- Valida que el folio de un comando del bot exista y sea del cliente.
SELECT request_code, status
FROM {email_request_table}
WHERE UPPER(request_code) = UPPER(%s)
  AND customer = %s;
