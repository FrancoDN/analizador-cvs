"""Clase 3 - Paso 2: cada herramienta para lo suyo.

Fase 1, extraer (CPU): procesos.  Fase 2, consultar la IA (espera): hilos.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs
from comun.reporte import guardar_csv, imprimir_top


def main():
    ia.chequear_ia()
    rutas = listar_cvs(config.LIMITE_CVS)

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=7) as pool:
        textos = list(pool.map(extraer_texto, rutas))
    t1 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=config.WORKERS) as pool:
        analisis = list(pool.map(ia.analizar_cv, textos))
    t2 = time.perf_counter()

    resultados = [{"archivo": r.name, **a} for r, a in zip(rutas, analisis)]
    imprimir_top(resultados)
    guardar_csv(resultados, "clase3_procesos_hilos.csv")

    total = t2 - t0
    print(f"\nExtraer: {t1 - t0:.2f} s   IA: {t2 - t1:.2f} s   Total: {total:.2f} s")
    # Amdahl: si la IA es casi todo el tiempo, acelerar la extracción casi no cambia nada
    print(f"La IA es el {(t2 - t1) / total:.0%} del tiempo")


if __name__ == "__main__":
    main()
