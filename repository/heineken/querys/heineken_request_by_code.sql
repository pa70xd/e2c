-- Folio de un comando del bot, solo si es de Heineken.
SELECT request_code, status
FROM {email_request_table}
WHERE UPPER(request_code) = UPPER(%s)
  AND customer = '{customer}';
