"""un hilo por CV.

Mientras un hilo espera la respuesta de la IA, otro puede mandar su pedido.
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun import ia
from comun.pdfs import extraer_texto, listar_cvs
from comun.reporte import imprimir_top

INICIO = time.perf_counter()


def trabajar(ruta, resultados, i):
    print(f"{time.perf_counter() - INICIO:5.1f}s  empieza {ruta.name}")
    analisis = ia.analizar_cv(extraer_texto(ruta))
    resultados[i] = {"archivo": ruta.name, **analisis}  # cada hilo usa su propio casillero
    print(f"{time.perf_counter() - INICIO:5.1f}s  termina {ruta.name}")


def main():
    ia.chequear_ia()
    rutas = listar_cvs(4)
    resultados = [None] * len(rutas)

    hilos = [threading.Thread(target=trabajar, args=(r, resultados, i))
             for i, r in enumerate(rutas)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()  # esperamos a que terminen todos

    imprimir_top(resultados)
    print(f"\nTotal: {time.perf_counter() - INICIO:.1f} s")


if __name__ == "__main__":
    main()
