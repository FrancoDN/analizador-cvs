# Portal de postulaciones

Una cara pública para el analizador: el candidato sube su CV y ve en qué lugar de
la fila está; RRHH entra a un panel con las postulaciones en vivo y, en otra
pestaña, el laboratorio de `gui/` tal cual.

```powershell
python portal/servidor.py           # solo en esta computadora
python portal/servidor.py --red     # también desde los celulares conectados al mismo wifi
```

Funciona con la misma configuración que el resto (`$env:IA_SIMULADA=1`, `$env:MODELO`, ...)
y no necesita instalar nada más.

| Dirección | Qué es |
|---|---|
| `http://localhost:8000` | Página pública: formulario y seguimiento de la postulación |
| `http://localhost:8000/admin` | Panel de RRHH: postulaciones + laboratorio |

La clave del panel sale en la consola al arrancar. Para dejarla fija:
`$env:ADMIN_CLAVE="lo-que-quieras"`. Cuántos hilos analizan postulaciones:
`$env:PORTAL_WORKERS=2` (por defecto 2).

## Qué tiene que ver con la materia

Es la clase 4 funcionando de verdad:

```
navegador --POST--> hilo del pedido --put--> cola --get--> analista-1 --> IA
                    (extrae el texto:                  --> analista-2 --> IA
                     trabajo de CPU)
```

- Cada pedido HTTP lo atiende un hilo distinto (`ThreadingHTTPServer`): son los productores.
- `queue.Queue` reparte el trabajo; los analistas son los consumidores (`analista()` en `servidor.py`).
- Las postulaciones viven en un diccionario compartido protegido por un `Lock`.
  El archivo `datos/postulaciones/postulaciones.json` se reescribe entero y con
  reemplazo atómico, así nunca queda a medio escribir.
- El panel se actualiza por Server-Sent Events, con el mismo canal que usa el laboratorio.

## Para la clase

1. `python portal/servidor.py --red` y proyectar el panel.
2. Los alumnos entran desde el celular a la dirección que aparece en el panel y suben
   un CV (hay un link para bajar uno de prueba).
3. Con 30 postulaciones llegando a la vez y 2 analistas se ve la fila crecer y vaciarse.
   Preguntas para hacer: ¿cuánto tarda el último? ¿Qué pasa con 4 analistas
   (`$env:PORTAL_WORKERS=4`)? ¿Y si Ollama solo atiende 2 pedidos a la vez?

## Archivos

```
portal/servidor.py    servidor: rutas, sesión del panel, cola y analistas
portal/publico.html   página del candidato
portal/admin.html     panel de RRHH (el laboratorio se carga adentro desde /admin/lab)
datos/postulaciones/  los PDF recibidos, su texto y el índice en JSON
```
