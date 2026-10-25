"""Smoke manual del proveedor haiku con UNA llamada real por operación.

Fuera de pytest. Solo corre si existe ANTHROPIC_API_KEY (gasta centavos):

    ANTHROPIC_API_KEY=... python eval/smoke_haiku.py

Usa texto sintético ya "redactado". No imprime el correo, solo el resultado.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classifier import validate  # noqa: E402
from classifier.contracts import FilaGuardada, ThreadCtx  # noqa: E402
from classifier.providers import haiku  # noqa: E402


def main() -> int:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY no está definida: no se hace ninguna llamada.")
        return 0

    ctx = ThreadCtx(
        etapa="reply",
        customer="danone",
        direccion="inbound",
        filas=(
            FilaGuardada(1, "PENDING", "SF-1001"),
            FilaGuardada(2, "PENDING", "SF-2002"),
        ),
    )
    asunto = "Re: Solicitud de servicio"
    cuerpo = "Cancelen la primera fila por favor, ya no la necesitamos."

    g = haiku.gate(asunto, cuerpo, ctx)
    print("gate:", g, "errores:", validate.validar_gate(g, ctx, 0.7))
    rows = haiku.extract(cuerpo, ctx)
    print("extract:", rows, "errores:", validate.validar_rows(rows, g, ctx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
