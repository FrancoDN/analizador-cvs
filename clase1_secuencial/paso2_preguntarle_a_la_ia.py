""" Comparen el tiempo de este paso con el del paso 1. Durante casi todo ese
tiempo nuestro programa no hace nada: está esperando la respuesta de Ollama.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs

ia.chequear_ia()
texto = extraer_texto(listar_cvs()[0])

print(f"Modelo: {'SIMULADO' if config.IA_SIMULADA else config.MODELO}")
inicio = time.perf_counter()
resultado = ia.analizar_cv(texto)
duracion = time.perf_counter() - inicio

print(json.dumps(resultado, indent=2, ensure_ascii=False))
print(f"\nLa IA tardó {duracion:.2f} s")
