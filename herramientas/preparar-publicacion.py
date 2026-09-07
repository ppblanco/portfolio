# -*- coding: utf-8 -*-
"""
Monta la carpeta publicar/ con el portfolio y nada mas.

Por que existe este paso: en esta carpeta conviven la web publicable, el
material de partida de Pedro (originales/, con la memoria del TFM dentro),
el repositorio ajeno que se usa de referencia y las notas internas. Subir la
carpeta entera a Netlify dejaria todo eso colgado de una URL publica. Asi que
se arma una copia limpia con una LISTA BLANCA: lo que no este apuntado aqui,
no sale.

QUE SE PUBLICA (01/09/2026): index.html, el portfolio, y sus cuatro
paginas de caso en trabajos/. Antes se publicaba index.html, la web de la
campana de candidatura; ese concepto se abandono y la pagina se borro.

Uso:
    python herramientas/preparar-publicacion.py

Luego se arrastra la carpeta publicar/ a https://app.netlify.com/drop
"""

import base64
import hashlib
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Por defecto el paquete se monta en publicar/, al lado de las fuentes.
#
# Se puede mandar a otro sitio con  --destino RUTA , y hay un motivo real:
# esta carpeta vive dentro de OneDrive, y OneDrive convierte publicar/ en un
# marcador de "Archivos a petición" (reparse point 0x9000E01A). Con eso
# puesto, shutil.rmtree revienta con PermissionError sobre la propia carpeta
# y el paquete no se puede regenerar. NO es un enlace simbolico y no hay
# destino que arreglar: es un marcador de nube.
#
# La salida limpia es montar el paquete FUERA del arbol de OneDrive:
#
#   py herramientas/preparar-publicacion.py --destino C:/ruta/local/publicar
#
# Lo que se sube es esa carpeta, con --dir apuntando a ella.
DESTINO = RAIZ / "publicar"

# Lo que sale a internet. Lo que no este aqui, no se sube.
PUBLICOS = [
    # El portfolio. Es la portada del sitio: se sirve en / y es el enlace que
    # va en el CV y en LinkedIn.
    "index.html",
    "404.html",
    # Los iconos van en la raiz por convencion: el navegador pide /favicon.ico
    # sin preguntar, aunque el HTML diga otra cosa.
    "favicon.ico",
    "favicon.svg",
    "apple-touch-icon.png",
]

OPCIONALES = set()

# Carpetas que se copian enteras. medios/ lleva las imagenes y el CV.
#
# LAS QUE NO ESTAN AQUI NO SE COPIAN, y eso es la mitad de la seguridad de
# este script: originales/ (el material de partida y la memoria del TFM),
# referencias/ (capturas de estudio y el repositorio ajeno descargado),
# herramientas/, pruebas/, documentacion/ y archivo/ no salen nunca porque
# nadie las ha apuntado, no porque haya una regla que las excluya. Anadir una
# carpeta a esta lista es una decision, no un tramite.
CARPETAS = ["tipos", "ui", "trabajos", "medios"]

# Lo que NO sube aunque este dentro de esas carpetas.
#
# Hasta el 01/09/2026 esta lista era larguisima: excluia el CSS, el
# JavaScript, los videos y las fotos del portfolio, porque lo que se publicaba
# era index.html. Al pasar el portfolio a version principal, casi todo eso
# entra y aqui solo queda lo que de verdad sobra.
#
# ANTES DE QUITAR ALGO DE ESTA LISTA, MIRAR QUE HAY DENTRO. Las carpetas se
# copian enteras: sube todo lo que haya, lo use la pagina o no. El 27/08/2026
# habia en medios/fotos/ dos archivos sueltos —una foto de familia y un
# original de 2,5 MB, ninguno referenciado— y se borraron. Publicar por
# descuido la cara de gente que no ha decidido nada no es un descuido
# cualquiera: comparar la carpeta con los src de las paginas.
SIN_PUBLICAR = [
    # Notas internas. Nunca.
    "*.md",
    # Los rectangulos grises de relleno de la primera maqueta. La carpeta ya
    # no existe; la entrada se queda por si alguien vuelve a generarlos.
    "marcadores",
]

# Lo que falta por rellenar. AVISA, pero YA NO IMPIDE PUBLICAR.
#
# VIDEO_ID y ENLACE_ALTERNATIVO se fueron con el concepto de candidatura: eran
# el video de Loom de 90 segundos y su copia de respaldo, y un portfolio no
# los necesita. Mientras estuvieron aqui, no tener grabado ese video bloqueaba
# el empaquetado entero, que es una herencia absurda de un objetivo que ya no
# existe.
#
# TU-DOMINIO se queda, pero solo como aviso: sin dominio las etiquetas de
# Open Graph apuntan a ninguna parte y la tarjeta de LinkedIn sale sin imagen.
# La web funciona igual, asi que no es motivo para no poder empaquetarla y
# probarla en Netlify.
MARCADORES = {
    "TU-DOMINIO": "la URL real del sitio (solo afecta a la tarjeta de Open Graph)",
}

ROBOTS = "User-agent: *\nAllow: /\n"

# Cabeceras que valen para todo el sitio.
COMUNES = [
    # SAMEORIGIN y no DENY, y el motivo importa: esta linea la hereda TODO lo
    # que se sirve, los PDF incluidos, y los visores de las paginas de caso
    # meten el PDF en un <iframe> del propio sitio. Con DENY el navegador se
    # negaba a pintarlo y salia "refused to connect" en produccion. En local
    # no se veia: el servidor de pruebas no manda cabeceras.
    #
    # Las paginas HTML NO se aflojan. Siguen con "frame-ancestors 'none'" en
    # su propia CSP, que es la directiva moderna, gana sobre X-Frame-Options
    # y prohibe empotrarlas hasta desde aqui mismo. Lo que se afloja es solo
    # lo que no lleva CSP propia -los documentos-, y solo para el mismo
    # origen: otro dominio sigue sin poder incrustarlos.
    "X-Frame-Options: SAMEORIGIN",
    "X-Content-Type-Options: nosniff",
    "Referrer-Policy: strict-origin-when-cross-origin",
    "Strict-Transport-Security: max-age=31536000; includeSubDomains",
    "Cross-Origin-Opener-Policy: same-origin",
    # Nada de camara, microfono ni ubicacion. autoplay SI se permite al propio
    # sitio, y no es un detalle: los tres videos de portada los arranca
    # plantilla.js con play(), y con autoplay=() la politica los bloquearia y
    # las portadas se quedarian en el poster para siempre.
    'Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
    'magnetometer=(), microphone=(), payment=(), usb=(), '
    'fullscreen=(self), autoplay=(self)',
]

# La CSP se calcula a partir del propio HTML: si editas una pagina, los hashes
# se recalculan solos al volver a empaquetar. Si se escribieran a mano, el dia
# que tocaras el CSS la pagina se quedaria sin estilos en produccion.
PLANTILLA_CSP = (
    "default-src 'none'; "
    "script-src {scripts}; "
    "style-src {estilos}; "
    # Los atributos style= y lo que el JavaScript escribe en element.style no
    # los cubre `style-src`: para eso esta `style-src-attr`. Sin esta linea el
    # navegador los descarta en silencio y se cayeron las animaciones
    # escalonadas —las seis paradas del TFM se encendian a la vez— y parte de
    # lo que hace ui/plantilla.js. Permite atributos de estilo, no scripts.
    "style-src-attr 'unsafe-inline'; "
    "font-src 'self'; "
    "img-src {imagenes}; "
    # Los tres videos de portada. Con default-src 'none' y sin esta linea, el
    # navegador los bloquea sin decir nada y las portadas se quedan en el
    # poster: el fallo mas silencioso que puede tener este paquete.
    "media-src 'self'; "
    # El visor del informe de Lipton mete el PDF en un <iframe> del propio
    # sitio. Antes aqui iba el dominio de Loom, que ya no pinta nada.
    "frame-src 'self'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'; "
    "upgrade-insecure-requests"
)

RE_SCRIPT = re.compile(r"<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>", re.S)
RE_ESTILO = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
# Recursos propios en archivo aparte: <script src="ui/..."> y <link rel=stylesheet>.
# Solo cuentan los relativos; uno de otro dominio tendria que ir con su origen.
RE_SCRIPT_PROPIO = re.compile(r'<script[^>]*\ssrc=["\'](?!https?:|//)[^"\']+["\']', re.I)
RE_ESTILO_PROPIO = re.compile(r'<link[^>]*rel=["\']stylesheet["\'][^>]*>', re.I)


def hash_csp(contenido):
    resumen = hashlib.sha256(contenido.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(resumen).decode("ascii") + "'"


def csp_de(texto):
    """Construye la CSP de una pagina a partir de lo que esa pagina usa.

    Las paginas viejas llevan el CSS y el JS dentro del HTML, y se
    autorizan por huella. portfolio.html los tiene en ui/, y esos se
    autorizan con 'self'. Cada pagina recibe la suya, la minima.
    """
    # dict.fromkeys quita repetidos sin perder el orden: nbconvert deja
    # varios <style> identicos y salian cuatro veces el mismo hash.
    fuentes_script = list(dict.fromkeys(hash_csp(b) for b in RE_SCRIPT.findall(texto)))
    fuentes_estilo = list(dict.fromkeys(hash_csp(b) for b in RE_ESTILO.findall(texto)))

    if RE_SCRIPT_PROPIO.search(texto):
        fuentes_script.append("'self'")
    if RE_ESTILO_PROPIO.search(texto):
        fuentes_estilo.append("'self'")

    # Las paginas de los cuadernos llevan los graficos incrustados como
    # data:. Sin esto, 'self' los bloquea y se quedan sin ni un dibujo.
    imagenes = ["'self'"]
    if re.search(r'src=["\']data:image', texto):
        imagenes.append("data:")

    return PLANTILLA_CSP.format(
        scripts=" ".join(fuentes_script) if fuentes_script else "'none'",
        estilos=" ".join(fuentes_estilo) if fuentes_estilo else "'none'",
        imagenes=" ".join(imagenes),
    )


def meter_csp_en_404(ruta):
    """Mete la CSP de la 404 DENTRO de la propia pagina, en un <meta>.

    La regla del _headers va por ruta: "/404.html" le pone su CSP a esa URL
    concreta. Pero un 404 de verdad no ocurre en /404.html, ocurre en la
    direccion que alguien se ha inventado, y ahi esa regla no casa: Netlify
    sirve el cuerpo de la 404 con las cabeceras comunes y sin CSP.

    Ponerla en /* no vale: cada pagina lleva la suya con sus hashes, y dos
    cabeceras CSP se aplican a la vez quedandose con la interseccion, o sea
    que romperia todas las demas paginas.

    Un <meta http-equiv> viaja dentro del documento, asi que vale en
    cualquier direccion. En meta se ignoran frame-ancestors y report-uri, de
    modo que frame-ancestors se quita: esa la sigue dando la cabecera
    X-Frame-Options, que si viaja en todas las respuestas.
    """
    texto = ruta.read_text(encoding="utf-8")
    politica = "; ".join(
        d.strip() for d in csp_de(texto).split(";")
        if d.strip() and not d.strip().startswith("frame-ancestors"))
    etiqueta = ('<meta http-equiv="Content-Security-Policy" '
                f'content="{politica}">\n')
    marca = '<meta charset="utf-8">' + '\n'
    ruta.write_text(texto.replace(marca, marca + etiqueta, 1), encoding="utf-8")


def construir_cabeceras(paginas):
    lineas = ["/*"]
    lineas += [f"  {c}" for c in COMUNES]
    lineas.append("")

    lineas.append("# Content Security Policy, una por pagina: los hashes son de")
    lineas.append("# sus bloques <script> y <style> en linea. No editar a mano.")
    for ruta, csp in paginas:
        lineas.append(ruta)
        lineas.append(f"  Content-Security-Policy: {csp}")
        lineas.append("")

    # El sitio se indexa, pero el CV no. Un PDF no puede llevar
    # <meta robots>, asi que su noindex tiene que venir por cabecera.
    for cv in ("/medios/cv-pedro-perez-blanco-es.pdf",
               "/medios/cv-pedro-perez-blanco-en.pdf"):
        lineas.append(cv)
        lineas.append("  X-Robots-Tag: noindex")
        lineas.append("")

    lineas.append("# Las tipografias llevan el peso en el nombre: si cambian, cambia el")
    lineas.append("# nombre. Por eso se pueden cachear un ano entero.")
    lineas.append("/tipos/*")
    lineas.append("  Cache-Control: public, max-age=31536000, immutable")
    return "\n".join(lineas) + "\n"


def revisar_marcadores():
    """Mira los archivos que de verdad se publican, no una lista fija.

    La version anterior miraba index.html y ui/pagina.js a pelo. Al cambiar
    la pagina principal eso habria dejado de comprobar nada sin avisar, que es
    la peor forma de que una comprobacion deje de servir.
    """
    pendientes = []
    revisables = [RAIZ / n for n in PUBLICOS]
    revisables += sorted((RAIZ / "trabajos").glob("*.html"))
    for ruta in revisables:
        if not ruta.exists() or ruta.suffix != ".html":
            continue
        texto = ruta.read_text(encoding="utf-8")
        for marcador, que_es in MARCADORES.items():
            if marcador in texto:
                pendientes.append((ruta.name, marcador, que_es))
    return pendientes


def main():
    forzar = "--forzar" in sys.argv

    faltan = [p for p in PUBLICOS if p not in OPCIONALES and not (RAIZ / p).exists()]
    if faltan:
        print("Faltan archivos que tienen que existir: " + ", ".join(faltan))
        return 1

    # Los marcadores AVISAN, no bloquean. Ver el comentario de MARCADORES: el
    # unico que queda afecta a la tarjeta de Open Graph, y una web que
    # funciona entera no puede quedarse sin empaquetar por eso.
    pendientes = revisar_marcadores()
    if pendientes:
        print("Aviso: quedan marcadores sin rellenar.\n")
        vistos = set()
        for nombre, marcador, que_es in pendientes:
            if marcador not in vistos:
                vistos.add(marcador)
                print(f"  {marcador:<20} -> {que_es}")
        print("\n  El paquete se genera igual: la web funciona sin eso.")
        print("  Para rellenarlos: python herramientas/rellenar.py\n")

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir()

    for nombre in PUBLICOS:
        origen = RAIZ / nombre
        if not origen.exists():
            print(f"  (salto {nombre}, no existe todavia)")
            continue
        shutil.copy2(origen, DESTINO / nombre)
        if nombre == "404.html":
            meter_csp_en_404(DESTINO / nombre)
        print(f"  + {nombre}")

    for carpeta in CARPETAS:
        origen = RAIZ / carpeta
        if not origen.is_dir():
            print(f"Falta la carpeta {carpeta}/. Ejecuta herramientas/hacer-tipos.py")
            return 1
        shutil.copytree(origen, DESTINO / carpeta,
                        ignore=shutil.ignore_patterns(*SIN_PUBLICAR))
        cuantos = len(list((DESTINO / carpeta).iterdir()))
        print(f"  + {carpeta}/ ({cuantos} archivos)")

    # El sitio es publico y se deja rastrear.
    (DESTINO / "robots.txt").write_text(ROBOTS, encoding="utf-8")

    # De PUBLICOS, no de una lista escrita a mano: si cambia la pagina
    # principal, esto cambia con ella en vez de dejar de comprobar en silencio.
    paginas = []
    for nombre in PUBLICOS:
        if not nombre.endswith(".html"):
            continue
        csp = csp_de((DESTINO / nombre).read_text(encoding="utf-8"))
        paginas.append(("/" + nombre, csp))
        if nombre == "index.html":
            paginas.append(("/", csp))  # la portada se sirve por las dos rutas

    # Las paginas de los cuadernos: mismo trato, cada una con la suya.
    carpeta_trabajos = DESTINO / "trabajos"
    if carpeta_trabajos.is_dir():
        for pagina in sorted(carpeta_trabajos.glob("*.html")):
            paginas.append(("/trabajos/" + pagina.name,
                            csp_de(pagina.read_text(encoding="utf-8"))))

    (DESTINO / "_headers").write_text(construir_cabeceras(paginas), encoding="utf-8")
    print(f"  + robots.txt\n  + _headers (CSP de {len(paginas)} rutas)")

    print(f"\nListo: {DESTINO}")
    print("Arrastra esa carpeta a https://app.netlify.com/drop")
    print("Despues, con la URL ya real: python herramientas/hacer-qr.py --base https://LA-URL")
    return 0


if __name__ == "__main__":
    if "--destino" in sys.argv:
        DESTINO = Path(sys.argv[sys.argv.index("--destino") + 1]).resolve()
        print(f"Destino: {DESTINO}\n")
    raise SystemExit(main())
