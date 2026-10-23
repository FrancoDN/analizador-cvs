# Analizador de CVs con IA local

Proyecto integrador de Programación Avanzada: paralelismo y concurrencia en Python
aplicados a un problema real.

## El problema

RRHH abre una búsqueda de "Desarrollador/a Backend Python Junior" y recibe 500 CVs en PDF.
Leerlos a mano lleva días. Armamos un programa que:

1. extrae el texto de cada PDF,
2. le pide a un modelo de lenguaje **local** que estructure los datos (nombre, años de
   experiencia, tecnologías, inglés),
3. calcula un puntaje con reglas explícitas y arma un ranking en CSV.

¿Por qué IA local? Los CVs son datos personales: con Ollama no salen de la máquina, no hay
API key, no hay costo por consulta.

¿Por qué sirve para la materia? Porque tiene las dos caras de la concurrencia:

| Etapa | Tipo de trabajo | Herramienta |
|---|---|---|
| Extraer texto del PDF | CPU (Python puro, tiene el GIL) | procesos |
| Consultar al modelo | espera (I/O de red) | hilos o asyncio |

## Instalación (Windows)

```powershell
cd analizador-cvs
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python datos/generar_cvs.py        # genera 500 CVs ficticios en datos/cvs/
```

### Ollama (el modelo local)

1. Descargar e instalar desde https://ollama.com/download
2. Bajar el modelo (una sola vez, ~1 GB):
   ```powershell
   ollama pull qwen2.5:1.5b
   ```
3. Para que Ollama atienda varios pedidos en paralelo (clase 2 en adelante):
   ```powershell
   setx OLLAMA_NUM_PARALLEL 4
   ```
   y reiniciar Ollama (cerrarlo desde el ícono de la bandeja y volver a abrirlo).

Si la máquina da para más, un modelo más grande extrae mejor: `ollama pull qwen2.5:3b`
y después `$env:MODELO="qwen2.5:3b"`.

### Sin Ollama

Todo funciona en modo simulado: misma interfaz, respuestas por expresiones regulares y una
demora parecida a la de un modelo real. Sirve para practicar la concurrencia en cualquier
máquina.

```powershell
$env:IA_SIMULADA=1
```

## Variables de entorno

Se setean en PowerShell con `$env:NOMBRE=valor` y duran hasta cerrar la terminal
(en cmd: `set NOMBRE=valor`; en Linux/Mac: `NOMBRE=valor python ...`).

| Variable | Default | Para qué |
|---|---|---|
| `IA_SIMULADA` | 0 | 1 = no usa Ollama |
| `LIMITE` | 10 | cuántos CVs se mandan a la IA |
| `WORKERS` | 4 | hilos / tareas concurrentes contra la IA |
| `MODELO` | qwen2.5:1.5b | modelo de Ollama |
| `OLLAMA_URL` | http://127.0.0.1:11434 | dónde corre Ollama |

## Recorrido por clase

Cada clase está pensada para una hora: unos 10 minutos de idea, 40 de práctica
corriendo los pasos en orden y 10 de cierre. Todo se corre desde la carpeta raíz,
por ejemplo `python clase1_secuencial/paso3_todos_secuencial.py`.

| Clase | Pasos | Tema |
|---|---|---|
| 1 | `paso1_leer_un_cv`, `paso2_preguntarle_a_la_ia`, `paso3_todos_secuencial` | Versión secuencial y dónde se va el tiempo |
| 2 | `paso1_hilos`, `paso2_pool`, `paso3_carrera_y_lock` | Hilos, pool, condición de carrera y Lock |
| 3 | `paso1_hilos_vs_procesos`, `paso2_procesos_y_hilos` | GIL, procesos, speedup y Amdahl |
| 4 | `paso1_productor_consumidor`, `paso2_pipeline` | Colas y pipeline de tres etapas |
| 5 | `paso1_async`, `paso2_semaforo`, `paso3_benchmark` | asyncio, semáforo y comparación final |

## Interfaz gráfica

```powershell
python gui/servidor.py
```

Abre http://localhost:8000 en el navegador. Desde ahí se puede:

- correr en secuencial o con N hilos y ver qué hace cada hilo en una línea de tiempo,
- ver el ranking a medida que llegan los resultados,
- abrir un CV y comparar el texto del PDF con lo que respondió el modelo,
- corregir lo que extrajo la IA y guardarlo como ejemplo (queda en `datos/ejemplos.json`),
- cambiar los excluyentes y deseables y volver a puntuar,
- comparar corridas en el historial.

Sobre los ejemplos: el modelo no se reentrena. Las últimas 2 correcciones se agregan al
pedido como casos ya resueltos (few-shot), y el modelo las usa como referencia. Cada
ejemplo hace el pedido más largo, así que cada consulta tarda un poco más.

Corre con la misma configuración que el resto (`$env:IA_SIMULADA=1`, `$env:MODELO`, etc.)
y no necesita instalar nada más.

## Estructura

```
config.py            configuración (modelo, búsqueda, límites)
comun/pdfs.py        extracción de texto (pypdf)
comun/ia.py          cliente de Ollama + reglas de puntaje + modo simulado
comun/reporte.py     CSV, top 5, cronómetro
gui/                 interfaz gráfica (servidor local + página)
datos/generar_cvs.py genera los CVs de prueba (datos inventados, semilla fija)
resultados/          acá quedan los CSV
TP_consigna.md       trabajo práctico para los alumnos
```

## Nota sobre el puntaje

El modelo **no** decide quién es mejor candidato: solo extrae datos. El puntaje sale de
`puntuar()` en `comun/ia.py`, con reglas que cualquiera puede leer y discutir. Con modelos
chicos la extracción tiene errores (sobre todo en años de experiencia): comparar contra el
modo simulado es un buen ejercicio de validación.
