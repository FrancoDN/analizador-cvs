"""Portal de postulaciones + panel de RRHH.

Uso:
    python portal/servidor.py           solo en esta computadora
    python portal/servidor.py --red     también desde celulares en la misma red (wifi del aula)

Páginas:
    /         página pública: el candidato sube su CV y sigue su lugar en la fila
    /admin    panel de RRHH (pide clave): postulaciones en vivo y el laboratorio de gui/

Es la clase 4 funcionando de verdad, productor / consumidor:

    pedidos HTTP (un hilo por pedido) --put--> cola --get--> N hilos analistas
    cada pedido extrae el texto (CPU)          cada analista le pregunta a la IA (espera)

La clave del panel se toma de ADMIN_CLAVE. Si no está, se inventa una al arrancar
y se muestra en la consola.
"""
import argparse
import io
import json
import os
import queue
import random
import secrets
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from comun import ia
from comun.pdfs import extraer_texto, listar_cvs
from gui import servidor as lab  # el laboratorio se reusa tal cual

AQUI = Path(__file__).resolve().parent
CARPETA = config.RAIZ / "datos" / "postulaciones"
INDICE = CARPETA / "postulaciones.json"
MAX_PDF = 5 * 1024 * 1024
ANALISTAS = int(os.getenv("PORTAL_WORKERS", "2"))
CLAVE = os.getenv("ADMIN_CLAVE") or secrets.token_hex(3)
CAMPOS_IA = ("nombre", "anios_experiencia", "tecnologias", "nivel_ingles", "resumen")


# ---------------------------------------------------------------------------
# Las postulaciones: un diccionario compartido por todos los hilos + la cola
# ---------------------------------------------------------------------------
class Postulaciones:
    def __init__(self):
        self.lock = threading.Lock()  # protege filas, contador y el archivo
        self.filas = {}               # id -> datos de la postulación
        self.contador = 0             # orden de llegada
        self.cola = queue.Queue()     # ids esperando a un analista

    # --- persistencia (siempre con el lock tomado) ---
    def cargar(self):
        CARPETA.mkdir(parents=True, exist_ok=True)
        (CARPETA / ".gitignore").write_text("*\n")  # son CVs de personas reales: nunca a git
        try:
            filas = json.loads(INDICE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            filas = []
        with self.lock:
            for f in sorted(filas, key=lambda f: f["orden"]):
                if f["estado"] in ("en cola", "analizando"):  # quedaron a medias al cerrar
                    f["estado"] = "en cola"
                    self.cola.put(f["id"])
                self.filas[f["id"]] = f
                self.contador = max(self.contador, f["orden"])

    def _guardar(self):
        temporal = INDICE.with_suffix(".tmp")
        temporal.write_text(json.dumps(list(self.filas.values()), ensure_ascii=False, indent=1),
                            encoding="utf-8")
        temporal.replace(INDICE)  # reemplazo atómico: nunca queda un JSON a medio escribir

    # --- productor: lo llama el hilo de cada pedido HTTP ---
    def agregar(self, nombre, email, pdf, texto, origen):
        id_ = secrets.token_urlsafe(6)
        (CARPETA / f"{id_}.pdf").write_bytes(pdf)
        (CARPETA / f"{id_}.txt").write_text(texto, encoding="utf-8")
        with self.lock:
            self.contador += 1
            self.filas[id_] = {
                "id": id_, "orden": self.contador, "origen": origen,
                "nombre": nombre, "email": email,
                "recibida": datetime.now().isoformat(timespec="seconds"),
                "estado": "en cola", "extraido": None, "crudo": "", "error": None,
                "worker": None, "inicio": None, "duracion": None,
            }
            self._guardar()
        self.cola.put(id_)
        avisar(id_)
        return id_

    def volver_a_encolar(self, id_):
        with self.lock:
            f = self.filas.get(id_)
            if f is None or f["estado"] in ("en cola", "analizando"):
                return False
            self.contador += 1
            f.update(estado="en cola", orden=self.contador, error=None, worker=None, inicio=None)
            self._guardar()
        self.cola.put(id_)
        avisar(id_)
        return True

    def borrar(self, id_):
        with self.lock:
            if self.filas.pop(id_, None) is None:
                return False
            self._guardar()
        for ext in ("pdf", "txt"):
            (CARPETA / f"{id_}.{ext}").unlink(missing_ok=True)
        avisar(id_)
        return True

    # --- lecturas ---
    def _delante_de(self, fila):
        return sum(1 for f in self.filas.values()
                   if f["estado"] == "en cola" and f["orden"] < fila["orden"])

    def _segundos_por_cv(self):
        hechas = sorted((f for f in self.filas.values() if f["duracion"]),
                        key=lambda f: f["orden"])[-10:]
        return sum(f["duracion"] for f in hechas) / len(hechas) if hechas else None

    def para_el_candidato(self, id_):
        """Lo que ve el candidato: su estado y lugar en la fila. El puntaje no."""
        with self.lock:
            f = self.filas.get(id_)
            if f is None:
                return None
            datos = {k: f[k] for k in ("id", "nombre", "estado", "recibida", "error")}
            datos["analistas"] = ANALISTAS
            datos["en_cola"] = sum(1 for x in self.filas.values() if x["estado"] == "en cola")
            datos["analizando"] = sum(1 for x in self.filas.values() if x["estado"] == "analizando")
            datos["segundos_por_cv"] = self._segundos_por_cv()
            if f["estado"] == "en cola":
                datos["delante"] = self._delante_de(f)
            if f["estado"] == "analizando":
                datos["hace"] = round(time.time() - f["inicio"], 1)
            if f["estado"] == "lista":
                datos["extraido"] = f["extraido"]
                techs = {t.lower() for t in ia._normalizar(f["extraido"].get("tecnologias", []))}
                datos["excluyentes"] = [{"nombre": t, "esta": t.lower() in techs} for t in config.EXCLUYENTES]
        return datos

    def para_el_panel(self):
        with self.lock:
            filas = [dict(f) for f in self.filas.values()]
            cola = [f["id"] for f in sorted(filas, key=lambda f: f["orden"]) if f["estado"] == "en cola"]
            promedio = self._segundos_por_cv()
        for f in filas:
            # el puntaje se calcula al leer: si cambian los criterios en el laboratorio, ya se ve
            if f["extraido"]:
                f.update(ia.puntuar(f["extraido"]))
        return {"filas": filas, "cola": cola, "analistas": nombres_analistas,
                "segundos_por_cv": promedio, "ahora": time.time()}


post = Postulaciones()
nombres_analistas = [f"analista-{i}" for i in range(1, ANALISTAS + 1)]


def avisar(id_):
    """Avisa a los paneles abiertos. Usa el mismo canal de eventos que el laboratorio."""
    lab.eventos.publicar("postulacion", id=id_)


# ---------------------------------------------------------------------------
# Consumidores: cada analista saca un id de la cola y le pregunta a la IA
# ---------------------------------------------------------------------------
def analista():
    while True:
        id_ = post.cola.get()  # se queda esperando hasta que haya algo
        with post.lock:
            fila = post.filas.get(id_)
            if fila is None or fila["estado"] != "en cola":
                continue  # la borraron mientras esperaba
            fila.update(estado="analizando", worker=threading.current_thread().name, inicio=time.time())
            post._guardar()
        avisar(id_)

        t0 = time.perf_counter()
        try:
            texto = (CARPETA / f"{id_}.txt").read_text(encoding="utf-8")
            resultado, crudo = ia.analizar_cv_detalle(texto)
            cambios = {"estado": "lista", "crudo": crudo, "error": None,
                       "extraido": {k: resultado.get(k) for k in CAMPOS_IA}}
        except Exception as e:  # un CV que falla no frena a los demás
            cambios = {"estado": "error", "error": f"{type(e).__name__}: {e}"}
        cambios["duracion"] = round(time.perf_counter() - t0, 2)

        with post.lock:
            if id_ in post.filas:
                post.filas[id_].update(cambios)
                post._guardar()
        avisar(id_)


def arrancar_analistas():
    for nombre in nombres_analistas:
        threading.Thread(target=analista, name=nombre, daemon=True).start()


# ---------------------------------------------------------------------------
# Recepción de un CV (productor)
# ---------------------------------------------------------------------------
class Rechazo(Exception):
    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.codigo = codigo


def leer_pdf(pdf: bytes) -> str:
    if not pdf.startswith(b"%PDF-"):
        raise Rechazo("El archivo no es un PDF. Exportá tu CV como PDF y volvé a subirlo.")
    try:
        texto = extraer_texto(io.BytesIO(pdf))  # trabajo de CPU, en el hilo del pedido
    except Exception:
        raise Rechazo("No pudimos abrir el PDF. Probá exportarlo de nuevo.")
    if len(texto) < 40:
        raise Rechazo("El PDF no tiene texto para leer (¿es una imagen escaneada?). "
                      "Exportalo desde Word o Google Docs.", 422)
    return texto


def simular(cantidad):
    """Mete CVs de prueba en la fila, como si se hubieran postulado."""
    ids = []
    for ruta in random.sample(listar_cvs(), k=min(cantidad, len(listar_cvs()))):
        pdf = ruta.read_bytes()
        texto = leer_pdf(pdf)
        nombre = texto.splitlines()[0].strip()
        ids.append(post.agregar(nombre, f"prueba+{ruta.stem}@ejemplo.com", pdf, texto, f"prueba ({ruta.name})"))
    return ids


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
sesiones = set()
url_red = None
LAB_GET = {"/api/estado", "/api/cv", "/api/eventos"}
LAB_POST = {"/api/correr", "/api/detener", "/api/criterios", "/api/ejemplos", "/api/ejemplos/borrar"}
# El laboratorio va adentro del panel, que ya tiene su propio encabezado
SIN_ENCABEZADO = b"<style>body>header{display:none}.app{padding-top:16px}</style></head>"


def info_puesto():
    return {"puesto": config.PUESTO, "excluyentes": config.EXCLUYENTES, "deseables": config.DESEABLES,
            "analistas": ANALISTAS, "max_mb": MAX_PDF // (1024 * 1024)}


def info_panel():
    return {**info_puesto(), "modelo": config.MODELO, "simulada": config.IA_SIMULADA,
            "ia_disponible": ia.ia_disponible(), "url_red": url_red}


class Manejador(lab.Manejador):

    # --- ayudas ---
    def enviar(self, cuerpo: bytes, tipo, extra=None):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(cuerpo)

    def pagina(self, nombre):
        self.enviar((AQUI / nombre).read_bytes(), "text/html; charset=utf-8")

    def autenticado(self):
        galleta = SimpleCookie(self.headers.get("Cookie", "")).get("sesion")
        return galleta is not None and galleta.value in sesiones

    def parametro(self, nombre):
        return parse_qs(urlparse(self.path).query).get(nombre, [""])[0].strip()

    # --- GET ---
    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta == "/":
            return self.pagina("publico.html")
        if ruta == "/admin":
            return self.pagina("admin.html")
        if ruta == "/api/puesto":
            return self.responder(info_puesto())
        if ruta == "/api/postulacion":
            datos = post.para_el_candidato(self.parametro("id"))
            return self.responder(datos or {"error": "No encontramos esa postulación."}, 200 if datos else 404)
        if ruta == "/cv-de-prueba.pdf":
            ruta_cv = random.choice(listar_cvs())
            return self.enviar(ruta_cv.read_bytes(), "application/pdf",
                               {"Content-Disposition": f'attachment; filename="{ruta_cv.name}"'})
        if ruta == "/api/admin/sesion":
            return self.responder({"ok": self.autenticado()})

        if not self.autenticado():
            return self.responder({"error": "Entrá al panel con la clave."}, 401)

        if ruta == "/admin/lab":
            html = lab.HTML.read_bytes().replace(b"</head>", SIN_ENCABEZADO, 1)
            return self.enviar(html, "text/html; charset=utf-8")
        if ruta == "/api/admin/info":
            return self.responder(info_panel())
        if ruta == "/api/admin/postulaciones":
            return self.responder(post.para_el_panel())
        if ruta == "/api/admin/texto":
            id_ = Path(self.parametro("id")).name
            archivo = CARPETA / f"{id_}.txt"
            return self.responder({"texto": archivo.read_text(encoding="utf-8") if archivo.exists() else ""})
        if ruta == "/api/admin/pdf":
            archivo = CARPETA / f"{Path(self.parametro('id')).name}.pdf"
            if not archivo.exists():
                return self.responder({"error": "No existe"}, 404)
            return self.enviar(archivo.read_bytes(), "application/pdf")
        if ruta in LAB_GET:
            return super().do_GET()
        self.responder({"error": "no existe"}, 404)

    # --- POST ---
    def do_POST(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/postular":
            return self.recibir_cv()
        if ruta == "/api/admin/entrar":
            clave = str(self.leer_json().get("clave", ""))
            if not secrets.compare_digest(clave, CLAVE):
                time.sleep(0.5)  # frena a quien prueba claves al azar
                return self.responder({"ok": False, "error": "La clave no es correcta."}, 401)
            token = secrets.token_urlsafe(24)
            sesiones.add(token)
            cuerpo = json.dumps({"ok": True}).encode()
            return self.enviar(cuerpo, "application/json",
                               {"Set-Cookie": f"sesion={token}; HttpOnly; SameSite=Strict; Path=/"})

        if not self.autenticado():
            return self.responder({"error": "Entrá al panel con la clave."}, 401)

        if ruta == "/api/admin/salir":
            galleta = SimpleCookie(self.headers.get("Cookie", "")).get("sesion")
            sesiones.discard(galleta.value if galleta else "")
            return self.responder({"ok": True})
        if ruta == "/api/admin/simular":
            cantidad = max(1, min(50, int(self.leer_json().get("cantidad", 10))))
            return self.responder({"ids": simular(cantidad)})
        if ruta == "/api/admin/reanalizar":
            return self.responder({"ok": post.volver_a_encolar(str(self.leer_json().get("id", "")))})
        if ruta == "/api/admin/borrar":
            return self.responder({"ok": post.borrar(Path(str(self.leer_json().get("id", ""))).name)})
        if ruta in LAB_POST:
            return super().do_POST()
        self.responder({"error": "no existe"}, 404)

    def recibir_cv(self):
        nombre = self.parametro("nombre")[:80]
        email = self.parametro("email")[:120]
        largo = int(self.headers.get("Content-Length") or 0)
        try:
            if not nombre or "@" not in email:
                raise Rechazo("Completá tu nombre y un email válido.")
            if largo == 0:
                raise Rechazo("Adjuntá tu CV en PDF.")
            if largo > MAX_PDF:
                raise Rechazo(f"El PDF pesa más de {MAX_PDF // (1024 * 1024)} MB.", 413)
            pdf = self.rfile.read(largo)
            texto = leer_pdf(pdf)
        except Rechazo as r:
            return self.responder({"error": str(r)}, r.codigo)
        id_ = post.agregar(nombre, email, pdf, texto, "formulario")
        self.responder(post.para_el_candidato(id_))


def ip_local():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no manda nada: solo elige la placa de red
            return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def main():
    global url_red
    parser = argparse.ArgumentParser(description="Portal de postulaciones + panel de RRHH")
    parser.add_argument("--red", action="store_true", help="aceptar conexiones de otros dispositivos de la red")
    parser.add_argument("--puerto", type=int, default=int(os.getenv("PUERTO", "8000")))
    args = parser.parse_args()

    post.cargar()
    arrancar_analistas()
    host = "0.0.0.0" if args.red else "127.0.0.1"
    servidor = lab.Servidor((host, args.puerto), Manejador)
    local = f"http://localhost:{args.puerto}"
    if args.red:
        url_red = f"http://{ip_local()}:{args.puerto}"

    print(f"Página pública:  {local}")
    if url_red:
        print(f"Desde celulares: {url_red}   (misma wifi; si Windows pregunta, permití el acceso)")
    print(f"Panel de RRHH:   {local}/admin   clave: {CLAVE}")
    print(f"IA: {'SIMULADA' if config.IA_SIMULADA else config.MODELO}   analistas: {ANALISTAS}")
    print("Ctrl+C para cerrar")
    threading.Timer(1, webbrowser.open, args=(f"{local}/admin",)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando...")
        lab.estado.cancelar.set()
        servidor.server_close()


if __name__ == "__main__":
    main()
