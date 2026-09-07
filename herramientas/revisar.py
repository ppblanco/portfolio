# -*- coding: utf-8 -*-
"""
Repasa las paginas antes de publicar. Solo Python de serie, sin instalar nada.

Mira lo que se puede mirar sin abrir un navegador: marcadores sin rellenar,
enlaces internos rotos, etiquetas que faltan, imagenes sin alt, y que siga
y que las paginas siguen teniendo sus metadatos.

Uso:
    python herramientas/revisar.py

Sale con codigo 1 si hay algo que arreglar, para poder encadenarlo.
"""

import html.parser
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Solo lo que se publica. version-corta.html y version-larga.html se quedan
# en la carpeta como historial, pero no salen a internet ni se revisan.
# Las paginas que se publican hoy: el portfolio, el 404 y los cuatro casos.
PAGINAS = (["index.html", "404.html"]
           + sorted(str(p.relative_to(RAIZ)).replace("\\", "/")
                    for p in (RAIZ / "trabajos").glob("*.html")))

# Desde que portfolio.html saca el JavaScript a ui/, algunos marcadores viven
# ahi y no en el HTML. Si no se miran, se publica con VIDEO_ID puesto.
# El JavaScript que carga el portfolio. pagina.js, consola.js y revelar.js
# eran de la web de candidatura y ya no existen.
FUENTES = ["ui/plantilla.js", "ui/fondo.js", "ui/mapa.js"]

# VIDEO_ID y ENLACE_ALTERNATIVO eran del video de Loom de la campana. Fuera.
MARCADORES = ["TU-DOMINIO"]

ARCHIVOS = [
    "index.html", "404.html",
    "trabajos/tfm-lead-scoring.html", "trabajos/videojuegos.html",
    "trabajos/apuestas.html", "trabajos/lipton.html",
    "trabajos/lipton-summer-shake-up.pdf",
    "medios/video/videojuegos.mp4", "medios/video/apuestas.mp4",
    "medios/video/lipton.mp4", "medios/informes/lipton-portada.jpg",
    "medios/og.jpg", "medios/hero.jpg", "medios/retrato.jpg",
    "medios/cv-pedro-perez-blanco-es.pdf",
    "medios/cv-pedro-perez-blanco-en.pdf",
    "favicon.ico", "favicon.svg", "apple-touch-icon.png",
    "tipos/barlow-condensed-400.woff2",
    "tipos/barlow-condensed-600.woff2",
    "tipos/barlow-400.woff2",
    "tipos/plex-mono-400.woff2",
    "ui/tipos.css", "ui/plantilla.css", "ui/trabajo.css",
    "ui/plantilla.js", "ui/fondo.js", "ui/mapa.js",
]

# Las paginas que alguien puede compartir. El 404 no: nadie pega el enlace de
# una pagina de error en LinkedIn, y exigirle tarjeta de Open Graph solo
# genera ruido en este informe.
COMPARTIBLES = [x for x in PAGINAS if x != "404.html"]

# etiqueta -> paginas donde tiene que estar
META = {
    'name="viewport"': PAGINAS,
    'name="description"': PAGINAS,
    'name="robots"': PAGINAS,
    'name="theme-color"': PAGINAS,
    'rel="icon"': PAGINAS,
    'rel="apple-touch-icon"': PAGINAS,
    'property="og:title"': COMPARTIBLES,
    'property="og:image"': COMPARTIBLES,
    'property="og:image:alt"': COMPARTIBLES,
    'property="og:url"': COMPARTIBLES,
    'name="twitter:card"': ["index.html", "tech.html"],
}


# Patrones que no deben aparecer nunca en las paginas publicadas.
# El motivo de cada uno esta en SEGURIDAD.md.
PROHIBIDO = [
    (re.compile(r"<\w+[^>]*\son(click|error|load|mouseover|focus)\s*=", re.I),
     "manejador de eventos en linea (onclick=...): la CSP lo bloquea y es por donde entra el codigo inyectado"),
    (re.compile(r"\.innerHTML\s*="),
     "innerHTML: usa textContent, que no interpreta etiquetas"),
    (re.compile(r"document\.write\s*\("),
     "document.write"),
    (re.compile(r"\beval\s*\(") ,
     "eval"),
    (re.compile(r'src\s*=\s*["\']http://'),
     "recurso por http sin cifrar (contenido mixto)"),
    (re.compile(r'<script[^>]*\ssrc\s*=\s*["\'](?!/)[^"\']*//'),
     "script cargado de otro dominio: si les entran a ellos, te entran a ti"),
    (re.compile(r"href\s*=\s*[\"']javascript:", re.I),
     "enlace javascript:"),
]


class Analizador(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.enlaces = []
        self.img_sin_alt = 0
        self.iframes_sin_titulo = 0
        self.h1 = 0
        self.tiene_main = False
        self.tiene_lang = False

    def handle_starttag(self, etiqueta, atributos):
        a = dict(atributos)
        if etiqueta == "a" and "href" in a:
            self.enlaces.append((a["href"], a.get("target"), a.get("rel", "")))
        elif etiqueta == "img" and not a.get("alt") and a.get("alt") != "":
            self.img_sin_alt += 1
        elif etiqueta == "iframe" and not a.get("title"):
            self.iframes_sin_titulo += 1
        elif etiqueta == "h1":
            self.h1 += 1
        elif etiqueta == "main":
            self.tiene_main = True
        elif etiqueta == "html" and a.get("lang"):
            self.tiene_lang = True


def main():
    problemas = []
    avisos = []

    # --- archivos que tienen que estar ---
    for rel in ARCHIVOS:
        if not (RAIZ / rel).exists():
            problemas.append(f"falta el archivo {rel}")

    hero = RAIZ / "medios" / "hero.jpg"
    if hero.exists() and hero.stat().st_size < 20_000:
        avisos.append("medios/hero.jpg pesa muy poco: ¿se ha regenerado bien?")

    for pagina in PAGINAS:
        ruta = RAIZ / pagina
        if not ruta.exists():
            continue
        texto = ruta.read_text(encoding="utf-8")

        # --- marcadores ---
        # El dominio AVISA pero no cuenta como problema: la web funciona sin
        # el, y solo afecta a la tarjeta de Open Graph. Antes bloqueaba, que
        # es herencia de cuando publicar dependia de tener un video grabado.
        for marcador in MARCADORES:
            if marcador in texto:
                avisos.append(f"{pagina}: queda el marcador {marcador}")

        # --- etiquetas obligatorias ---
        for etiqueta, donde in META.items():
            if pagina in donde and etiqueta not in texto:
                problemas.append(f"{pagina}: falta <meta/link {etiqueta}>")

        # --- nada de tipografias pedidas fuera ---
        if "fonts.googleapis.com" in texto or "fonts.gstatic.com" in texto:
            problemas.append(f"{pagina}: pide tipografias a Google; deben servirse desde tipos/")

        # --- seguridad ---
        for patron, motivo in PROHIBIDO:
            if patron.search(texto):
                problemas.append(f"{pagina}: {motivo}")

        # El parametro ?e= viene de la URL: si se busca en la tabla sin
        # hasOwnProperty, ?e=constructor pinta una funcion en la portada.
        if "empresas[clave]" in texto and "hasOwnProperty" not in texto:
            problemas.append(f"{pagina}: el parámetro ?e= se busca sin hasOwnProperty")

        # --- estructura ---
        a = Analizador()
        a.feed(texto)

        if a.h1 != 1:
            problemas.append(f"{pagina}: tiene {a.h1} <h1>, debe haber exactamente uno")
        if not a.tiene_main:
            problemas.append(f"{pagina}: no hay <main>")
        if not a.tiene_lang:
            problemas.append(f"{pagina}: <html> sin lang")
        if a.img_sin_alt:
            problemas.append(f"{pagina}: {a.img_sin_alt} <img> sin alt")
        if a.iframes_sin_titulo:
            problemas.append(f"{pagina}: {a.iframes_sin_titulo} <iframe> sin title")

        # --- enlaces ---
        for href, target, rel in a.enlaces:
            if href.startswith(("http://", "https://")):
                if target == "_blank" and "noopener" not in rel:
                    problemas.append(f"{pagina}: {href} abre pestaña sin rel=noopener")
            elif href.startswith("#"):
                ancla = href[1:]
                if ancla and f'id="{ancla}"' not in texto:
                    problemas.append(f"{pagina}: el ancla {href} no existe")
            elif href.startswith(("tel:", "mailto:")):
                if href.startswith("tel:") and not re.fullmatch(r"tel:\+?[0-9]+", href):
                    problemas.append(f"{pagina}: teléfono con formato raro: {href}")
            elif href == "/":
                pass
            else:
                # RELATIVO A SU PAGINA, no a la raiz. Desde que las paginas de
                # trabajos/ entraron en la lista, resolver todo contra la raiz
                # daba por roto cada "../index.html", que es correcto.
                destino = (RAIZ / pagina).parent / href.split("?")[0].split("#")[0]
                if not destino.exists():
                    problemas.append(f"{pagina}: el enlace {href} no lleva a ningún archivo")

    # --- marcadores en el JavaScript de ui/ ---
    for fuente in FUENTES:
        ruta = RAIZ / fuente
        if not ruta.exists():
            continue
        texto = ruta.read_text(encoding="utf-8")
        for marcador in MARCADORES:
            if marcador in texto:
                problemas.append(f"{fuente}: queda el marcador {marcador}")

    # --- informe ---
    if problemas:
        print(f"{len(problemas)} cosas que arreglar:\n")
        for p in problemas:
            print(f"  · {p}")
    else:
        print("Sin problemas.")

    if avisos:
        print("\nAvisos (no bloquean):\n")
        for a in avisos:
            print(f"  · {a}")

    print("\nEsto no lo puede ver un script, míralo tú:")
    print("  · que los tres vídeos de portada se reproducen, en móvil y en escritorio")
    print("  · que el QR escanea con el móvil")
    print("  · que los enlaces de los trabajos abren y se leen")
    print("  · que la tarjeta og.jpg sale bien al pegar el enlace en LinkedIn o WhatsApp")

    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
