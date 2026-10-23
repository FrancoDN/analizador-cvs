"""Interfaz gráfica del analizador de CVs.

Uso:   python gui/servidor.py
y se abre http://localhost:8000 en el navegador.

Solo usa la biblioteca estándar. El servidor también sirve de ejemplo de lo que
vimos en la materia: atiende cada pedido del navegador en un hilo, las corridas
usan un pool de hilos, y el progreso viaja al navegador por colas (una por cliente).
"""
import json
import queue
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs

PUERTO = 8000
HTML = Path(__file__).resolve().parent / "index.html"


class Eventos:
    """Manda cada evento a todos los navegadores conectados (una cola por cliente)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._clientes = []

    def suscribir(self):
        q = queue.Queue()
        with self._lock:
            self._clientes.append(q)
        return q

    def desuscribir(self, q):
        with self._lock:
            self._clientes.remove(q)

    def publicar(self, tipo, **datos):
        mensaje = json.dumps({"tipo": tipo, **datos}, ensure_ascii=False)
        with self._lock:
            for q in self._clientes:
                q.put(mensaje)


class Estado:
    """Lo que comparten los hilos del servidor. Todo se toca con el lock."""

    def __init__(self):
        self.lock = threading.Lock()
        self.resultados = {}  # archivo -> fila
        self.textos = {}      # archivo -> texto extraído
        self.historial = []
        self.cancelar = threading.Event()
        self.hilo = None

    def en_curso(self):
        return self.hilo is not None and self.hilo.is_alive()


eventos = Eventos()
estado = Estado()
lock_ejemplos = threading.Lock()


# ---------------------------------------------------------------------------
# Corridas
# ---------------------------------------------------------------------------
def analizar_uno(ruta, inicio):
    if estado.cancelar.is_set():
        return
    worker = threading.current_thread().name
    eventos.publicar("empieza", archivo=ruta.name, worker=worker, t=time.perf_counter() - inicio)

    t0 = time.perf_counter()
    texto, crudo = "", ""
    try:
        texto = extraer_texto(ruta)
        resultado, crudo = ia.analizar_cv_detalle(texto)
    except Exception as e:  # un CV que falla no corta la corrida
        resultado = {"nombre": "?", "puntaje": 0, "cumple_excluyentes": False,
                     "tecnologias": [], "motivo": f"ERROR: {e}"}

    fila = {"archivo": ruta.name, **resultado, "crudo": crudo,
            "duracion": round(time.perf_counter() - t0, 2), "worker": worker}
    with estado.lock:
        estado.resultados[ruta.name] = fila
        estado.textos[ruta.name] = texto
    eventos.publicar("termina", fila=fila, t=time.perf_counter() - inicio)


def correr(modo, workers, limite):
    rutas = listar_cvs(limite)
    with estado.lock:
        estado.resultados.clear()
    estado.cancelar.clear()
    if modo == "secuencial":
        workers = 1

    inicio = time.perf_counter()
    eventos.publicar("inicio", modo=modo, workers=workers, total=len(rutas))

    if modo == "secuencial":
        for ruta in rutas:
            analizar_uno(ruta, inicio)
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ia") as pool:
            list(pool.map(lambda r: analizar_uno(r, inicio), rutas))

    total = time.perf_counter() - inicio
    with estado.lock:
        hechos = len(estado.resultados)
        registro = {"modo": modo, "workers": workers, "cvs": hechos,
                    "segundos": round(total, 1), "cancelada": estado.cancelar.is_set(),
                    "modelo": "simulado" if config.IA_SIMULADA else config.MODELO}
        estado.historial.append(registro)
    eventos.publicar("fin", **registro)


def iniciar_corrida(modo, workers, limite):
    if estado.en_curso():
        return False
    # en secuencial el hilo de la corrida se llama ia_0, igual que el primer worker del pool
    estado.hilo = threading.Thread(target=correr, args=(modo, workers, limite),
                                   name="ia_0", daemon=True)
    estado.hilo.start()
    return True


# ---------------------------------------------------------------------------
# Criterios y ejemplos
# ---------------------------------------------------------------------------
def aplicar_criterios(excluyentes, deseables):
    config.EXCLUYENTES[:] = excluyentes  # se modifican en el lugar: todos los módulos ven el cambio
    config.DESEABLES[:] = deseables
    with estado.lock:
        for fila in estado.resultados.values():
            fila.update(ia.puntuar(fila))
        filas = list(estado.resultados.values())
    eventos.publicar("repuntuado", filas=filas)


def guardar_ejemplo(archivo, respuesta):
    with estado.lock:
        texto = estado.textos.get(archivo)
        fila = estado.resultados.get(archivo)
    if texto is None:
        texto = extraer_texto(config.CARPETA_CVS / archivo)

    with lock_ejemplos:
        ejemplos = ia.cargar_ejemplos()
        ejemplos = [e for e in ejemplos if e["archivo"] != archivo]
        ejemplos.append({"archivo": archivo, "texto": texto, "respuesta": respuesta})
        ia.RUTA_EJEMPLOS.write_text(json.dumps(ejemplos, ensure_ascii=False, indent=2), encoding="utf-8")

    # la fila corregida pasa a mostrar los datos buenos
    if fila is not None:
        with estado.lock:
            fila.update(respuesta)
            fila.update(ia.puntuar(fila))
        eventos.publicar("actualiza", fila=fila)
    return ejemplos


def borrar_ejemplo(archivo):
    with lock_ejemplos:
        ejemplos = [e for e in ia.cargar_ejemplos() if e["archivo"] != archivo]
        ia.RUTA_EJEMPLOS.write_text(json.dumps(ejemplos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ejemplos


def resumen_ejemplos():
    return [{"archivo": e["archivo"], "nombre": e["respuesta"].get("nombre", "")}
            for e in ia.cargar_ejemplos()]


def estado_actual():
    with estado.lock:
        resultados = list(estado.resultados.values())
        historial = list(estado.historial)
    return {
        "modelo": config.MODELO,
        "simulada": config.IA_SIMULADA,
        "ia_disponible": ia.ia_disponible(),
        "puesto": config.PUESTO,
        "excluyentes": config.EXCLUYENTES,
        "deseables": config.DESEABLES,
        "total_cvs": len(listar_cvs()),
        "limite": config.LIMITE_CVS,
        "workers": config.WORKERS,
        "en_curso": estado.en_curso(),
        "max_ejemplos": ia.MAX_EJEMPLOS,
        "ejemplos": resumen_ejemplos(),
        "resultados": resultados,
        "historial": historial,
    }


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
# Errores que aparecen cuando el navegador cierra la conexión (recargar, cerrar la pestaña).
# No son fallas del programa, así que no los mostramos.
CONEXION_CORTADA = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)


class Servidor(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], CONEXION_CORTADA):
            super().handle_error(request, client_address)


class Manejador(BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass  # sin log por cada pedido

    def responder(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def leer_json(self):
        largo = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(largo) or b"{}")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            cuerpo = HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
        elif url.path == "/api/estado":
            self.responder(estado_actual())
        elif url.path == "/api/cv":
            archivo = Path(parse_qs(url.query).get("archivo", [""])[0]).name  # solo el nombre
            with estado.lock:
                texto = estado.textos.get(archivo)
            if texto is None and (config.CARPETA_CVS / archivo).exists():
                texto = extraer_texto(config.CARPETA_CVS / archivo)
            self.responder({"archivo": archivo, "texto": texto or ""})
        elif url.path == "/api/eventos":
            self.transmitir_eventos()
        else:
            self.responder({"error": "no existe"}, 404)

    def do_POST(self):
        datos = self.leer_json()
        if self.path == "/api/correr":
            modo = "hilos" if datos.get("modo") == "hilos" else "secuencial"
            workers = max(1, min(16, int(datos.get("workers", 4))))
            limite = max(1, min(500, int(datos.get("limite", 10))))
            ok = iniciar_corrida(modo, workers, limite)
            self.responder({"ok": ok, "error": None if ok else "Ya hay una corrida en curso"})
        elif self.path == "/api/detener":
            estado.cancelar.set()
            self.responder({"ok": True})
        elif self.path == "/api/criterios":
            limpiar = lambda xs: [x.strip() for x in xs if x.strip()]
            aplicar_criterios(limpiar(datos.get("excluyentes", [])), limpiar(datos.get("deseables", [])))
            self.responder({"ok": True})
        elif self.path == "/api/ejemplos":
            guardar_ejemplo(Path(datos["archivo"]).name, datos["respuesta"])
            self.responder({"ejemplos": resumen_ejemplos()})
        elif self.path == "/api/ejemplos/borrar":
            borrar_ejemplo(Path(datos["archivo"]).name)
            self.responder({"ejemplos": resumen_ejemplos()})
        else:
            self.responder({"error": "no existe"}, 404)

    def transmitir_eventos(self):
        """Server-Sent Events: la conexión queda abierta y le vamos escribiendo eventos."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        q = eventos.suscribir()
        try:
            while True:
                try:
                    mensaje = q.get(timeout=15)
                    self.wfile.write(f"data: {mensaje}\n\n".encode("utf-8"))
                except queue.Empty:
                    self.wfile.write(b": sigo vivo\n\n")  # evita que el navegador corte la conexión
                self.wfile.flush()
        except CONEXION_CORTADA:
            pass
        finally:
            eventos.desuscribir(q)


def main():
    servidor = Servidor(("127.0.0.1", PUERTO), Manejador)
    url = f"http://localhost:{PUERTO}"
    print(f"Interfaz en {url}  (Ctrl+C para cerrar)")
    print(f"IA: {'SIMULADA' if config.IA_SIMULADA else config.MODELO}")
    threading.Timer(1, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando...")
        estado.cancelar.set()
        servidor.server_close()


if __name__ == "__main__":
    main()
