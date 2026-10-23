"""Clase 5 - Paso 3: todas las versiones con los mismos CVs.

En PowerShell:
    $env:IA_SIMULADA=1; $env:LIMITE=40; python clase5_asyncio/paso3_benchmark.py
"""
import asyncio
import contextlib
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import listar_cvs
from clase1_secuencial.paso3_todos_secuencial import procesar_secuencial
from clase2_hilos.paso2_pool import procesar_con_hilos
from clase4_pipeline.paso2_pipeline import correr_pipeline
from clase5_asyncio.paso2_semaforo import procesar_async


def main():
    ia.chequear_ia()
    rutas = listar_cvs(config.LIMITE_CVS)
    w = config.WORKERS
    config.CARPETA_RESULTADOS.mkdir(exist_ok=True)
    csv_tmp = config.CARPETA_RESULTADOS / "benchmark_pipeline.csv"

    versiones = {
        "secuencial": lambda: procesar_secuencial(rutas),
        f"{w} hilos": lambda: procesar_con_hilos(rutas, w),
        "pipeline": lambda: correr_pipeline(rutas, w, csv_tmp),
        "asyncio": lambda: asyncio.run(procesar_async(rutas, w)),
    }

    print(f"{len(rutas)} CVs, {w} workers\n")
    base = None
    for nombre, funcion in versiones.items():
        with contextlib.redirect_stdout(io.StringIO()):  # silencia los prints de cada versión
            inicio = time.perf_counter()
            funcion()
            t = time.perf_counter() - inicio
        base = base or t
        print(f"{nombre:<12} {t:6.1f} s   x{base / t:.1f}")


if __name__ == "__main__":
    main()
