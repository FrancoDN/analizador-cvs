"""todos los CVs, uno detrás de otro.
Es la versión de referencia: todo lo que hagamos después se compara contra esto.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # para importar config y comun/

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs
from comun.reporte import guardar_csv, imprimir_top


def procesar_secuencial(rutas):
    resultados = []
    t_cpu = t_ia = 0.0

    for ruta in rutas:
        t0 = time.perf_counter()
        texto = extraer_texto(ruta)
        t1 = time.perf_counter()
        analisis = ia.analizar_cv(texto)
        t2 = time.perf_counter()

        t_cpu += t1 - t0   # trabajo de CPU
        t_ia += t2 - t1    # esperando a la IA
        resultados.append({"archivo": ruta.name, **analisis})
        print(f"{ruta.name} -> {analisis['puntaje']}")

    return resultados, t_cpu, t_ia


def main():
    ia.chequear_ia()
    rutas = listar_cvs(config.LIMITE_CVS)

    inicio = time.perf_counter()
    resultados, t_cpu, t_ia = procesar_secuencial(rutas)
    total = time.perf_counter() - inicio

    imprimir_top(resultados)
    guardar_csv(resultados, "clase1_secuencial.csv")

    print(f"\nTotal: {total:.1f} s para {len(rutas)} CVs")
    print(f"  extrayendo PDFs:   {t_cpu:6.2f} s ({t_cpu / total:.0%})")
    print(f"  esperando la IA:   {t_ia:6.2f} s ({t_ia / total:.0%})")
    print(f"Los 500 CVs tardarían ~{total / len(rutas) * 500 / 60:.0f} minutos")


if __name__ == "__main__":
    main()
