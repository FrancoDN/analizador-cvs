"""Clase 5 - Paso 2: limitar cuántos pedidos van a la vez.

Con gather solo, 500 CVs serían 500 pedidos juntos a Ollama.
El semáforo deja pasar de a WORKERS; wait_for corta si uno se cuelga.
"""
import asyncio
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs
from comun.reporte import guardar_csv, imprimir_top
from clase5_asyncio.paso1_async import analizar_async


async def analizar_limitado(cliente, semaforo, ruta, texto):
    async with semaforo:  # si ya hay WORKERS en curso, espera acá
        try:
            analisis = await asyncio.wait_for(analizar_async(cliente, texto), config.TIMEOUT_IA)
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            analisis = {"puntaje": 0, "motivo": f"ERROR: {e!r}"}
    print(f"{ruta.name} -> {analisis['puntaje']}")
    return {"archivo": ruta.name, **analisis}


async def procesar_async(rutas, workers):
    textos = [extraer_texto(r) for r in rutas]
    semaforo = asyncio.Semaphore(workers)
    async with httpx.AsyncClient(timeout=None) as cliente:
        tareas = [analizar_limitado(cliente, semaforo, r, t) for r, t in zip(rutas, textos)]
        return await asyncio.gather(*tareas)


def main():
    ia.chequear_ia()
    rutas = listar_cvs(config.LIMITE_CVS)

    inicio = time.perf_counter()
    resultados = asyncio.run(procesar_async(rutas, config.WORKERS))

    imprimir_top(resultados)
    guardar_csv(resultados, "clase5_async.csv")
    print(f"\nSemáforo de {config.WORKERS}: {time.perf_counter() - inicio:.1f} s")


if __name__ == "__main__":
    main()
