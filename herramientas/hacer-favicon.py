# -*- coding: utf-8 -*-
"""
Genera el favicon: una P blanca sobre negro, en Barlow Condensed SemiBold.

Saca tres archivos, que son los que hacen falta para cubrir todo:
  favicon.svg          -> navegadores modernos, nitido a cualquier tamano
  favicon.ico          -> 16/32/48, para los que aun piden .ico
  apple-touch-icon.png -> 180x180, cuando alguien guarda el enlace en el movil

La P se saca del contorno real de la fuente, no se dibuja a mano: asi el icono
y los titulares de la pagina son la misma letra.

Uso:  python herramientas/hacer-favicon.py
"""

from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = Path(__file__).resolve().parent / "fuentes"
TTF = FUENTES / "BarlowCondensed-SemiBold.ttf"

LETRA = "P"
LIENZO = 64  # el viewBox del SVG


def contorno_svg():
    """Devuelve el path de la P, escalado y centrado en un lienzo de 64x64."""
    fuente = TTFont(TTF)
    glifo_nombre = fuente.getBestCmap()[ord(LETRA)]
    conjunto = fuente.getGlyphSet()
    glifo = conjunto[glifo_nombre]

    lapiz = SVGPathPen(conjunto)
    glifo.draw(lapiz)
    d = lapiz.getCommands()

    upem = fuente["head"].unitsPerEm
    # Caja real de la letra, para centrarla de verdad y no fiarme del avance.
    xmin, ymin, xmax, ymax = fuente["glyf"][glifo_nombre].xMin, \
        fuente["glyf"][glifo_nombre].yMin, \
        fuente["glyf"][glifo_nombre].xMax, \
        fuente["glyf"][glifo_nombre].yMax

    alto = ymax - ymin
    ancho = xmax - xmin
    margen = 0.16  # aire alrededor, en proporcion del lienzo
    escala = LIENZO * (1 - 2 * margen) / max(alto, ancho)

    # El eje Y de las fuentes va al reves que el del SVG: se voltea.
    dx = LIENZO / 2 - (xmin + ancho / 2) * escala
    dy = LIENZO / 2 + (ymin + alto / 2) * escala

    fuente.close()
    return d, escala, dx, dy, upem


def escribir_svg():
    d, escala, dx, dy, _ = contorno_svg()
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LIENZO} {LIENZO}">
  <rect width="{LIENZO}" height="{LIENZO}" fill="#000"/>
  <g transform="translate({dx:.3f} {dy:.3f}) scale({escala:.6f} {-escala:.6f})">
    <path d="{d}" fill="#fff"/>
  </g>
</svg>
'''
    destino = RAIZ / "favicon.svg"
    destino.write_text(svg, encoding="utf-8")
    print(f"  + favicon.svg  ({len(svg)} bytes)")


def pintar(lado):
    """Version en pixeles, para .ico y apple-touch-icon."""
    img = Image.new("RGB", (lado, lado), (0, 0, 0))
    lapiz = ImageDraw.Draw(img)
    # 0.78 del lado deja un aire parecido al del SVG.
    fuente = ImageFont.truetype(str(TTF), int(lado * 0.78))
    caja = lapiz.textbbox((0, 0), LETRA, font=fuente)
    x = (lado - (caja[2] - caja[0])) / 2 - caja[0]
    y = (lado - (caja[3] - caja[1])) / 2 - caja[1]
    lapiz.text((x, y), LETRA, font=fuente, fill=(255, 255, 255))
    return img


def main():
    if not TTF.exists():
        print(f"Falta la fuente: {TTF}")
        return 1

    escribir_svg()

    ico = RAIZ / "favicon.ico"
    pintar(48).save(ico, sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"  + favicon.ico  ({ico.stat().st_size} bytes)")

    apple = RAIZ / "apple-touch-icon.png"
    pintar(180).save(apple, "PNG", optimize=True)
    print(f"  + apple-touch-icon.png  ({apple.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
