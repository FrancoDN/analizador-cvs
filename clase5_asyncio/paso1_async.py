"""Clase 5 - Paso 1: lo mismo que con hilos, pero con asyncio.

Un solo hilo. En cada `await` la corrutina cede el turno mientras espera.
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
from comun.reporte import imprimir_top


async def analizar_async(cliente, texto):
    if config.IA_SIMULADA:
        await asyncio.sleep(ia.demora_simulada())  # time.sleep acá bloquearía todo
        return ia.respuesta_simulada(texto)
    resp = await cliente.post(f"{config.OLLAMA_URL}/api/chat", json=ia.armar_pedido(texto))
    resp.raise_for_status()
    return ia.interpretar_respuesta(resp.json())


async def main():
    ia.chequear_ia()
    rutas = listar_cvs(config.LIMITE_CVS)
    textos = [extraer_texto(r) for r in rutas]

    inicio = time.perf_counter()
    async with httpx.AsyncClient(timeout=config.TIMEOUT_IA) as cliente:
        # gather lanza todas las corrutinas a la vez y espera a que terminen
        analisis = await asyncio.gather(*(analizar_async(cliente, t) for t in textos))

    imprimir_top([{"archivo": r.name, **a} for r, a in zip(rutas, analisis)])
    print(f"\n{len(rutas)} pedidos a la vez: {time.perf_counter() - inicio:.1f} s")


if __name__ == "__main__":
    asyncio.run(main())
