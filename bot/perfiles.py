"""Perfil de cada cliente para bot/commands.py. Cada diferencia de hoy se
conserva tal cual, incluidos los textos de log (el de bot.estatus de
Danone/Penafiel dice "cancelar": viene así del código original)."""

from bot.commands import PerfilBot

_LOGS_HILO = {
    "global": "[ERROR] No se logró generar el estado global: {e}",
    "estatus": "No se logro cancelar la solicitud {e}",
    "cancelar": "No se logro cancelar la solicitud {e}",
    "finalizar": "No se logro completar la solicitud {e}",
}


def _logs_folio(etiqueta):
    return {
        "global": f"[{etiqueta}][BOT][ERROR] No se logró generar el estado global: {{e}}",
        "estatus": f"[{etiqueta}][BOT][ERROR] No se logró consultar el estatus de {{request_code}}: {{e}}",
        "cancelar": f"[{etiqueta}][BOT][ERROR] No se logró cancelar {{request_code}}: {{e}}",
        "finalizar": f"[{etiqueta}][BOT][ERROR] No se logró finalizar {{request_code}}: {{e}}",
    }


def _perfil_hilo(db, msj, process):
    """Danone y Penafiel: todo sale de su DB_POSTGRE; estatus vacío -> msj_fail."""
    return PerfilBot(
        msj=msj,
        repo=db,
        estatus=lambda request_code: db.email_request_bot_status(request_code),
        datos_global=lambda: db.get_email_request_global(),
        archivo_global=lambda data: process.process_email_request_global(data),
        estatus_vacio=lambda solicitud: msj.msj_fail(),
        logs=_LOGS_HILO,
        lectura_estricta=True,
    )


def perfil_danone(db, msj, process):
    return _perfil_hilo(db, msj, process)


def perfil_penafiel(db, msj, process):
    return _perfil_hilo(db, msj, process)


def perfil_kof(db, msj, process):
    """KOF: mismo perfil por hilo que Danone/Penafiel (repository.gen)."""
    return _perfil_hilo(db, msj, process)


def perfil_holanda(db, db_holanda, msj, process):
    """Estatus y global desde DB_HOLANDA; estatus vacío -> msj_folio_requerido(folio)."""
    return PerfilBot(
        msj=msj,
        repo=db,
        estatus=lambda request_code: db_holanda.bot_status(request_code),
        datos_global=lambda: db_holanda.global_status(),
        archivo_global=lambda data: process.process_email_request_global(data),
        estatus_vacio=lambda solicitud: msj.msj_folio_requerido(solicitud.folio),
        logs=_logs_folio("HOLANDA"),
    )


def perfil_heineken(db, db_heineken, msj, process):
    """Estatus y global desde DB_HEINEKEN; estatus vacío ->
    msj_folio_requerido(request_code) (en D2D no hay folio)."""
    return PerfilBot(
        msj=msj,
        repo=db,
        estatus=lambda request_code: db_heineken.bot_status(request_code),
        datos_global=lambda: db_heineken.global_status(),
        archivo_global=lambda data: process.process_email_request_global(data),
        estatus_vacio=lambda solicitud: msj.msj_folio_requerido(solicitud.request_code),
        logs=_logs_folio("HEINEKEN"),
    )
