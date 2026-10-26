"""Parser de Torrey -- cliente.torrey@.

Solo garantías (con Excel "Lay Out Repare" y factura PDF), consultas de
estatus de OS y quejas o seguimientos. Mismo flujo que Imbera
(parsers/imbera_parse/flujo.py); lo propio de Torrey está en
parsers/torrey_parse/ y config/customers/torrey/reglas_torrey.py:
  * toda solicitud con Excel se MARCA como garantía (no se valida aquí);
  * la respuesta avisa si falta la factura PDF;
  * una máquina o fábrica de hielo se crea para el cliente IMBERA, pero se
    contesta en el hilo de Torrey (la respuesta va al correo recibido).
"""

from bot.perfiles import perfil_torrey
from config.customers.torrey.reglas_torrey import (
    CLIENTE_OS,
    CUSTOMER,
    EXIGE_FACTURA_PDF,
    SIEMPRE_GARANTIA,
)
from parsers.imbera_parse.flujo import LAYOUT_INIT, LAYOUT_REPLY
from parsers.imbera_parse.perfil import PerfilLayout
from parsers.torrey_parse.hielo import cliente_os_hielo

PERFIL_TORREY = PerfilLayout(
    customer=CUSTOMER,
    etiqueta="TORREY",
    cliente_os=CLIENTE_OS,
    siempre_garantia=SIEMPRE_GARANTIA,
    exige_factura_pdf=EXIGE_FACTURA_PDF,
    cliente_os_fila=cliente_os_hielo,
)


class TORREY_INIT(LAYOUT_INIT):
    perfil = PERFIL_TORREY


class TORREY_REPLY(LAYOUT_REPLY):
    init_cls = TORREY_INIT
    perfil_bot = staticmethod(perfil_torrey)
