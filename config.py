"""Configuración compartida por todas las clases.

Casi todo se puede pisar con variables de entorno, así no hay que tocar código
en el aula (ej: IA_SIMULADA=1 si Ollama no anda).
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CARPETA_CVS = RAIZ / "datos" / "cvs"
CARPETA_RESULTADOS = RAIZ / "resultados"

# --- IA local (Ollama) ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODELO = os.getenv("MODELO", "qwen2.5:1.5b")
TIMEOUT_IA = float(os.getenv("TIMEOUT_IA", "120"))

# Si no hay Ollama, IA_SIMULADA=1 responde con una heurística y una demora
# parecida a la de un modelo real. Sirve para practicar la concurrencia igual.
IA_SIMULADA = os.getenv("IA_SIMULADA", "0") == "1"

# Cuántos CVs mandar a la IA. Con el modelo real cada uno tarda unos segundos,
# así que en clase conviene arrancar con pocos.
LIMITE_CVS = int(os.getenv("LIMITE", "10"))

# Hilos / procesos por defecto
WORKERS = int(os.getenv("WORKERS", "4"))

# La búsqueda contra la que se evalúa cada CV.
# La IA solo EXTRAE datos del CV; el puntaje lo calculamos nosotros con estas
# reglas (ver comun/ia.py -> puntuar). Así el criterio es explícito y auditable.
PUESTO = "Desarrollador/a Backend Python Junior"
EXCLUYENTES = ["Python", "SQL", "Git"]
DESEABLES = ["Django", "FastAPI", "Docker", "pytest", "PostgreSQL", "Linux"]
