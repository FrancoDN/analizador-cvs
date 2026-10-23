"""condición de carrera.

Varios hilos suman en el mismo contador. Correrlo, ver que no da 500,
cambiar USAR_LOCK a True y correrlo de nuevo.
"""
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun.pdfs import extraer_texto, listar_cvs

USAR_LOCK = True

contador = 0
lock = threading.Lock()


def sumar_uno():
    global contador
    actual = contador
    time.sleep(0)  # cede el turno a otro hilo: agranda la ventana del error
    contador = actual + 1


def procesar(ruta):
    extraer_texto(ruta)
    if USAR_LOCK:
        with lock:
            sumar_uno()
    else:
        sumar_uno()


def main():
    rutas = listar_cvs()  # los 500, sin IA: así corre en segundos
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(procesar, rutas))

    print(f"Lock: {USAR_LOCK}")
    print(f"Contados: {contador}  Reales: {len(rutas)}")


if __name__ == "__main__":
    main()
