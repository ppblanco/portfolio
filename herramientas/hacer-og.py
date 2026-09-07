# -*- coding: utf-8 -*-
"""
Genera og.jpg (1200x630), la tarjeta que se ve cuando alguien reenvia el enlace.

Misma piel que index.html y tech.html: negro puro, texto blanco, humo al 62%,
Barlow Condensed en mayusculas con mucho tracking. Las fuentes estan en
herramientas/fuentes/ (descargadas del repo de Google Fonts, licencia OFL).

Uso:  python herramientas/hacer-og.py
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = Path(__file__).resolve().parent / "fuentes"
SALIDA = RAIZ / "medios" / "og.jpg"

ANCHO, ALTO = 1200, 630
MARGEN = 76

BLANCO = (255, 255, 255)
HUMO = (159, 159, 159)          # rgba(255,255,255,.62) sobre negro
BORDE_TENUE = (36, 36, 36)      # rgba(255,255,255,.14) sobre negro
AZUL_NOCHE = (11, 15, 20)       # #0B0F14 del gradiente del hero


def fondo():
    """Negro con el mismo gradiente radial del hero, mas campo de estrellas.

    El gradiente se calcula en pequeno y se escala: sale suave y evita
    recorrer 756.000 pixeles en Python.
    """
    cx, cy = ANCHO * 0.5, 0.0
    rx, ry = ANCHO * 1.10, ALTO * 0.60

    p_ancho, p_alto = 120, 63
    pequeno = Image.new("RGB", (p_ancho, p_alto))
    pix = pequeno.load()
    for py in range(p_alto):
        y = (py + 0.5) * ALTO / p_alto
        for px in range(p_ancho):
            x = (px + 0.5) * ANCHO / p_ancho
            t = math.hypot((x - cx) / rx, (y - cy) / ry)
            f = min(t / 0.66, 1.0)
            pix[px, py] = tuple(round(c * (1 - f)) for c in AZUL_NOCHE)

    img = pequeno.resize((ANCHO, ALTO), Image.BICUBIC)

    # Estrellas: mismo papel que los radial-gradient de 1.4px del CSS.
    estrellas = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    lapiz = ImageDraw.Draw(estrellas)
    rnd = random.Random(4821)  # semilla fija: la tarjeta sale igual cada vez
    for _ in range(46):
        x = rnd.uniform(0, ANCHO)
        y = rnd.uniform(0, ALTO * 0.82)
        r = rnd.uniform(0.9, 2.1)
        alfa = round(255 * rnd.uniform(0.16, 0.46))
        lapiz.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, alfa))

    img = Image.alpha_composite(img.convert("RGBA"), estrellas)
    return img.convert("RGB")


def cargar(nombre, tam):
    return ImageFont.truetype(str(FUENTES / nombre), tam)


def ancho_texto(lapiz, texto, fuente, tracking=0):
    if not tracking:
        return lapiz.textlength(texto, font=fuente)
    return sum(lapiz.textlength(c, font=fuente) for c in texto) + tracking * max(len(texto) - 1, 0)


def escribir(lapiz, xy, texto, fuente, color, tracking=0, anclaje="la"):
    """Dibuja texto letra a letra para poder aplicar letter-spacing."""
    x, y = xy
    if not tracking:
        lapiz.text((x, y), texto, font=fuente, fill=color, anchor=anclaje)
        return
    for c in texto:
        lapiz.text((x, y), c, font=fuente, fill=color, anchor=anclaje)
        x += lapiz.textlength(c, font=fuente) + tracking


def main():
    img = fondo()
    lapiz = ImageDraw.Draw(img)

    condensada = cargar("BarlowCondensed-SemiBold.ttf", 96)
    etiqueta = cargar("BarlowCondensed-Regular.ttf", 21)
    pie = cargar("BarlowCondensed-Regular.ttf", 19)
    cifra = cargar("BarlowCondensed-SemiBold.ttf", 74)
    corrida = ImageFont.truetype(str(FUENTES / "Barlow-Regular.ttf"), 23)

    # --- Etiqueta superior (eyebrow, tracking .34em) ---
    escribir(lapiz, (MARGEN, 68), "PEDRO PÉREZ BLANCO · ANALISTA DE MARKETING Y DATOS",
             etiqueta, HUMO, tracking=21 * 0.34)

    # --- Titular ---
    y = 128
    for linea in ("SUS LEADS NO VALEN", "TODOS LO MISMO"):
        escribir(lapiz, (MARGEN, y), linea, condensada, BLANCO, tracking=96 * 0.01)
        y += 92  # line-height .96

    # --- Entradilla ---
    lapiz.text((MARGEN, y + 46),
               "Lead scoring sobre el CRM de admisiones de la Universidad Pontificia Comillas.",
               font=corrida, fill=HUMO)

    # --- Filete ---
    y_filete = 426
    lapiz.line([(MARGEN, y_filete), (ANCHO - MARGEN, y_filete)], fill=BORDE_TENUE, width=1)

    # --- Cifras: las mismas tres de las paginas ---
    columnas = [
        ("96%", "DE LAS CONVERSIONES", "CAPTURADAS"),
        ("30%", "DE LOS LEADS", "TRABAJADOS"),
        ("×6,8", "LIFT DE LA LISTA A", "SOBRE LA MEDIA"),
    ]
    util = ANCHO - 2 * MARGEN
    paso = util / 3
    for i, (numero, l1, l2) in enumerate(columnas):
        x = MARGEN + i * paso
        escribir(lapiz, (x, y_filete + 32), numero, cifra, BLANCO, tracking=74 * 0.01)
        escribir(lapiz, (x, y_filete + 114), l1, pie, HUMO, tracking=19 * 0.2)
        escribir(lapiz, (x, y_filete + 138), l2, pie, HUMO, tracking=19 * 0.2)

    img.save(SALIDA, "JPEG", quality=92, optimize=True, progressive=True)
    print(f"Escrito {SALIDA}  ({SALIDA.stat().st_size / 1024:.0f} KB, {ANCHO}x{ALTO})")


if __name__ == "__main__":
    main()
