"""
Antes de pensar en concurrencia, entendamos qué hace el programa con un solo
archivo y cuánto tarda.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # para importar config y comun/

from comun.pdfs import extraer_texto, listar_cvs

ruta = listar_cvs()[0]

inicio = time.perf_counter()
texto = extraer_texto(ruta)
duracion = time.perf_counter() - inicio

print(texto[:1200])
print("...")
print(f"\n{ruta.name}: {len(texto)} caracteres extraídos en {duracion * 1000:.1f} ms")
