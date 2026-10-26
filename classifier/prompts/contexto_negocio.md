## Contexto de negocio

Reglas del dominio. Aplican junto con las instrucciones y ejemplos de esta tarea; si chocan con un ejemplo, mandan estas reglas.

Estructura
- Un hilo es una OS padre; cada línea de la solicitud es una OS hija. Casi todos los pedidos llegan con un Excel cuyo formato cambia; el resto, en texto plano.
- Ruta = reparación. Movimiento = instalación, retiro, reubicación o traslado (también cambios y préstamos).
- Cuenta no es cliente: un buzón (sobre todo el de Imbera) recibe de varios sub-clientes. El cliente real se lee del contenido, no del buzón.

Qué NO es una OS (no_os)
- Seguimientos, consultas de estatus o informes, saludos, felicitaciones, borradores, correos automáticos o de "no responder", avisos de reunión y rebotes del servidor ("no se puede entregar").
- Consultar el estatus de un folio queda fuera de alcance: es tipo estatus, nunca nueva_solicitud.
- Una respuesta de REPARE con las OS generadas adjuntas es un cierre: nunca es una solicitud nueva.

Hilos largos (Danone y Peñafiel, cerca del 30% del volumen)
- Un mismo hilo se reutiliza. Casos típicos: inventario no disponible, formato incompleto, serie inexistente, tipo de servicio equivocado.
- "Me falta uno más, mételo a la lista" es agregar_filas. Una serie corregida y reenviada es modificar_filas.
- Las filas se comparan por número de serie.

Holanda
- Usa un solo hilo para todo y traza por número de caso. Cada "Caso: NNNNNN <falla>" nuevo en el cuerpo es una solicitud nueva (nueva_solicitud), aunque venga como respuesta. Solo es ruta.

Texto plano que sí es OS
- KOF y Holanda mandan solicitudes en texto plano que sí son OS.
- KOF "venta de material" (extensión, charolas, parrillas) es ruta, no falla. KOF "Cambio de Equipo" es instalación más retiro.

Reglas por cliente
- Heineken: "reparación mercado" necesita la falla para clasificarse. "Instalación de mobiliario" se genera como retiro; lo mismo la "instalación especial" de Lala.
- Danone: "TIPO DE SERVICIO" con RETIRO, INSTALACIÓN, REPARACIÓN o REUBICACION. Series en "# SERIE DEL FABRICANTE" y "# SERIE DANONE/BNF"; la de fabricante suele venir "NA" en los retiros.
- Peñafiel: "Solicitud de servicio", "No SERIE", "FOLIO NET.".
- KOF: "Folio (.Net)" y "Tipo de Movimiento"; Cobertura, Equipo Adicional y Cambio de Equipo son instalación.
- Torrey: solo garantías (Lay Out Repare).
- Lala: el tipo va en "Observaciones"; solo retiros.

Extracción
- Extrae solo lo que el cliente escribió. No inventes filas que genera el sistema: la fila espejo "M" de Holanda, el desdoble de una reubicación ni las series genéricas MOB/ENF de Heineken.
- No descartes filas por reglas de validación de una etapa posterior (garantías, congeladores, vending): si el cliente las escribió, se extraen.

Cancelación
- Para clientes, usa el criterio de las instrucciones y ejemplos. Solo el comando bot.cancelar está definido como regla fija.
