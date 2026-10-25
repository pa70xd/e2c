"""Despachador único de los comandos bot.* (antes copiado en los parsers de
Danone, Penafiel, Holanda y Heineken).

Lo que cambia por cliente vive en un PerfilBot (ver bot/perfiles.py): qué
métodos del repositorio se llaman, qué mensaje se usa cuando el estatus viene
vacío, cómo se resuelve la solicitud y los textos de log. El flujo es el mismo
para todos:

  1. Sin palabra reservada -> None.
  2. bot.help / bot.ayuda   -> msj_ayuda (no necesita solicitud).
  3. bot.global             -> datos globales + Excel (no necesita solicitud).
  4. Cualquier otra palabra -> msj_comando_no_reconocido. Hoy es inalcanzable:
     el reader solo detecta palabras de palabras_reservadas.
  5. Se resuelve la solicitud (hilo o folio). Si falla, se responde lo que
     devuelva el resolvedor.
  6. bot.estatus / bot.status, bot.cancelar, bot.finalizar / bot.cerrar.

Los errores del repositorio se imprimen y se responde igual (éxito aunque el
UPDATE no haya afectado filas): es el comportamiento actual, no se corrige aquí.
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

AYUDA = ("bot.help", "bot.ayuda")
GLOBAL = "bot.global"
ESTATUS = ("bot.estatus", "bot.status")
CANCELAR = "bot.cancelar"
FINALIZAR = ("bot.finalizar", "bot.cerrar")
CON_SOLICITUD = ESTATUS + (CANCELAR,) + FINALIZAR


@dataclass(frozen=True)
class Solicitud:
    """Solicitud sobre la que actúa el comando. `folio` es el texto
    REPARE_xxx que escribió el operador, si se resolvió por folio."""

    request_code: str
    folio: str | None = None


# Devuelve la Solicitud o, si no se pudo resolver, la respuesta a enviar.
Resolvedor = Callable[[], Awaitable["Solicitud | dict"]]


@dataclass(frozen=True)
class PerfilBot:
    msj: Any
    # DB_POSTGRE compartido: cancel_pending_coolers, cancel_email_request,
    # complete_email_request.
    repo: Any
    estatus: Callable[[str], Any]
    datos_global: Callable[[], Any]
    archivo_global: Callable[[Any], Any]
    # Mensaje cuando el estatus viene vacío o falla.
    estatus_vacio: Callable[[Solicitud], str]
    # Plantillas de log con {e} y {request_code}. Llaves: global, estatus,
    # cancelar, finalizar.
    logs: Mapping[str, str]
    # Danone/Penafiel indexan result_type (KeyError si falta la llave);
    # Holanda/Heineken usan .get().
    lectura_estricta: bool = False


def respuesta(mensaje, attachments=None):
    return {"mensaje": mensaje, "attachments": attachments}


def solicitud_fija(request_code) -> Resolvedor:
    """Solicitud ya resuelta por hilo (Danone, Penafiel, Heineken D2D)."""

    async def resolver():
        return Solicitud(request_code)

    return resolver


def resolver_por_folio(buscar_folio, get_request, msj) -> Resolvedor:
    """Folio REPARE_xxx -> get_request(folio). Sin folio, o con folio que no
    existe, responde msj_folio_requerido (Holanda, Heineken)."""

    async def resolver():
        folio = await buscar_folio()
        if not folio:
            return respuesta(msj.msj_folio_requerido())
        solicitud = get_request(folio)
        if not solicitud:
            return respuesta(msj.msj_folio_requerido(folio))
        return Solicitud(solicitud["request_code"], folio)

    return resolver


def _log(perfil, llave, e, request_code=None):
    print(perfil.logs[llave].format(e=e, request_code=request_code))


async def ejecutar(perfil: PerfilBot, result_type, resolver: Resolvedor):
    if perfil.lectura_estricta:
        if not result_type["tiene_palabra_reservada"]:
            return None
        palabra = result_type["palabra"].lower()
    else:
        if not result_type.get("tiene_palabra_reservada"):
            return None
        palabra = (result_type.get("palabra") or "").lower()

    msj = perfil.msj

    if palabra in AYUDA:
        return respuesta(msj.msj_ayuda())

    if palabra == GLOBAL:
        archivo = None
        try:
            data = perfil.datos_global()
            if data:
                archivo = perfil.archivo_global(data)
        except Exception as e:
            _log(perfil, "global", e)
        return respuesta(msj.msj_global(), [archivo] if archivo else None)

    if palabra not in CON_SOLICITUD:
        return respuesta(msj.msj_comando_no_reconocido())

    solicitud = await resolver()
    if not isinstance(solicitud, Solicitud):
        return solicitud
    request_code = solicitud.request_code

    if palabra in ESTATUS:
        data = None
        try:
            data = perfil.estatus(request_code)
        except Exception as e:
            _log(perfil, "estatus", e, request_code)
        if not data:
            return respuesta(perfil.estatus_vacio(solicitud))
        return respuesta(msj.msj_status_solicitud(data))

    if palabra == CANCELAR:
        # También se cancelan los coolers PENDING, para que un outbound
        # posterior no reviva la solicitud.
        try:
            perfil.repo.cancel_pending_coolers(request_code)
            perfil.repo.cancel_email_request(request_code)
        except Exception as e:
            _log(perfil, "cancelar", e, request_code)
        return respuesta(msj.msj_cancelar(request_code))

    # bot.finalizar / bot.cerrar
    try:
        perfil.repo.complete_email_request(request_code)
    except Exception as e:
        _log(perfil, "finalizar", e, request_code)
    return respuesta(msj.msj_finalizar(request_code))
