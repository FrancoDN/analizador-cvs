"""Guardar e imprimir resultados. Nada de concurrencia acá."""
import csv
import time
from contextlib import contextmanager

import config

COLUMNAS = ["archivo", "nombre", "puntaje", "cumple_excluyentes", "motivo",
            "anios_experiencia", "tecnologias", "nivel_ingles", "resumen"]


def guardar_csv(resultados, nombre_archivo):
    config.CARPETA_RESULTADOS.mkdir(exist_ok=True)
    ruta = config.CARPETA_RESULTADOS / nombre_archivo
    ordenados = sorted(resultados, key=lambda r: r["puntaje"], reverse=True)
    # utf-8-sig para que Excel en Windows muestre bien los acentos
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore")
        escritor.writeheader()
        for r in ordenados:
            escritor.writerow({**r, "tecnologias": ", ".join(r.get("tecnologias", []))})
    return ruta


def imprimir_top(resultados, n=5):
    print(f"\nTop {n}:")
    for r in sorted(resultados, key=lambda r: r["puntaje"], reverse=True)[:n]:
        print(f"  {r['puntaje']:>3}  {r['nombre']:<28} {r['archivo']}")


@contextmanager
def cronometro(etiqueta, tiempos=None):
    """with cronometro("extraer"): ...  -> imprime cuánto tardó el bloque."""
    inicio = time.perf_counter()
    yield
    duracion = time.perf_counter() - inicio
    if tiempos is not None:
        tiempos[etiqueta] = duracion
    print(f"[{etiqueta}] {duracion:.2f} s")
