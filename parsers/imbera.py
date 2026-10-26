"""Parser de Imbera -- cliente.imbera@ (buzón MULTI-CLIENTE).

El cliente real (Jumex, laboratorios, distribuidores, comercializadores o
Imbera mismo) se lee del contenido del correo, no de la cuenta. Formato
"Lay Out Repare", compartido con Torrey: todo el flujo vive en
parsers/imbera_parse/ (ver flujo.py); aquí solo se elige el perfil.
Reglas y dudas abiertas: config/customers/imbera/reglas_imbera.py.
"""

from bot.perfiles import perfil_imbera
from config.customers.imbera.reglas_imbera import CLIENTE_OS, CUSTOMER
from parsers.imbera_parse.flujo import LAYOUT_INIT, LAYOUT_REPLY
from parsers.imbera_parse.perfil import PerfilLayout

PERFIL_IMBERA = PerfilLayout(
    customer=CUSTOMER,
    etiqueta="IMBERA",
    cliente_os=CLIENTE_OS,
)


class IMBERA_INIT(LAYOUT_INIT):
    perfil = PERFIL_IMBERA


class IMBERA_REPLY(LAYOUT_REPLY):
    init_cls = IMBERA_INIT
    perfil_bot = staticmethod(perfil_imbera)
