"""Genera CVs ficticios en PDF para practicar.

Uso:  python datos/generar_cvs.py            (500 CVs)
      python datos/generar_cvs.py 500        (los que quieras)

Todos los datos son inventados (nombres, mails, empresas). Usamos una semilla
fija para que todos en el curso tengan exactamente los mismos CVs.
"""
import random
import sys
import unicodedata
from pathlib import Path

from fpdf import FPDF

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

NOMBRES = ["Lucía", "Martín", "Sofía", "Tomás", "Valentina", "Joaquín", "Camila",
           "Mateo", "Agustina", "Facundo", "Micaela", "Nicolás", "Florencia",
           "Santiago", "Julieta", "Ignacio", "Rocío", "Franco", "Carolina", "Bruno",
           "Milagros", "Gonzalo", "Paula", "Ezequiel", "Antonella", "Lautaro"]
APELLIDOS = ["González", "Rodríguez", "Fernández", "López", "Martínez", "Pérez",
             "Gómez", "Díaz", "Romero", "Sosa", "Álvarez", "Torres", "Ruiz",
             "Ramírez", "Acosta", "Benítez", "Medina", "Herrera", "Suárez", "Aguirre"]
CIUDADES = ["La Plata", "CABA", "Quilmes", "Berazategui", "Avellaneda", "Lanús",
            "Mar del Plata", "Rosario", "Córdoba", "Ensenada"]
EMPRESAS = ["Datasur", "Pampa Tech", "Andes Software", "Rio Logística", "Mercadito SRL",
            "Nube Austral", "Patagonia Labs", "Tango Sistemas", "Ceibo Digital",
            "Federal Pagos", "Estudio Contable Ríos", "Municipalidad (área sistemas)"]
CARRERAS = ["Licenciatura en Sistemas", "Ingeniería en Informática",
            "Tecnicatura en Programación", "Ingeniería Industrial",
            "Licenciatura en Diseño Gráfico", "Analista de Sistemas"]
UNIVERSIDADES = ["Universidad Atlántida Argentina", "UNLP", "UTN FRLP", "UNQ", "UBA", "UNMDP"]

# Perfiles: cada uno sesga qué tecnologías aparecen. Así el ranking tiene sentido.
PERFILES = {
    "backend_python": (["Python", "SQL", "Git", "Django", "FastAPI", "PostgreSQL",
                        "Docker", "pytest", "Linux", "Redis", "Flask"], "Desarrollador/a backend"),
    "frontend": (["JavaScript", "TypeScript", "React", "Git", "CSS", "HTML", "Node.js"],
                 "Desarrollador/a frontend"),
    "java": (["Java", "Spring Boot", "SQL", "Git", "MySQL", "Docker"], "Desarrollador/a Java"),
    "datos": (["Python", "SQL", "Pandas", "Power BI", "Excel", "Git"], "Analista de datos"),
    "no_it": (["Excel", "Photoshop", "Illustrator", "Canva", "Office"], "Perfil no técnico"),
}
PESOS_PERFIL = [35, 20, 15, 20, 10]

TAREAS = [
    "Desarrollo y mantenimiento de APIs REST para el área de {area}.",
    "Migración de procesos manuales a scripts automatizados con {tec}.",
    "Diseño de modelos de datos y optimización de consultas lentas.",
    "Participación en ceremonias ágiles (daily, planning, retro) con un equipo de {n} personas.",
    "Implementación de tests automatizados y mejora de la cobertura.",
    "Soporte a usuarios internos y documentación de procesos.",
    "Integración con servicios externos de pagos y facturación.",
    "Armado de tableros e informes para la gerencia de {area}.",
    "Revisión de código (code review) y mentoría a perfiles trainee.",
]
AREAS = ["ventas", "logística", "finanzas", "recursos humanos", "operaciones", "marketing"]
PROYECTOS = [
    ("Bot de turnos", "Bot que reserva turnos en un consultorio y manda recordatorios."),
    ("Gestor de gastos", "Aplicación para dividir gastos entre amigos con reportes mensuales."),
    ("Scraper de precios", "Relevamiento diario de precios de supermercados y alertas por variación."),
    ("API de biblioteca", "Préstamos, reservas y multas de una biblioteca universitaria."),
    ("Dashboard de colectivos", "Visualización de frecuencias de líneas de colectivo con datos abiertos."),
    ("Juego de trivia", "Juego multijugador de preguntas en tiempo real."),
]


CURSOS = ["Docker desde cero", "Testing con pytest", "SQL avanzado", "Git y GitHub",
          "Clean Code", "Introducción a AWS", "React moderno", "Scrum Fundamentals",
          "Patrones de diseño", "Linux para desarrolladores", "Seguridad web (OWASP)",
          "Análisis de datos con Pandas", "Inglés técnico", "Arquitectura de microservicios"]
PLATAFORMAS = ["Coursera", "Udemy", "Platzi", "Fundación Sadosky", "Argentina Programa", "freeCodeCamp"]


def sin_acentos(txt):
    return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()


def frase_relleno(rng):
    # texto "de CV" para que los documentos tengan un largo realista (2-3 páginas)
    partes = [
        "Trabajo cómodo en equipos multidisciplinarios y me interesa seguir aprendiendo.",
        "Me gusta entender el problema de negocio antes de escribir una línea de código.",
        "Valoro la documentación clara y los procesos de deploy repetibles.",
        "Participé en la definición de estándares de código del equipo.",
        "Tengo experiencia relevando requerimientos directamente con usuarios finales.",
        "Me interesa la calidad del software y la automatización de tareas repetitivas.",
    ]
    return " ".join(rng.sample(partes, k=rng.randint(2, 4)))


def armar_cv(i, rng):
    perfil = rng.choices(list(PERFILES), weights=PESOS_PERFIL)[0]
    techs_perfil, titulo = PERFILES[perfil]
    nombre = f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)}"
    # la primera tecnología del perfil siempre está; el resto, al azar
    principal, *resto = techs_perfil
    techs = [principal] + rng.sample(resto, k=rng.randint(2, len(resto)))
    # a algunos les falta Git o SQL a propósito: no cumplen los excluyentes
    if rng.random() < 0.25 and "Git" in techs:
        techs.remove("Git")

    anio_actual = 2026
    experiencias = []
    fin = anio_actual
    for _ in range(rng.randint(0, 4)):
        inicio = fin - rng.randint(1, 3)
        desde_hasta = f"{inicio} - {'actualidad' if fin == anio_actual else fin}"
        tareas = [t.format(area=rng.choice(AREAS), tec=rng.choice(techs), n=rng.randint(3, 12))
                  for t in rng.sample(TAREAS, k=rng.randint(3, 5))]
        experiencias.append((rng.choice(EMPRESAS), titulo, desde_hasta, tareas))
        fin = inicio

    return {
        "nombre": nombre,
        "perfil": perfil,
        "titulo": titulo,
        "ciudad": rng.choice(CIUDADES),
        "email": f"{sin_acentos(nombre.split()[0]).lower()}.{i:03d}@ejemplo.com",
        "resumen": frase_relleno(rng),
        "experiencias": experiencias,
        "carrera": rng.choice(CARRERAS),
        "universidad": rng.choice(UNIVERSIDADES),
        "ingreso": rng.randint(2014, 2024),
        "techs": techs,
        "proyectos": rng.sample(PROYECTOS, k=rng.randint(1, 4)),
        "ingles": rng.choice(["básico", "intermedio", "avanzado"]),
        "cursos": [(c, rng.choice(PLATAFORMAS), rng.randint(2018, 2026))
                   for c in rng.sample(CURSOS, k=rng.randint(4, 12))],
        "extra": [frase_relleno(rng) for _ in range(rng.randint(6, 14))],
    }


def escribir_pdf(cv, ruta):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def titulo(txt):
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, txt, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

    def parrafo(txt):
        pdf.multi_cell(0, 5, txt, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, cv["nombre"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    parrafo(f"{cv['titulo']} | {cv['ciudad']} | {cv['email']}")

    titulo("Perfil")
    parrafo(cv["resumen"])

    titulo("Experiencia laboral")
    if not cv["experiencias"]:
        parrafo("Sin experiencia laboral formal. Busco mi primer trabajo en el área.")
    for empresa, puesto, periodo, tareas in cv["experiencias"]:
        pdf.set_font("Helvetica", "B", 10)
        parrafo(f"{empresa} - {puesto} ({periodo})")
        pdf.set_font("Helvetica", "", 10)
        for t in tareas:
            parrafo(f"- {t}")

    titulo("Educación")
    parrafo(f"{cv['carrera']} - {cv['universidad']} (ingreso {cv['ingreso']})")

    titulo("Tecnologías")
    parrafo(", ".join(cv["techs"]))

    titulo("Proyectos")
    for nombre, desc in cv["proyectos"]:
        parrafo(f"{nombre}: {desc} Tecnologías: {', '.join(cv['techs'][:3])}.")

    titulo("Cursos y certificaciones")
    for curso, plataforma, anio in cv["cursos"]:
        parrafo(f"- {curso} ({plataforma}, {anio}). Certificado de aprobación con evaluación final.")

    titulo("Idiomas")
    parrafo(f"Español nativo. Inglés {cv['ingles']}.")

    titulo("Información adicional")
    for p in cv["extra"]:
        parrafo(p)

    pdf.output(str(ruta))


def main():
    cantidad = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    rng = random.Random(2026)
    config.CARPETA_CVS.mkdir(parents=True, exist_ok=True)
    for viejo in config.CARPETA_CVS.glob("*.pdf"):
        viejo.unlink()
    for i in range(1, cantidad + 1):
        cv = armar_cv(i, rng)
        escribir_pdf(cv, config.CARPETA_CVS / f"cv_{i:03d}.pdf")
    print(f"Listo: {cantidad} CVs en {config.CARPETA_CVS}")


if __name__ == "__main__":
    main()
