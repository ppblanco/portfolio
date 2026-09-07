# -*- coding: utf-8 -*-
"""
Genera los QR de la web, en PNG (pantalla y email) y SVG (imprenta).

Hay un sitio y una URL. De ahi salen dos clases de codigo:

  qr-web        -> la URL a secas. Este es el que va en el CV, en LinkedIn y
                   en cualquier sitio donde no sepas quien lo va a escanear.
  (Antes habia ademas un qr-<empresa> por cada empresa de la campana, con su
   ?e=. Se fue con ese concepto: un portfolio tiene una URL y ya.)

Uso:
    python herramientas/hacer-qr.py --base https://pedroperezblanco.com

Si tienes enlaces cortos del acortador, pasalos y el QR apunta al corto:

    python herramientas/hacer-qr.py --base https://... --cortos cortos.json

donde cortos.json es {"web": "https://...", "merkle": "https://...", ...}.

Los modulos van oscuros sobre blanco a proposito: es lo que leen todos los
lectores. Un QR blanco sobre negro falla en muchos moviles.
"""

import argparse
import json
from pathlib import Path

import segno

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "qr"

# Aqui habia un diccionario con las cinco empresas de la campana, para generar
# un QR por cada una con su ?e= y saber quien escaneaba. Ese concepto se
# abandono: esto es un portfolio, y solo hace falta UN codigo, el que va en el
# CV y en LinkedIn.
EMPRESAS = {}


def main():
    p = argparse.ArgumentParser(description="Genera los QR de la web.")
    p.add_argument("--base", default="https://TU-DOMINIO",
                   help="URL de la web, sin barra final.")
    p.add_argument("--cortos", help="JSON {clave: enlace_corto} del acortador.")
    p.add_argument("--escala", type=int, default=24,
                   help="Pixeles por modulo en el PNG (24 ~ 1000px de lado).")
    p.add_argument("--invertido", action="store_true",
                   help="Blanco sobre negro. Solo sobre soporte oscuro y probandolo antes.")
    args = p.parse_args()

    if "TU-DOMINIO" in args.base:
        print("AVISO: estas usando el dominio de relleno. Los QR no llevaran a ningun sitio.\n")

    cortos = {}
    if args.cortos:
        cortos = json.loads(Path(args.cortos).read_text(encoding="utf-8"))

    SALIDA.mkdir(exist_ok=True)
    oscuro, claro = ("#ffffff", "#000000") if args.invertido else ("#000000", "#ffffff")
    base = args.base.rstrip("/")

    destinos = [("web", "Para el CV y para compartir", f"{base}/")]
    destinos += [(c, n, f"{base}/?e={c}") for c, n in EMPRESAS.items()]

    filas = []
    for clave, nombre, url in destinos:
        codificado = cortos.get(clave, url)

        # error='h': aguanta hasta un 30% del codigo danado. Para papel importa.
        qr = segno.make(codificado, error="h")
        qr.save(SALIDA / f"qr-{clave}.png", scale=args.escala, border=4,
                dark=oscuro, light=claro)
        qr.save(SALIDA / f"qr-{clave}.svg", scale=10, border=4,
                dark=oscuro, light=claro)

        filas.append((clave, nombre, codificado, qr.designator))
        print(f"{clave:<14} {codificado}")

    indice = SALIDA / "enlaces.csv"
    with indice.open("w", encoding="utf-8", newline="") as f:
        f.write("clave,para,url,qr_version,png,svg\n")
        for clave, nombre, url, designador in filas:
            f.write(f"{clave},{nombre},{url},{designador},qr-{clave}.png,qr-{clave}.svg\n")

    print(f"\n{len(filas)} QR en {SALIDA}")
    print(f"Indice en {indice}")
    print("\nEl del CV es qr-web.svg: en vectorial no se pixela al imprimir.")
    print("Escanea los seis con el movil antes de mandar nada. Uno por uno.")


if __name__ == "__main__":
    main()
