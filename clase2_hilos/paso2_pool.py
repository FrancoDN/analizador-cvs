"""pool de hilos.

Probar con distintos valores (PowerShell):
    $env:WORKERS=1; python clase2_hilos/paso2_pool.py
    $env:WORKERS=4; python clase2_hilos/paso2_pool.py
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs
from comun.reporte import guardar_csv, imprimir_top


def analizar_archivo(ruta):
    return {"archivo": ruta.name, **ia.analizar_cv(extraer_texto(ruta))}


def procesar_con_hilos(rutas, workers):
    resultados = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = [pool.submit(analizar_archivo, r) for r in rutas]
        for futuro in as_completed(futuros):  # en el orden en que terminan
            res = futuro.result()
            resultados.append(res)
            print(f"{res['archivo']} -> {res['puntaje']}")
    return resultados


def main():
    ia.chequear_ia()
    rutas = listar_cvs(config.LIMITE_CVS)

    inicio = time.perf_counter()
    resultados = procesar_con_hilos(rutas, config.WORKERS)
    total = time.perf_counter() - inicio

    imprimir_top(resultados)
    guardar_csv(resultados, "clase2_hilos.csv")
    print(f"\n{config.WORKERS} hilos: {total:.1f} s para {len(rutas)} CVs")


if __name__ == "__main__":
    main()
