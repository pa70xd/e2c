SELECT
    er.request_code,
    er.customer,
    er.status AS request_status,
    er.priority,

    er.total_coolers,
    er.completed_coolers,
    er.failed_coolers,
    er.pending_coolers,

    er.assigned_to,
    er.created_at,
    er.updated_at,
    er.completed_at,

    cr.id AS cooler_id,
    cr.row_number,

    -- Datos de la solicitud
    cr.id_cliente,
    cr.fecha_solicitud,
    cr.modelo,
    cr.serie_fabricante,
    cr.serie_dnn_bnf,
    cr.tipo_servicio,
    cr.canal,
    cr.region,
    cr.plaza,
    cr.razon_social,
    cr.direccion,
    cr.cp,
    cr.ciudad,
    cr.colonia,
    cr.latitud,
    cr.longitud,
    cr.ruta,
    cr.telefono_1,
    cr.telefono_2,
    cr.comentarios,
    cr.cbu,
    cr.cliente,
    cr.os,

    -- Datos de gestión
    cr.status AS cooler_status,
    cr.rejection_reason,
    cr.prioridad,
    cr.folio,
    cr.ticket_solicitud,
    cr.assigned_to AS cooler_assigned_to,
    cr.gestion_observaciones,
    cr.fecha_asignacion,
    cr.fecha_atencion,
    cr.fecha_completado,

    cr.created_at AS cooler_created_at,
    cr.updated_at AS cooler_updated_at

FROM {email_request_table} er
LEFT JOIN {cooler_request_table} cr
    ON cr.request_code = er.request_code


ORDER BY cr.row_number;