flowchart TD
    A[Microsoft Graph notifica un correo] --> B[src/handler.py<br/>POST /receive_mail]
    B --> C[BackgroundTasks<br/>procesar_mail_background]
    C --> D[src/service.py<br/>processMail]
    D --> E[Graph API<br/>Obtiene metadatos y cuerpo del mensaje]
    E --> F[src/email_type.py<br/>validate_email]

    F -->|No valido: borrador, automatico,<br/>vacio o duplicado| Z[Fin: correo ignorado]
    F -->|Valido| G[detect_customer]
    G -->|No encuentra cliente| Z1[Fin: cliente no valido]
    G -->|danone o test_zuri| H{Tipo de correo}

    H -->|Inicial| I[parsers/danone.py<br/>DANONE_INIT.parse]
    H -->|Respuesta| J[detect_direccion]
    J --> K[parsers/danone.py<br/>DANONE_REPLY.parse]

    subgraph Inicial [Flujo de correo inicial]
        I --> I1[PostgreSQL: email_init_exist<br/>Evita reprocesar el mismo correo]
        I1 -->|Ya existe| Z2[Fin: correo omitido]
        I1 -->|No existe| I2[utils.py: analizar_proposito<br/>Valida que sea una solicitud permitida]
        I2 -->|No permitido| Z3[Fin: solicitud ignorada]
        I2 -->|Permitido| I3[reader.py: get_adjuntos]
        I3 --> I4[Descarga Excel .xlsx o .xls<br/>Ignora temporales y otros adjuntos]
        I4 --> I5[Normaliza columnas con<br/>columns_names.py]
        I5 --> I6[DuckDB: tablas excel_1, excel_2, etc.]
        I6 --> I7[utils.py: unir_tablas]
        I7 --> I8[catalog.py<br/>Modelo, distribuidora, capacidad y linea]
        I8 --> I9[business.py: business_rules]
        I9 -->|Faltan columnas| R1[Respuesta: formato desconocido]
        I9 -->|Datos aceptados| I10[sabana.py<br/>Llena movimientos, rutas y solicitud]
        I10 --> I11[process_data.py: fill_email_model]
        I11 --> I12[PostgreSQL<br/>save_email_log_init y send_email_request]
        I12 --> I13[prepare_data_cooler<br/>send_email_coolers]
        I13 --> I14[excel_ingestion.py<br/>Genera tres adjuntos]
        I14 --> I15[Graph API responde:<br/>sabana_movimiento, sabana_ruta y solicitud]
    end

    subgraph Respuestas [Flujo de correo de respuesta]
        K --> K1[PostgreSQL: email_reply_validate<br/>Busca solicitud por conversacion y asunto]
        K1 -->|No existe solicitud| Z4[Fin: correo ignorado]
        K1 -->|Existe solicitud| K2[reader.py: detectar_tipo_correo]
        K2 --> L{Direccion detectada}

        L -->|inbound: Cliente a REPARE| M{Tiene Excel?}
        M -->|No| Z5[Fin: no se procesa]
        M -->|Si| M1[Descarga, une y normaliza Excel]
        M1 --> M2[Catalogos y reglas de negocio]
        M2 --> M3[Llena sabanas y solicitud]
        M3 --> M4[PostgreSQL: insert_update_cooler<br/>update_email_request]
        M4 --> M5[Responde con tres Excel actualizados]

        L -->|outbound: REPARE a cliente| N{Contenido}
        N -->|Excel y comando| Z6[Fin: combinacion no permitida]
        N -->|Excel| N1[prepare_cooler_update]
        N1 --> N2[PostgreSQL: update_cooler<br/>y consulta totales/estatus]
        N2 --> N3[Responde con estatus<br/>COMPLETED o IN_PROGRESS]

        L -->|reply_to_bot| O{Palabra reservada}
        O -->|bot.help o bot.ayuda| O1[Responde ayuda]
        O -->|bot.estatus o bot.status| O2[Consulta y responde estatus]
        O -->|bot.cancelar| O3[PostgreSQL: cancela solicitud]
        O -->|bot.finalizar o bot.cerrar| O4[PostgreSQL: completa solicitud]
    end

    R1 --> P[Graph API: respuesta de texto]
    I15 --> Q[Fin: solicitud inicial registrada]
    M5 --> Q1[Fin: solicitud actualizada]
    N3 --> Q2[Fin: estatus informado]
    O1 --> Q3[Fin: comando atendido]
    O2 --> Q3
    O3 --> Q3
    O4 --> Q3
