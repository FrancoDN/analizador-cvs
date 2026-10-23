"""Cliente mínimo para el LLM local (Ollama).

Usamos la API HTTP de Ollama directamente con urllib (stdlib) para que se vea
que "llamar a la IA" es, para nuestro programa, una petición de red más:
mandamos un pedido y nos quedamos ESPERANDO la respuesta.

División de tareas:
  - el modelo LEE el CV y devuelve datos estructurados (lo que hace bien)
  - el puntaje lo calcula `puntuar()` con reglas fijas (explicable, sin sesgos ocultos)
"""
import json
import random
import re
import time
import urllib.request

import config

# Le pedimos a Ollama que responda respetando este JSON Schema (structured outputs).
ESQUEMA = {
    "type": "object",
    "properties": {
        "nombre": {"type": "string"},
        "anios_experiencia": {"type": "integer"},
        "tecnologias": {"type": "array", "items": {"type": "string"}, "maxItems": 15},
        "nivel_ingles": {"type": "string", "enum": ["basico", "intermedio", "avanzado", "no dice"]},
        "resumen": {"type": "string"},
    },
    "required": ["nombre", "anios_experiencia", "tecnologias", "nivel_ingles", "resumen"],
}

INSTRUCCIONES = """Extraé datos de un CV. Respondé SOLO con el JSON pedido.
- anios_experiencia: años de experiencia laboral sumando todos los trabajos (0 si no tiene).
- tecnologias: lenguajes, frameworks y herramientas que aparecen en el CV, tal cual están escritas.
- resumen: una oración de menos de 20 palabras describiendo el perfil."""


# Correcciones hechas desde la interfaz gráfica. Se le muestran al modelo como
# ejemplos dentro del prompt (few-shot). No cambian los pesos del modelo.
RUTA_EJEMPLOS = config.RAIZ / "datos" / "ejemplos.json"
MAX_EJEMPLOS = 2


def cargar_ejemplos() -> list:
    try:
        return json.loads(RUTA_EJEMPLOS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def armar_pedido(texto_cv: str) -> dict:
    """Arma el body del POST /api/chat. Lo reusan la versión sync y la async."""
    mensajes = [{"role": "system", "content": INSTRUCCIONES}]
    for ej in cargar_ejemplos()[-MAX_EJEMPLOS:]:
        mensajes.append({"role": "user", "content": ej["texto"][:1500]})
        mensajes.append({"role": "assistant", "content": json.dumps(ej["respuesta"], ensure_ascii=False)})
    mensajes.append({"role": "user", "content": texto_cv[:2500]})
    return {
        "model": config.MODELO,
        "stream": False,
        "format": ESQUEMA,
        # temperature 0: respuestas estables. num_predict: corta si el modelo se enrosca
        "options": {"temperature": 0, "num_predict": 250},
        "messages": mensajes,
    }


def interpretar_respuesta(datos: dict) -> dict:
    extraido = json.loads(datos["message"]["content"])
    # los modelos chicos a veces repiten tecnologías: dejamos cada una una sola vez
    techs = [t.strip() for t in extraido.get("tecnologias", []) if t.strip()]
    extraido["tecnologias"] = list(dict.fromkeys(techs))
    return {**extraido, **puntuar(extraido)}


def analizar_cv(texto_cv: str) -> dict:
    """Llamada BLOQUEANTE: el hilo que la ejecuta queda esperando la respuesta."""
    return analizar_cv_detalle(texto_cv)[0]


def analizar_cv_detalle(texto_cv: str):
    """Igual que analizar_cv, pero también devuelve el texto crudo que respondió el modelo."""
    if config.IA_SIMULADA:
        time.sleep(demora_simulada())
        resultado = respuesta_simulada(texto_cv)
        crudo = json.dumps({k: resultado[k] for k in ESQUEMA["required"]}, ensure_ascii=False)
        return resultado, crudo

    cuerpo = json.dumps(armar_pedido(texto_cv)).encode("utf-8")
    pedido = urllib.request.Request(
        f"{config.OLLAMA_URL}/api/chat",
        data=cuerpo,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(pedido, timeout=config.TIMEOUT_IA) as resp:
        datos = json.load(resp)
    return interpretar_respuesta(datos), datos["message"]["content"]


# ---------------------------------------------------------------------------
# Puntaje: reglas nuestras sobre lo que extrajo la IA
# ---------------------------------------------------------------------------
# Algunas tecnologías "cuentan como" otra (si sabés PostgreSQL, sabés SQL)
EQUIVALENCIAS = {"postgresql": "sql", "mysql": "sql", "github": "git", "gitlab": "git"}


def _normalizar(techs):
    nombres = {t.strip().lower() for t in techs}
    return nombres | {EQUIVALENCIAS[t] for t in nombres if t in EQUIVALENCIAS}


def puntuar(extraido: dict) -> dict:
    techs = _normalizar(extraido.get("tecnologias", []))
    faltan = [t for t in config.EXCLUYENTES if t.lower() not in techs]
    deseables = [t for t in config.DESEABLES if t.lower() in techs]
    anios = max(0, int(extraido.get("anios_experiencia") or 0))

    puntaje = 50 if not faltan else 10
    puntaje += 7 * len(deseables)
    puntaje += 3 * min(anios, 4)  # para un junior, más de 4 años no suma
    puntaje += {"intermedio": 3, "avanzado": 5}.get(extraido.get("nivel_ingles"), 0)

    return {
        "puntaje": min(puntaje, 100),
        "cumple_excluyentes": not faltan,
        "motivo": f"faltan: {', '.join(faltan)}" if faltan
                  else f"cumple excluyentes; deseables: {', '.join(deseables) or 'ninguno'}",
    }


def ia_disponible() -> bool:
    if config.IA_SIMULADA:
        return True
    try:
        urllib.request.urlopen(f"{config.OLLAMA_URL}/api/tags", timeout=3)
        return True
    except OSError:
        return False


def chequear_ia():
    if not ia_disponible():
        raise SystemExit(
            f"No encuentro Ollama en {config.OLLAMA_URL}.\n"
            f"  - Abrí Ollama y corré: ollama pull {config.MODELO}\n"
            "  - O probá sin modelo con IA_SIMULADA=1"
        )


# ---------------------------------------------------------------------------
# Modo simulado: misma "forma" de respuesta, sin modelo.
# Extrae con expresiones regulares y tarda lo que tardaría una consulta.
# ---------------------------------------------------------------------------
def demora_simulada() -> float:
    return random.uniform(0.6, 1.4)


def respuesta_simulada(texto_cv: str) -> dict:
    lineas = texto_cv.splitlines()
    techs = re.search(r"Tecnologías\n(.+)", texto_cv)
    periodos = re.findall(r"\((20\d\d) - (20\d\d|actualidad)\)", texto_cv)
    anios = sum((2026 if fin == "actualidad" else int(fin)) - int(ini) for ini, fin in periodos)
    ingles = re.search(r"Inglés (básico|intermedio|avanzado)", texto_cv)
    extraido = {
        "nombre": lineas[0].strip() if lineas else "?",
        "anios_experiencia": anios,
        "tecnologias": techs.group(1).split(", ") if techs else [],
        "nivel_ingles": ingles.group(1).replace("á", "a") if ingles else "no dice",
        "resumen": "(simulado) " + (lineas[1] if len(lineas) > 1 else ""),
    }
    return {**extraido, **puntuar(extraido)}
