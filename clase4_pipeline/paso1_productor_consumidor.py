"""Clase 4 - Paso 1: productor / consumidor con una cola.

  productor --> cola --> consumidores x N

queue.Queue ya está sincronizada: put y get son seguros entre hilos.
"""
import queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs
from comun.reporte import imprimir_top

FIN = None  # centinela: "no hay más trabajo"


def productor(rutas, cola, n_consumidores):
    for ruta in rutas:
        cola.put((ruta.name, extraer_texto(ruta)))  # espera si la cola está llena
        print(f"encolé {ruta.name} (en cola: {cola.qsize()})")
    for _ in range(n_consumidores):
        cola.put(FIN)  # un centinela por consumidor


def consumidor(cola, resultados):
    while True:
        item = cola.get()  # espera si la cola está vacía
        if item is FIN:
            break
        nombre, texto = item
        resultados.put({"archivo": nombre, **ia.analizar_cv(texto)})
        print(f"    analicé {nombre}")


def main():
    ia.chequear_ia()
    rutas = listar_cvs(20)
    cola = queue.Queue(maxsize=3)
    resultados = queue.Queue()

    hilos = [threading.Thread(target=productor, args=(rutas, cola, config.WORKERS))]
    hilos += [threading.Thread(target=consumidor, args=(cola, resultados))
              for _ in range(config.WORKERS)]

    inicio = time.perf_counter()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    imprimir_top(list(resultados.queue))
    print(f"\nTotal: {time.perf_counter() - inicio:.1f} s")


if __name__ == "__main__":
    main()
