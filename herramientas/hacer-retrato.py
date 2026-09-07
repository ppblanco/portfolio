# -*- coding: utf-8 -*-
"""
Prepara el retrato para la web a partir de FOTO MIA.png.

Se hizo una versión con viñeteado y color frío para fundirla con el fondo negro,
y quedaba oscura por zonas. Pedro la quiere natural, así que este script hace
solo lo imprescindible:

  · Recorta a 4:5 centrado en la cara, que está en el tercio superior.
  · Reduce a tamaño web.

Nada de grados de color, nada de viñeteado. Es la foto tal cual, y a 92 píxeles
dentro del panel se lee como lo que es: una foto de carnet.

Uso:  python herramientas/hacer-retrato.py
"""

from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "originales" / "imagenes" / "FOTO MIA.png"
SALIDA = RAIZ / "medios" / "retrato.jpg"

ANCHO, ALTO = 720, 900          # 4:5
ALTURA_CARA = 0.40              # dónde cae la cara, de arriba abajo


def recortar(img):
    """Recorte 4:5 con la cara en el primer tercio, no en el centro."""
    objetivo = ANCHO / ALTO
    a, b = img.size
    actual = a / b

    if actual > objetivo:                     # sobra por los lados
        nueva_a = int(b * objetivo)
        izq = (a - nueva_a) // 2
        img = img.crop((izq, 0, izq + nueva_a, b))
    else:                                     # sobra por arriba y abajo
        nueva_b = int(a / objetivo)
        # No se centra: se deja más aire abajo para que la cara suba.
        arriba = int((b - nueva_b) * ALTURA_CARA)
        arriba = max(0, min(arriba, b - nueva_b))
        img = img.crop((0, arriba, a, arriba + nueva_b))

    return img.resize((ANCHO, ALTO), Image.LANCZOS)


def main():
    if not ORIGEN.exists():
        print(f"No encuentro {ORIGEN.name}")
        return 1

    img = Image.open(ORIGEN).convert("RGB")
    print(f"original: {img.size[0]}x{img.size[1]}")

    img = recortar(img)
    img.save(SALIDA, "JPEG", quality=90, optimize=True, progressive=True)

    kb = SALIDA.stat().st_size / 1024
    medio = float(np.asarray(img).mean()) / 255 * 100
    print(f"escrito {SALIDA.name}  {ANCHO}x{ALTO}  {kb:.0f} KB  luminancia media {medio:.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
