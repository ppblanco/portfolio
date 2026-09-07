# -*- coding: utf-8 -*-
"""
ATENCION: HOY ESTE SCRIPT NO LO USA NADIE (02/09/2026).

Generaba las portadas de las fichas de proyecto a partir de las figuras de los
cuadernos, en dos juegos —claro y oscuro—. Los dos han desaparecido: el claro
se fue con version-clara.html, y el oscuro cuando Pedro puso sus propias fotos
en las cuatro fichas. medios/portadas/ ya no existe.

Se conserva porque es la unica forma de volver a sacar esas portadas de los
notebooks, y rehacerlo desde cero seria un rato largo. Si dentro de unos meses
sigue sin usarse, borralo sin remordimientos.

Saca una imagen de portada para cada trabajo, a partir de material real.

Los proyectos de la web eran solo texto y cifras, y eso hace que la página
parezca un documento en vez de un portfolio. Cada ficha necesita una imagen, y
la imagen tiene que salir del propio trabajo: un gráfico inventado sería
decorar, y decorar con datos falsos en una web que presume de datos reales es
justo lo que no se puede hacer.

De dónde sale cada una:
  · videojuegos y apuestas -> un gráfico de su propio notebook, ya renderizado
  · lipton                 -> una página de la presentación
  · tfm                    -> la nube de puntos del modelo, sobre fondo claro

Uso:  python herramientas/hacer-portadas.py
"""

import base64
import io
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "medios" / "portadas"
DESTINO_OSCURO = DESTINO / "oscuras"


def destino(oscuro=False):
    return DESTINO_OSCURO if oscuro else DESTINO

ANCHO, ALTO = 1000, 620          # 16:10, el formato de las tarjetas


# La version clara vive sobre #FAFAF9 y la del portfolio sobre #0B0C0F. Una
# portada pensada para fondo claro puesta sobre la negra es una losa blanca que
# deslumbra, asi que hay dos juegos: medios/portadas/ y medios/portadas/oscuras/.
CLARO = (255, 255, 255)
OSCURO = (19, 21, 25)


def encajar(img, fondo=CLARO):
    """Mete la imagen en el marco sin recortarla ni deformarla."""
    img = img.convert("RGB")
    escala = min(ANCHO / img.width, ALTO / img.height)
    nueva = img.resize((max(1, int(img.width * escala)), max(1, int(img.height * escala))),
                       Image.LANCZOS)
    lienzo = Image.new("RGB", (ANCHO, ALTO), fondo)
    lienzo.paste(nueva, ((ANCHO - nueva.width) // 2, (ALTO - nueva.height) // 2))
    return lienzo


def franja(img, alto, desde=0.0):
    """Recorta una banda horizontal, en fracciones de la altura.

    Hace falta porque una figura vertical metida en un marco 16:10 se encoge
    hasta ser un hilo con dos bandas blancas a los lados: en la tarjeta se lee
    como un recuadro vacío. Recortando la parte que importa, lo que queda
    ocupa el marco y se ve.
    """
    y0 = int(img.height * desde)
    y1 = min(img.height, y0 + int(img.height * alto))
    return img.crop((0, y0, img.width, y1))


def invertir_luz(img):
    """Da la vuelta a la luz de una figura sin cambiarle los colores.

    El SHAP viene cocido dentro del cuaderno como PNG con fondo blanco: no hay
    forma de volver a dibujarlo en oscuro. Invertirlo a secas sí lo oscurece,
    pero también gira el tono: los puntos rojos salen verdes y los azules
    naranjas, y en un SHAP el color ES el dato —rojo es valor alto, azul es
    valor bajo—. Un gráfico con la leyenda invertida miente.

    Así que se invierte y luego se gira el tono media vuelta, que deshace
    exactamente el giro que provocó la inversión. Resultado: el blanco pasa a
    negro, el texto negro pasa a blanco, y el rojo sigue siendo rojo.
    """
    from PIL import ImageOps

    invertida = ImageOps.invert(img.convert("RGB")).convert("HSV")
    h, s, v = invertida.split()
    h = h.point(lambda p: (p + 128) % 256)
    return Image.merge("HSV", (h, s, v)).convert("RGB")


def de_notebook(ruta, indice, salida, recorte=None, oscuro=False):
    """Coge la figura número `indice` de las que ya están guardadas como PNG."""
    nb = json.loads((RAIZ / ruta).read_text(encoding="utf-8"))
    encontradas = []
    for celda in nb.get("cells", []):
        for s in celda.get("outputs", []):
            d = s.get("data") or {}
            if "image/png" in d:
                encontradas.append(d["image/png"])
    if not encontradas:
        print(f"  {salida}: ese notebook no tiene ninguna figura guardada")
        return False
    i = min(indice, len(encontradas) - 1)
    crudo = encontradas[i]
    if isinstance(crudo, list):
        crudo = "".join(crudo)
    img = Image.open(io.BytesIO(base64.b64decode(crudo)))
    if recorte:
        img = franja(img, *recorte)
    if oscuro:
        img = invertir_luz(img)
    encajar(img, OSCURO if oscuro else CLARO).save(
        destino(oscuro) / salida, "JPEG", quality=86, optimize=True)
    print(f"  + {'oscuras/' if oscuro else ''}{salida}   (figura {i + 1} de {len(encontradas)})")
    return True


def de_plotly(ruta, indice, salida, oscuro=False):
    """Igual, pero para los notebooks que guardan las figuras como datos.

    Plotly no deja la imagen hecha, deja la receta. Hay que renderizarla,
    que es lo mismo que hace hacer-trabajos.py para las páginas.
    """
    import plotly.io as pio

    nb = json.loads((RAIZ / ruta).read_text(encoding="utf-8"))
    figuras = []
    for celda in nb.get("cells", []):
        for s in celda.get("outputs", []):
            d = s.get("data") or {}
            if "application/vnd.plotly.v1+json" in d:
                figuras.append(d["application/vnd.plotly.v1+json"])
    if not figuras:
        print(f"  {salida}: ese notebook no tiene figuras de Plotly")
        return False

    i = min(indice, len(figuras) - 1)
    figura = json.loads(json.dumps(figuras[i]))   # copia, no tocar el notebook

    # Algunas figuras vienen con plantilla oscura y en una web clara eso es un
    # rectángulo negro en mitad de la página. Se fuerza el fondo blanco —y con
    # él la tinta: si solo se cambia el fondo, los rótulos se quedan del gris
    # clarito que llevaban para fondo negro y desaparecen.
    TINTA, LINEA = ("#D7DAE0", "#2A2E36") if oscuro else ("#1B1F23", "#D8D8D6")
    PAPEL = "#131519" if oscuro else "white"

    def aclarar(capa):
        capa["paper_bgcolor"] = PAPEL
        capa["plot_bgcolor"] = PAPEL
        capa.setdefault("font", {})["color"] = TINTA
        for eje in ("xaxis", "yaxis"):
            e = capa.setdefault(eje, {})
            e["color"] = TINTA
            e["gridcolor"] = LINEA
            e["linecolor"] = LINEA
            e["zerolinecolor"] = LINEA
            e.setdefault("tickfont", {})["color"] = TINTA
            e.setdefault("title", {}).setdefault("font", {})["color"] = TINTA
        t = capa.setdefault("title", {})
        if isinstance(t, dict):
            t.setdefault("font", {})["color"] = TINTA

    disposicion = figura.setdefault("layout", {})
    aclarar(disposicion)
    if isinstance(disposicion.get("template"), dict):
        aclarar(disposicion["template"].setdefault("layout", {}))

    png = pio.to_image(figura, format="png", width=980, height=580, scale=2)
    encajar(Image.open(io.BytesIO(png)), OSCURO if oscuro else CLARO).save(
        destino(oscuro) / salida, "JPEG", quality=86, optimize=True)
    print(f"  + {'oscuras/' if oscuro else ''}{salida}   (figura {i + 1} de {len(figuras)}, renderizada)")
    return True


def de_pdf(ruta, salida, minimo_kb=60, oscuro=False):
    """Saca la imagen más grande incrustada en el PDF."""
    from pypdf import PdfReader
    lector = PdfReader(RAIZ / ruta)
    mejor, mejor_area = None, 0
    for pagina in lector.pages[:14]:
        try:
            for imagen in pagina.images:
                img = Image.open(io.BytesIO(imagen.data))
                if img.width * img.height > mejor_area and len(imagen.data) > minimo_kb * 1024:
                    mejor, mejor_area = img, img.width * img.height
        except Exception:
            continue
    if mejor is None:
        print(f"  {salida}: no encontré ninguna imagen aprovechable en el PDF")
        return False
    encajar(mejor, OSCURO if oscuro else CLARO).save(
        destino(oscuro) / salida, "JPEG", quality=86, optimize=True)
    print(f"  + {'oscuras/' if oscuro else ''}{salida}   ({mejor.width}x{mejor.height} del PDF)")
    return True


def nube_del_modelo(salida, oscuro=False, medida=None):
    """La misma nube de puntos de la consola 3D del sitio.

    Mismas proporciones que el test del TFM: 8,06% de A y 30,35% de A+B.
    Los leads son sintéticos, igual que en la web, y la ficha lo dice.
    """
    semilla = 4821

    def azar():
        nonlocal semilla
        semilla = (semilla * 1103515245 + 12345) & 0x7fffffff
        return semilla / 0x7fffffff

    ancho, alto = medida or (ANCHO, ALTO)

    N, PROP_A, PROP_AB = 3200, 0.0806, 0.3035
    # Dos paletas. Sobre blanco hay que oscurecer bastante; sobre negro pasa lo
    # contrario, y además las A van en el ámbar de la página para que la nube
    # diga lo mismo que el resto del sitio sin una sola palabra.
    if oscuro:
        CAT = {
            "A": ((224, 164, 88), (0.05, 0.40), 4.6),
            "B": ((150, 158, 170), (0.42, 0.74), 3.0),
            "C": ((92, 98, 108), (0.76, 1.00), 2.3),
        }
        FONDO = (11, 12, 15)
    else:
        CAT = {
            "A": ((10, 106, 128), (0.05, 0.40), 4.6),
            "B": ((92, 108, 124), (0.42, 0.74), 3.0),
            "C": ((168, 177, 186), (0.76, 1.00), 2.3),
        }
        FONDO = (250, 250, 249)

    lienzo = Image.new("RGB", (ancho * 2, alto * 2), FONDO)
    from PIL import ImageDraw
    lapiz = ImageDraw.Draw(lienzo, "RGBA")

    puntos = []
    for i in range(N):
        u = i / N
        cat = "A" if u < PROP_A else ("B" if u < PROP_AB else "C")
        d = CAT[cat][1]
        r = d[0] + azar() * (d[1] - d[0])
        th, ph = azar() * 2 * np.pi, np.arccos(2 * azar() - 1)
        puntos.append((r * np.sin(ph) * np.cos(th), r * np.cos(ph) * 0.70,
                       r * np.sin(ph) * np.sin(th), cat))

    puntos.sort(key=lambda p: p[2])
    cx, cy = ancho, alto                 # centro del lienzo, que va al doble
    # La nube está achatada por 0,70 en vertical: hay que compensarlo o queda
    # una isla pequeña en mitad del marco.
    escala, dist = (alto * 2 * 0.86) / 0.70 / 2, 3.1
    escala *= 1.6
    giro = 0.6
    cg, sg = np.cos(giro), np.sin(giro)

    for x, y, z, cat in puntos:
        x1, z1 = x * cg - z * sg, x * sg + z * cg
        persp = dist / (dist - z1)
        px, py = cx + x1 * escala * persp, cy + y * escala * persp
        color, _, base = CAT[cat]
        prof = (z1 + 1) / 2
        rad = base * persp * (0.6 + prof * 0.6)
        alfa = int(255 * (0.42 + prof * 0.52) * (1.0 if cat == "A" else 0.86))
        lapiz.ellipse([px - rad, py - rad, px + rad, py + rad], fill=color + (alfa,))

    lienzo.resize((ancho, alto), Image.LANCZOS).save(
        destino(oscuro) / salida, "JPEG", quality=88, optimize=True)
    print(f"  + {'oscuras/' if oscuro else ''}{salida}   "
          f"(nube, {N} leads sintéticos, {ancho}x{alto})")
    return True


NB_VJ = ("originales/notebooks/Trabajo ML Supervisado_Pedro_Pérez_Blanco/"
         "ML_Prediccion_Ventas_Videojuegos.ipynb")
NB_ATP = ("originales/notebooks/Trabajo Programación/"
          "EDA Ganar a la casa de apuestas.ipynb")
PDF_LIP = "originales/memorias/Lipton Campaign final.pdf"


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    DESTINO_OSCURO.mkdir(parents=True, exist_ok=True)

    print("Juego claro (ya no lo usa ninguna pagina; se conserva por si vuelve):")
    nube_del_modelo("tfm.jpg")
    # El SHAP es la figura buena del trabajo, pero es vertical y tiene veinte
    # filas. Solo el tercio de arriba —las variables que de verdad pesan—
    # cabe en el marco a un tamaño que se pueda leer.
    de_notebook(NB_VJ, 3, "videojuegos.jpg", recorte=(0.385, 0.0))
    # Antes salía la figura 6, la tarta de la mano dominante: no cuenta nada
    # del trabajo y encima Plotly le cortaba el título y la leyenda. La 8 sí es
    # la tesis del trabajo: en hierba gana el más alto casi el 58% de las veces.
    de_plotly(NB_ATP, 8, "apuestas.jpg")
    de_pdf(PDF_LIP, "lipton.jpg")

    # Juego oscuro, para index.html. Las mismas figuras con el fondo y la
    # tinta al revés: una portada pensada para fondo claro, puesta sobre la
    # página negra, es una losa blanca que deslumbra y se come la ficha.
    print("\nJuego oscuro (para index.html):")
    nube_del_modelo("tfm.jpg", oscuro=True)
    # Y una versión alta para la columna de la sección de experiencia, que
    # necesita 340×530 y no 16:10.
    nube_del_modelo("tfm-alto.jpg", oscuro=True, medida=(680, 1060))
    de_notebook(NB_VJ, 3, "videojuegos.jpg", recorte=(0.385, 0.0), oscuro=True)
    de_plotly(NB_ATP, 8, "apuestas.jpg", oscuro=True)
    de_pdf(PDF_LIP, "lipton.jpg", oscuro=True)

    archivos = list(DESTINO.rglob("*.jpg"))
    total = sum(f.stat().st_size for f in archivos)
    print(f"\n{len(archivos)} portadas, {total / 1024:.0f} KB en total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
