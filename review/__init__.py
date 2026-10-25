"""Revisión humana y aplicación de cambios pedidos en un mensaje de hilo.

Recibe la ``Decision`` y el ``ThreadCtx`` que devuelve
``classifier.decidir_correo`` (viajan por la llamada; no hay estado global).

* ``cargador(repo)``: cargador del contexto del hilo para
  ``classifier.registrar_cargador_contexto`` (filas de ``cooler_request`` por
  ``request_code``, sin PII).
* ``aplicar(decision, ctx, repo)``: aplica sobre las filas PENDING y separa
  lo que va a revisión.
* ``debe_atender(decision, ctx, email)``: si el mensaje lo atiende este módulo
  en lugar del parser. Solo con ``CLASSIFIER_EXTRACT`` distinto de ``regex``.
* ``atender(decision, ctx, repo, enviar)``: aplica, avisa a REPARE las filas
  que requieren revisión y devuelve la respuesta del hilo.

Reglas de negocio (usuario, 2026-10-25):

* Una fila PENDING se puede agregar, modificar o cancelar desde el hilo.
* Una fila ACCEPTED (con OS) nunca se modifica ni se cancela
  automáticamente: va a revisión con el comentario "requiere revisión".
  CANCELLED y REJECTED tampoco se tocan.
* La revisión le llega a una persona: respuesta en el mismo hilo a REPARE.
"""

from review.aplicador import FilaAplicada, FilaEnRevision, Resultado, aplicar
from review.canal import atender, debe_atender
from review.contexto import cargador

__all__ = [
    "FilaAplicada",
    "FilaEnRevision",
    "Resultado",
    "aplicar",
    "atender",
    "cargador",
    "debe_atender",
]
