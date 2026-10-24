SELECT DISTINCT
    cliente,
    categoria
FROM repare.catalogo_servicios_ruta
WHERE cliente IN ({clientes})
ORDER BY cliente, categoria;