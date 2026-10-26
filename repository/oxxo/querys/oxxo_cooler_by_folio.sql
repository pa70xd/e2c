-- La solicitud más antigua de un folio, en cualquiera de los dos clientes
-- de Oxxo (escalaciones de garantía y dedupe de mantenimiento).
SELECT request_code, row_number, status, cliente
FROM {cooler_request_table}
WHERE cliente IN ({clientes})
  AND folio = %s
ORDER BY created_at, request_code, row_number
LIMIT 1;
