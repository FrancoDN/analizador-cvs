"""Clase 3 - Paso 1: extraer los 500 PDFs con hilos y con procesos.

Extraer texto es CPU en Python puro. Con hilos el GIL no deja que corran a la
vez; con procesos cada uno tiene su propio intérprete y su propio GIL.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun.pdfs import extraer_texto, listar_cvs


def medir(pool_clase, workers, rutas):
    inicio = time.perf_counter()
    with pool_clase(max_workers=workers) as pool:
        list(pool.map(extraer_texto, rutas, chunksize=10))
    return time.perf_counter() - inicio


def main():
    rutas = listar_cvs()
    print(f"{len(rutas)} CVs, {os.cpu_count()} núcleos\n")

    inicio = time.perf_counter()
    for r in rutas:
        extraer_texto(r)
    base = time.perf_counter() - inicio
    print(f"secuencial    {base:5.2f} s")

    t = medir(ThreadPoolExecutor, 4, rutas)
    print(f"4 hilos       {t:5.2f} s   x{base / t:.2f}")

    for p in sorted({2, 4, os.cpu_count()}):
        t = medir(ProcessPoolExecutor, p, rutas)
        print(f"{p} procesos    {t:5.2f} s   x{base / t:.2f}")


# En Windows cada proceso hijo vuelve a importar este archivo.
# Sin este if, cada hijo crearía su propio pool otra vez.
if __name__ == "__main__":
    main()
