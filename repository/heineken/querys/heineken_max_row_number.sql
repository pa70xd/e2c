SELECT COALESCE(MAX(row_number), 0) AS maximo
FROM {cooler_request_table}
WHERE request_code = %s;
