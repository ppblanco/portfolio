# -*- coding: utf-8 -*-
"""
Genera hero.jpg: el fondo de la portada, un campo de estrellas de verdad.

Sustituye a los cuatro puntos que hacia el CSS con radial-gradient. La diferencia
esta en lo que hace que un cielo parezca una fotografia y no un fondo de
escritorio:

  · Las estrellas no son circulos duros. Son un nucleo con halo gaussiano, que es
    como las recoge un sensor.
  · El brillo sigue una ley de potencias: muchisimas debiles y muy pocas fuertes.
    Repartirlas por igual es lo que delata a un cielo falso.
  · Tienen temperatura de color. Ni una es blanco puro: van de azuladas a
    ambar, con muy poca saturacion para no romper la sobriedad de la pagina.
  · Las mas brillantes llevan cuatro puntas tenues, el reflejo del diafragma.
  · Hay polvo de fondo a baja frecuencia y grano fino. Sin grano, la imagen se ve
    sintetica y ademas se nota el escalonado en los degradados oscuros.

El fondo arranca del mismo degradado que ya tenia el CSS (#0B0F14 arriba al
centro, a negro), asi que la imagen y el color de respaldo casan.

La luminancia se mantiene baja a proposito: encima de esto va texto blanco y
texto al 62%, y tiene que leerse.

Uso:  python herramientas/hacer-hero.py
"""

import numpy as np
from PIL import Image
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "medios" / "hero.jpg"

ANCHO, ALTO = 1920, 1200
SEMILLA = 4821  # fija: la imagen sale igual cada vez que se regenera

AZUL_NOCHE = np.array([11, 15, 20]) / 255.0   # #0B0F14, el del CSS

# Contenido a ojo: mas estrellas quedan espectaculares en la imagen suelta, pero
# encima va texto. Con 3800 el parrafo al 62% de blanco se leia mal.
N_ESTRELLAS = 2600
N_CON_PUNTAS = 9


def degradado_base():
    """El mismo radial-gradient del CSS: #0B0F14 arriba al centro, a negro."""
    y, x = np.mgrid[0:ALTO, 0:ANCHO].astype(np.float32)
    cx, cy = ANCHO * 0.5, 0.0
    rx, ry = ANCHO * 1.10, ALTO * 0.60
    t = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
    f = np.clip(t / 0.66, 0, 1)
    return (1 - f)[..., None] * AZUL_NOCHE[None, None, :]


def ruido_suave(rng, alto, ancho, celdas_y, celdas_x):
    """Ruido de baja frecuencia: se sortea pequeno y se estira con suavizado."""
    bajo = rng.random((celdas_y, celdas_x)).astype(np.float32)
    img = Image.fromarray((bajo * 255).astype(np.uint8), mode="L")
    img = img.resize((ancho, alto), Image.BICUBIC)
    return np.asarray(img).astype(np.float32) / 255.0


def polvo(rng):
    """Nebulosidad muy tenue, mas presente en la mitad de arriba."""
    a = ruido_suave(rng, ALTO, ANCHO, 7, 11)
    b = ruido_suave(rng, ALTO, ANCHO, 17, 27)
    campo = 0.65 * a + 0.35 * b
    # Elevar a una potencia deja solo las crestas: se ve como jirones, no como niebla.
    campo = np.clip((campo - 0.45) / 0.55, 0, 1) ** 2.2

    y = np.linspace(0, 1, ALTO, dtype=np.float32)[:, None]
    campo *= np.clip(1.25 - y * 1.15, 0, 1)  # se apaga hacia abajo

    tinte = np.array([0.55, 0.68, 1.0], dtype=np.float32)  # frio, azulado
    return campo[..., None] * tinte[None, None, :] * 0.030


def color_estelar(temp):
    """temp 0 = azulada, 1 = ambar. Saturacion baja a proposito."""
    frio = np.array([0.78, 0.86, 1.00])
    calido = np.array([1.00, 0.89, 0.76])
    return frio + (calido - frio) * temp


def pintar_estrellas(lienzo, rng):
    alto, ancho, _ = lienzo.shape

    # Posicion: base uniforme mas unos cuantos grumos. Un cielo perfectamente
    # uniforme no existe; la irregularidad es lo que lo hace creible.
    n_grumo = int(N_ESTRELLAS * 0.30)
    n_libre = N_ESTRELLAS - n_grumo

    xs = [rng.random(n_libre) * ancho]
    ys = [rng.random(n_libre) * alto]
    for _ in range(6):
        cx, cy = rng.random() * ancho, rng.random() * alto * 0.85
        n = n_grumo // 6
        xs.append(rng.normal(cx, ancho * 0.10, n))
        ys.append(rng.normal(cy, alto * 0.10, n))

    x = np.concatenate(xs)
    y = np.concatenate(ys)
    dentro = (x >= 0) & (x < ancho) & (y >= 0) & (y < alto)
    x, y = x[dentro], y[dentro]
    n = len(x)

    # Ley de potencias: casi todas debiles, unas pocas que mandan.
    brillo = rng.random(n) ** 4.8
    temps = rng.random(n)

    # Menos densidad abajo, que es donde en tech.html va el titular.
    guardar = rng.random(n) < np.clip(1.05 - (y / alto) * 0.55, 0, 1)
    x, y, brillo, temps = x[guardar], y[guardar], brillo[guardar], temps[guardar]

    orden = np.argsort(brillo)  # las brillantes al final, se pintan encima
    x, y, brillo, temps = x[orden], y[orden], brillo[orden], temps[orden]

    for i in range(len(x)):
        b = brillo[i]
        sigma = 0.55 + b * 1.9
        radio = int(np.ceil(sigma * 3.2)) + 1
        cx, cy = x[i], y[i]
        x0, x1 = max(0, int(cx) - radio), min(ancho, int(cx) + radio + 1)
        y0, y1 = max(0, int(cy) - radio), min(alto, int(cy) + radio + 1)
        if x1 <= x0 or y1 <= y0:
            continue

        gy, gx = np.mgrid[y0:y1, x0:x1]
        d2 = (gx - cx) ** 2 + (gy - cy) ** 2
        nucleo = np.exp(-d2 / (2 * sigma ** 2))
        # Un halo mucho mas ancho y flojo: es lo que da sensacion de luz real.
        halo = np.exp(-d2 / (2 * (sigma * 3.0) ** 2)) * 0.13
        perfil = (nucleo + halo) * (0.035 + b * 0.82)

        lienzo[y0:y1, x0:x1] += perfil[..., None] * color_estelar(temps[i])[None, None, :]

    # Las cuatro puntas del diafragma, solo en las mas fuertes y muy tenues.
    for i in range(len(x) - N_CON_PUNTAS, len(x)):
        if i < 0:
            continue
        b = brillo[i]
        largo = int(14 + b * 46)
        cx, cy = int(x[i]), int(y[i])
        col = color_estelar(temps[i])
        for d in range(1, largo):
            caida = (1 - d / largo) ** 2.4 * b * 0.22
            for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                px, py = cx + ux * d, cy + uy * d
                if 0 <= px < ancho and 0 <= py < alto:
                    lienzo[py, px] += caida * col


def vinetear(lienzo):
    y, x = np.mgrid[0:ALTO, 0:ANCHO].astype(np.float32)
    nx = (x / ANCHO - 0.5) * 2
    ny = (y / ALTO - 0.5) * 2
    r = np.sqrt(nx ** 2 + ny ** 2) / np.sqrt(2)
    return lienzo * np.clip(1.0 - (r ** 2.6) * 0.55, 0, 1)[..., None]


def main():
    rng = np.random.default_rng(SEMILLA)

    lienzo = degradado_base().astype(np.float32)
    lienzo += polvo(rng)
    pintar_estrellas(lienzo, rng)
    lienzo = vinetear(lienzo)

    # Grano fino. Sin esto se ve el escalonado del degradado en las zonas oscuras,
    # que en una pantalla buena canta mucho.
    lienzo += rng.normal(0, 0.0055, lienzo.shape).astype(np.float32)

    lienzo = np.clip(lienzo, 0, 1)
    img = Image.fromarray((lienzo * 255 + 0.5).astype(np.uint8), mode="RGB")
    img.save(SALIDA, "JPEG", quality=88, optimize=True, progressive=True, subsampling=0)

    kb = SALIDA.stat().st_size / 1024
    medio = float(np.mean(lienzo)) * 100
    print(f"Escrito {SALIDA}")
    print(f"  {ANCHO}x{ALTO} · {kb:.0f} KB · luminancia media {medio:.1f}%")
    if kb > 320:
        print("  AVISO: pesa bastante para un fondo. Baja la calidad o el tamano.")


if __name__ == "__main__":
    main()
