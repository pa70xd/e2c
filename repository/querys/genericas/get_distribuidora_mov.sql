select
    DISTINCT
    cpm.codigo_postal,
    cpm.centro,
    dr.nombre_resp_pago,
    dr.distribuidora,
    concat(distribuidora,' | ',nombre_distribuidora) as distribuidora_id
from
    repare_email_parse.cp_mov cpm
inner join
    repare_email_parse.distribuidoras_repare dr
    ON dr.centro = cpm.centro
where
    codigo_postal = %s
AND
UPPER(descr_gpo_precios) LIKE UPPER(%s);