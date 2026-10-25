from config.config_general.palabras_reser import palabras_reservadas


async def detectar_tipo_correo(client, user_id, mail_id, email) -> dict:

    resultado = {
        "tiene_excel": False,
        "tiene_palabra_reservada": False,
        "palabra": None,
        "descripcion": None,
    }

    texto = (
        f"{getattr(getattr(email, 'unique_body', None), 'content', '')}"
    ).lower()

    for palabra, descripcion in palabras_reservadas.items():

        palabra = palabra.lower()

        if palabra in texto:
            resultado["tiene_palabra_reservada"] = True
            resultado["palabra"] = palabra
            resultado["descripcion"] = descripcion
            break

    attachments = await (
        client.users
        .by_user_id(user_id)
        .messages
        .by_message_id(mail_id)
        .attachments
        .get()
    )

    for attachment in attachments.value or []:
        nombre = (attachment.name or "").lower()

        if nombre.endswith((".xlsx", ".xls", ".xlsm")):
            resultado["tiene_excel"] = True
            break

    return resultado
