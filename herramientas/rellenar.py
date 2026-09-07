# -*- coding: utf-8 -*-
"""
Rellena los marcadores de la web sin tocarlos a mano.

Hay muchos sitios donde poner lo mismo. Hacerlo a mano es pedir una errata, y
una errata en el dominio significa que la tarjeta al reenviar el enlace no
carga y no te enteras.

Uso (queda uno; los de Loom se fueron con el concepto de candidatura):

    python herramientas/rellenar.py --video abc123def456
    python herramientas/rellenar.py --dominio pedroperezblanco.com
    python herramientas/rellenar.py --alternativo https://drive.google.com/...

Se puede repetir las veces que haga falta. Lo que ya se puso queda anotado en
herramientas/valores.json, asi que si cambias el dominio, sustituye el anterior
en lugar de buscar un marcador que ya no esta.
"""

import argparse
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# El JavaScript va en ui/pagina.js, asi que el id del video esta ahi y no en el
# HTML. Si no se toca, se publica con VIDEO_ID puesto.
#
# contenido.json entra en la lista aunque no sea una pagina: es de donde
# hacer-web.py saca el texto de version-clara.html. Si solo se arreglara el
# HTML, la siguiente vez que se regenerara volverian a salir los marcadores.
# Solo queda un marcador que rellenar —el dominio— y vive en las cinco paginas
# del portfolio. El id del video de Loom y su enlace de respaldo se fueron con
# el concepto de candidatura: no hay nada que rellenar de eso.
PAGINAS = (["index.html", "404.html"]
           + sorted(str(p.relative_to(RAIZ)).replace("\\", "/")
                    for p in (RAIZ / "trabajos").glob("*.html")))
REGISTRO = Path(__file__).resolve().parent / "valores.json"

# clave interna -> (marcador original, como se describe)
CAMPOS = {
    "video": ("VIDEO_ID", "el id del video de Loom"),
    "alternativo": ("ENLACE_ALTERNATIVO", "la copia del video en otro sitio"),
    "dominio": ("TU-DOMINIO", "el dominio, sin https:// ni barra final"),
}


def limpiar_dominio(valor):
    valor = re.sub(r"^https?://", "", valor.strip())
    return valor.rstrip("/")


def limpiar_video(valor):
    """Acepta la URL entera de Loom o solo el id."""
    valor = valor.strip()
    m = re.search(r"loom\.com/(?:share|embed)/([0-9a-zA-Z]+)", valor)
    if m:
        return m.group(1)
    return valor


def main():
    p = argparse.ArgumentParser(description="Rellena los marcadores de las paginas.")
    p.add_argument("--video", help="Id del video de Loom, o la URL entera.")
    p.add_argument("--alternativo", help="Enlace a la copia del video.")
    p.add_argument("--dominio", help="Dominio real, p.ej. pedroperezblanco.com")
    args = p.parse_args()

    nuevos = {}
    if args.video:
        nuevos["video"] = limpiar_video(args.video)
    if args.alternativo:
        nuevos["alternativo"] = args.alternativo.strip()
    if args.dominio:
        nuevos["dominio"] = limpiar_dominio(args.dominio)

    if not nuevos:
        print("No has pasado ningun valor. Mira --help.")
        return 1

    if args.alternativo and not args.alternativo.strip().startswith("https://"):
        print("AVISO: el enlace alternativo no empieza por https://. "
              "Algunos clientes de correo marcan los enlaces sin cifrar.\n")

    puestos = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else {}

    for pagina in PAGINAS:
        ruta = RAIZ / pagina
        if not ruta.exists():
            print(f"  (salto {pagina}, no existe)")
            continue
        texto = ruta.read_text(encoding="utf-8")
        original = texto

        for campo, valor in nuevos.items():
            marcador, _ = CAMPOS[campo]
            # Si ya se habia puesto algo antes, lo que hay que buscar es
            # aquel valor y no el marcador, que ya no existe en el archivo.
            buscar = puestos.get(campo, marcador)
            cuantos = texto.count(buscar)
            if cuantos == 0:
                print(f"  {pagina}: no encuentro '{buscar}' para {campo}. Lo salto.")
                continue
            texto = texto.replace(buscar, valor)
            print(f"  {pagina}: {campo} -> {valor}   ({cuantos} sitios)")

        if texto != original:
            ruta.write_text(texto, encoding="utf-8")

    puestos.update(nuevos)
    REGISTRO.write_text(json.dumps(puestos, indent=2, ensure_ascii=False), encoding="utf-8")

    faltan = [m for c, (m, _) in CAMPOS.items() if c not in puestos]
    print()
    if faltan:
        print("Todavia sin poner: " + ", ".join(faltan))
    else:
        print("Los tres marcadores estan puestos.")
    print("\nAhora: python herramientas/revisar.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
