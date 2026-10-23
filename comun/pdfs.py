"""Extracción de texto de los PDFs.

pypdf está escrito en Python puro: parsear un PDF es trabajo de CPU
y mientras corre tiene el GIL tomado. Esto importa en la clase 3.
"""
import re
from pathlib import Path

from pypdf import PdfReader

import config


def listar_cvs(limite=None):
    """Devuelve las rutas de los CVs ordenadas (siempre en el mismo orden)."""
    rutas = sorted(config.CARPETA_CVS.glob("*.pdf"))
    if not rutas:
        raise SystemExit("No hay CVs. Corré primero: python datos/generar_cvs.py")
    return rutas[:limite] if limite else rutas


def extraer_texto(ruta: Path) -> str:
    lector = PdfReader(ruta)
    texto = "\n".join(pagina.extract_text() or "" for pagina in lector.pages)
    return limpiar(texto)


def limpiar(texto: str) -> str:
    # saca espacios repetidos y líneas vacías que deja la extracción
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n\s*\n+", "\n", texto)
    return texto.strip()
