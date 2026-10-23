# Trabajo práctico: Analizador de CVs concurrente

Partiendo del código visto en clase, cada grupo elige **dos** extensiones de la lista
(al menos una de la parte A) y las implementa.

## Parte A - Concurrencia

1. **Generador en paralelo.** `datos/generar_cvs.py` tarda varios segundos en crear los
   500 PDFs. Paralelizarlo con procesos. Cuidado: cada CV usa números al azar; el resultado
   tiene que ser idéntico al de la versión secuencial (pista: una semilla por CV).
2. **Cancelación limpia.** En el pipeline de la clase 4, que Ctrl+C detenga todo de forma
   ordenada usando `threading.Event`: dejar de encolar, terminar los pedidos en curso,
   cerrar el CSV con lo que haya.
3. **Caché de resultados.** No volver a mandarle a la IA un CV que ya se analizó
   (identificarlo por el hash del archivo). La caché la comparten varios hilos: justificar
   cómo se evita la condición de carrera.
4. **Reintentos.** En `clase5_asyncio/paso2_semaforo.py`, reintentar hasta 3 veces un
   pedido que falla, esperando cada vez el doble (backoff exponencial). La espera no
   tiene que ocupar un lugar del semáforo.
5. **Prioridades.** Usar `queue.PriorityQueue` para que los CVs que mencionan "Python" se
   analicen primero.

## Parte B - Medición

6. **Curva de speedup.** Con el modelo real, medir el tiempo para 1, 2, 4, 8 y 16 workers
   con dos valores distintos de `OLLAMA_NUM_PARALLEL`. Graficar y explicar dónde se
   estanca y por qué.
7. **Otro dominio.** Adaptar el pipeline a otro problema (reclamos de clientes, facturas,
   papers) cambiando solo `comun/ia.py` y la fuente de datos. Medir y comparar.

## Entrega

- Código funcionando (que corra con `IA_SIMULADA=1` en cualquier máquina).
- Informe corto (2 a 4 páginas): qué hicieron, qué primitiva de concurrencia usaron y por
  qué, tabla de tiempos y conclusiones.

## Criterios de evaluación

- Corrección: sin condiciones de carrera ni bloqueos (deadlocks), cierre ordenado.
- Elección justificada de hilos / procesos / asyncio según el tipo de trabajo.
- Mediciones reproducibles y bien interpretadas.
- Código legible.
