"""Clase 4 - Paso 2: pipeline de tres etapas.

  procesos (extraer) --> cola --> hilos (IA) --> cola --> 1 hilo (escribe el CSV)

La IA arranca con el primer PDF y el CSV se va escribiendo mientras corre.
"""
import csv
import os
import queue
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs
from comun.reporte import COLUMNAS

FIN = None


def extraer(rutas, cola_textos, n_ia):
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        futuros = {pool.submit(extraer_texto, r): r for r in rutas}
        for f in as_completed(futuros):
            cola_textos.put((futuros[f].name, f.result()))
    for _ in range(n_ia):
        cola_textos.put(FIN)


def analizar(cola_textos, cola_resultados):
    while (item := cola_textos.get()) is not FIN:
        nombre, texto = item
        try:
            res = {"archivo": nombre, **ia.analizar_cv(texto)}
        except Exception as e:  # un CV que falla no frena al resto
            res = {"archivo": nombre, "puntaje": 0, "motivo": f"ERROR: {e}"}
        cola_resultados.put(res)


def escribir(cola_resultados, ruta_csv):
    # único hilo que toca el archivo: no necesita lock
    with open(ruta_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        while (res := cola_resultados.get()) is not FIN:
            w.writerow({**res, "tecnologias": ", ".join(res.get("tecnologias", []))})
            f.flush()
            print(f"guardado {res['archivo']} -> {res['puntaje']}")


def correr_pipeline(rutas, workers, ruta_csv):
    cola_textos = queue.Queue(maxsize=10)
    cola_resultados = queue.Queue()

    extractor = threading.Thread(target=extraer, args=(rutas, cola_textos, workers))
    analistas = [threading.Thread(target=analizar, args=(cola_textos, cola_resultados))
                 for _ in range(workers)]
    escritor = threading.Thread(target=escribir, args=(cola_resultados, ruta_csv))

    for h in [extractor, *analistas, escritor]:
        h.start()

    # cierre en orden: primero el que produce, al final el que escribe
    extractor.join()
    for h in analistas:
        h.join()
    cola_resultados.put(FIN)
    escritor.join()


def main():
    ia.chequear_ia()
    config.CARPETA_RESULTADOS.mkdir(exist_ok=True)
    ruta_csv = config.CARPETA_RESULTADOS / "clase4_pipeline.csv"

    inicio = time.perf_counter()
    correr_pipeline(listar_cvs(20), config.WORKERS, ruta_csv)
    print(f"\nListo en {time.perf_counter() - inicio:.1f} s -> {ruta_csv}")


if __name__ == "__main__":
    main()
