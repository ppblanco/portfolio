# -*- coding: utf-8 -*-
"""
Convierte las tres tipografias que usan las paginas a WOFF2 recortado al latino,
y las deja en tipos/ para servirlas desde el propio dominio.

Por que no se piden a Google:
  · La gente a la que va esto abre el enlace desde la red de su empresa. Esas
    redes bloquean cosas — el propio CLAUDE.md cuenta con ello para GA4. Si
    cae fonts.googleapis.com, la pagina entera pierde la Barlow Condensed y se
    ve con la Arial del sistema. Es justo el publico para el que no puede pasar.
  · Quita dos conexiones a otro dominio y el parpadeo de texto al cargar.
  · No sale una peticion a Google cada vez que alguien abre la pagina.

Solo se convierten los pesos que el CSS usa de verdad: Barlow Condensed 400 y
600, y Barlow 400. El Barlow 500 que se pedia no se usaba en ninguna regla.

Uso:  python herramientas/hacer-tipos.py
"""

from pathlib import Path

from fontTools.subset import Subsetter
from fontTools.ttLib import TTFont

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = Path(__file__).resolve().parent / "fuentes"
DESTINO = RAIZ / "tipos"

# archivo de origen -> (nombre de salida, familia, peso)
TIPOS = [
    ("BarlowCondensed-Regular.ttf", "barlow-condensed-400", "Barlow Condensed", 400),
    ("BarlowCondensed-SemiBold.ttf", "barlow-condensed-600", "Barlow Condensed", 600),
    ("Barlow-Regular.ttf", "barlow-400", "Barlow", 400),
    # Solo para las lecturas numericas del portfolio: metricas, tablas de
    # resultados y etiquetas de dato. Una mono separa el dato de la prosa.
    ("IBMPlexMono-Regular.ttf", "plex-mono-400", "IBM Plex Mono", 400),
]

# Latino basico + suplemento + comillas, guiones, · y ×. Cubre el castellano
# entero y los signos que usan las paginas.
UNICODES = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
    "U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
)


def rangos_a_conjunto(spec):
    codigos = set()
    for trozo in spec.split(","):
        trozo = trozo.strip().removeprefix("U+")
        if "-" in trozo:
            a, b = trozo.split("-")
            codigos.update(range(int(a, 16), int(b, 16) + 1))
        else:
            codigos.add(int(trozo, 16))
    return codigos


def main():
    if not ORIGEN.exists():
        print(f"Faltan los .ttf en {ORIGEN}")
        return 1

    DESTINO.mkdir(exist_ok=True)
    codigos = rangos_a_conjunto(UNICODES)

    total_antes = total_despues = 0
    for archivo, salida, familia, peso in TIPOS:
        ttf = ORIGEN / archivo
        if not ttf.exists():
            print(f"Falta {ttf}")
            return 1

        fuente = TTFont(ttf)
        recortador = Subsetter()
        recortador.populate(unicodes=codigos)
        recortador.subset(fuente)

        fuente.flavor = "woff2"
        destino = DESTINO / f"{salida}.woff2"
        fuente.save(destino)
        fuente.close()

        antes = ttf.stat().st_size
        despues = destino.stat().st_size
        total_antes += antes
        total_despues += despues
        print(f"  + {destino.name:<26} {familia} {peso:<4} "
              f"{antes // 1024} KB -> {despues // 1024} KB")

    print(f"\nTotal {total_antes // 1024} KB -> {total_despues // 1024} KB "
          f"({100 - total_despues * 100 // total_antes}% menos)")
    print("Las reglas @font-face ya estan escritas en index.html y tech.html.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
