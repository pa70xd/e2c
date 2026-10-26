-- Solo lectura. Modelos crudos que mandaron los clientes (cooler_request.modelo), agrupados.
-- Sin direcciones, razón social, teléfonos ni series.
SELECT
    e.customer AS cliente,
    c.modelo AS modelo,
    COUNT(*) AS n
FROM {cooler_request_table} c
JOIN {email_request_table} e ON e.request_code = c.request_code
WHERE c.created_at >= %s
GROUP BY e.customer, c.modelo
ORDER BY e.customer, n DESC
