# -*- coding: utf-8 -*-
"""
Prepara los documentos que se enseñan dentro de una página de trabajo.

Hace dos cosas, y las dos existen para que la página no pueda mentir:

  1. RASTERIZA LA PRIMERA PÁGINA del PDF a una imagen. Es la portada que se
     ve en el visor antes de cargar el documento de verdad. Sin ella, el
     hueco sería un rectángulo gris, y con 8,5 MB de PDF eso significa o
     descargarlo siempre o enseñar un vacío.

  2. MIDE el archivo —páginas y peso— y escribe esas dos cifras en el JSON
     del caso. No se escriben a mano. Un «8,5 MB» tecleado al lado de un
     botón de descarga se queda viejo la primera vez que alguien cambie el
     PDF, y nadie se entera hasta que un reclutador se descarga otra cosa.
     Hay además una prueba que compara lo que dice la página con el archivo
     real, por si alguien edita el JSON sin volver a pasar por aquí.

DEPENDENCIAS: pypdf y pypdfium2, las dos SOLO de construcción. La web sigue
sin llevar ni una: lo que se sirve es un JPEG y un PDF. Si no están, el
script lo dice y no rompe nada.

    pip install pypdf pypdfium2

Uso:  python herramientas/hacer-informe.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "medios" / "informes"

# json del caso -> (pdf, nombre de la portada)
INFORMES = {
    "contenido-tfm.json": ("trabajos/tfm-presentacion.pdf", "tfm"),
    "contenido-rlgym.json": ("trabajos/rlgym-presentacion.pdf", "rlgym"),
    "contenido-lipton.json": ("trabajos/lipton-summer-shake-up.pdf", "lipton"),
    "contenido-videojuegos.json": ("trabajos/videojuegos-presentacion.pdf", "videojuegos"),
    "contenido-deeplearning.json": ("trabajos/deep-learning-presentacion.pdf", "deep-learning"),
    "contenido-letterboxd.json": ("trabajos/letterboxd-presentacion.pdf", "letterboxd"),
    "contenido-apuestas.json": ("trabajos/apuestas-presentacion.pdf", "apuestas"),
}

ANCHO = 1000        # px de la portada. El visor la enseña a unos 470 de ancho.
CALIDAD = 82


def peso_legible(n):
    """8915611 -> '8,5 MB'. Con coma, que es como se escribe en español."""
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB".replace(".", ",")
    return f"{n / 1024:.0f} KB"


def preparar(nombre_json, ruta_pdf, salida):
    pdf = RAIZ / ruta_pdf
    if not pdf.exists():
        print(f"  falta {ruta_pdf}")
        return False

    from pypdf import PdfReader
    import pypdfium2 as pdfium

    paginas = len(PdfReader(str(pdf)).pages)
    octetos = pdf.stat().st_size

    doc = pdfium.PdfDocument(str(pdf))
    pagina = doc[0]
    escala = ANCHO / pagina.get_width()
    imagen = pagina.render(scale=escala).to_pil().convert("RGB")
    destino = DESTINO / f"{salida}-portada.jpg"
    imagen.save(destino, "JPEG", quality=CALIDAD, optimize=True, progressive=True)
    doc.close()

    # Y las cifras al JSON, para que la página las lea de un solo sitio.
    j = RAIZ / nombre_json
    d = json.loads(j.read_text(encoding="utf-8"))
    informe = d.setdefault("cierre", {}).setdefault("informe", {})
    # La ruta se calcula DESDE trabajos/, que es donde vive la página que la
    # va a usar. El PDF también está ahí, así que sale un nombre a secas; si
    # algún día se mueve a medios/, sale "../medios/...". Escribirla a mano es
    # como se rompen los enlaces al reorganizar carpetas.
    informe["archivo"] = str(
        Path(ruta_pdf).relative_to("trabajos")
        if ruta_pdf.startswith("trabajos/") else Path("..") / ruta_pdf).replace("\\", "/")
    informe["portada"] = f"../medios/informes/{salida}-portada.jpg"
    # Las medidas reales de la portada. Van al HTML como width/height para que
    # el navegador reserve el hueco con la proporcion correcta: una memoria en
    # A4 y una presentacion apaisada no tienen la misma forma, y escribir una
    # sola medida a mano hace saltar la pagina al cargar la imagen.
    informe["ancho"] = imagen.width
    informe["alto"] = imagen.height
    informe["paginas"] = paginas
    informe["peso"] = peso_legible(octetos)
    informe["octetos"] = octetos
    informe.setdefault("titulo", "Informe")
    informe.setdefault("descarga", "lipton-summer-shake-up.pdf")
    j.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"  + {destino.name:<24} {imagen.width}x{imagen.height}  "
          f"{destino.stat().st_size / 1024:>4.0f} KB")
    print(f"    {pdf.name}: {paginas} páginas, {peso_legible(octetos)}"
          f"   -> anotado en {nombre_json}")
    return True


def main():
    try:
        import pypdf                      # noqa: F401
        import pypdfium2                  # noqa: F401
    except ImportError:
        print("Faltan las librerías de construcción. Instálalas con:")
        print("    pip install pypdf pypdfium2")
        print("La web no las necesita: solo hacen falta para regenerar la portada.")
        return 1

    DESTINO.mkdir(parents=True, exist_ok=True)
    print("Documentos de los trabajos:")
    hechos = sum(1 for k, v in INFORMES.items() if preparar(k, *v))
    print(f"\n{hechos} de {len(INFORMES)}")
    print("Las páginas y el peso NO se escriben a mano: salen de aquí, del "
          "archivo de verdad.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
