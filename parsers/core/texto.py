import re
import unicodedata

from bs4 import BeautifulSoup

from config.config_general.stopwords import STOPWORDS


def eliminar_stopwords(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", " ", texto)
    palabras = texto.split()
    palabras = [p for p in palabras if p not in STOPWORDS]
    return " ".join(palabras)


def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""

    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def convertir_html_a_texto(html: str) -> str:
    texto = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    texto = normalizar_texto(texto)
    texto = eliminar_stopwords(texto)
    return texto
