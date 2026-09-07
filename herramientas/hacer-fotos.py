# -*- coding: utf-8 -*-
"""
Prepara las fotos de Pedro para el portfolio: recorta, ajusta y guarda.

Las originales están en originales/imagenes/ y de ahí no se publica nada. Aquí
se recortan al encuadre que pide cada hueco y se guardan en medios/fotos/, que
sí sube. Cambiar un recorte es cambiar una línea de RECORTES y volver a
ejecutar; nunca se toca el original.

DOS RECORTES QUE NO SON ESTÉTICOS, SON DE SENTIDO COMÚN. En dos de las fotos
aparece gente que no es Pedro: en la de ICADE hay una segunda persona y en la
de Comillas están sus padres y su hermana. Este portfolio va a circular por
empresas, y publicar la cara de terceros que no lo han decidido no es cosa
nuestra. Los dos encuadres los dejan fuera y además funcionan mejor: uno se
queda con Pedro y el otro con el rótulo del edificio, que es lo que dice
"Comillas" de un vistazo. Si Pedro los quiere dentro, se cambia el recorte.

Uso:  python herramientas/hacer-fotos.py
"""

from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "originales" / "imagenes"
DESTINO = RAIZ / "medios" / "fotos"

# Cada entrada: archivo original -> (salida, recorte, medida final)
#
# El recorte va en fracciones del original (izquierda, arriba, derecha, abajo),
# así el mismo número sirve aunque cambie la resolución de la foto.
#
# Las placas de formación son un 34% del ancho de su fila: a lo sumo unos
# 400x300. Se guardan a 900x600 para que se vean nítidas en pantallas densas.
PLACA = (900, 600)

# Las fichas de proyecto van en 16:9. 1000x563 da de sobra para el tamano al
# que se ven (unos 400 de ancho) hasta en pantallas densas.
FICHA = (1000, 563)

RECORTES = {
    # LAS TRES PORTADAS DE FICHA que eligio Pedro. Van a medios/fotos/ y no a
    # medios/portadas/oscuras/, que es lo que genera hacer-portadas.py desde
    # los notebooks: dos scripts escribiendo el mismo archivo es como uno de
    # los dos pierde su trabajo sin que nadie se entere.
    "Predicción de ventas de videojuegos.jpg": (
        "Predicción de ventas de videojuegos.jpg", (0.0, 0.0, 1.0, 1.0), FICHA,
        "llenar", "Cuadrada de origen; el monton de consolas aguanta el recorte "
        "a 16:9 porque llena el encuadre entero."),
    "Ganar a la casa de apuestas.jpg": (
        "Ganar a la casa de apuestas.jpg", (0.0, 0.0, 1.0, 1.0), FICHA,
        "llenar", "3:2 de origen, casi apaisada ya: el rotulo queda centrado."),
    "Lipton · The Summer Shake Up.jpg": (
        "Lipton · The Summer Shake Up.jpg", (0.0, 0.0, 1.0, 1.0), FICHA,
        "rellenar", "VERTICAL (0,56). Recortada a 16:9 se le va media lata, "
        "asi que va entera sobre una copia suya desenfocada."),

    # Las fotos de formacion y la portada del TFM las deja Pedro directamente
    # en medios/fotos/ con el nombre de su seccion, y se usan tal cual.
    #
    # Esta NO se recorta: solo se reduce. Pedro la eligio entera y asi va. Lo
    # unico que hace falta es que no pese 2,5 MB, que es lo que ocupa el PNG
    # que llego del movil: en un movil con datos, esa sola foto es mas que
    # todo el resto de la pagina junta. El recorte (0,0,1,1) es la imagen
    # completa, y el modo "reducir" mantiene la proporcion sin tocar el
    # encuadre. El hueco de la seccion se ajusta a la foto, no al reves.
    "03 · Experiencia.png": (
        "experiencia.jpg", (0.0, 0.0, 1.0, 1.0), (1200, 900), "reducir",
        "La foto entera, tal cual, solo mas ligera. 4:3, que es la proporcion "
        "del hueco de Experiencia, asi que no se pierde ni un pixel."),

    # Igual que la de arriba: mismo encuadre, la mitad de peso. Llegaba a 488
    # KB y la placa la enseña como mucho a 405 puntos de ancho, asi que 1200
    # cubre de sobra hasta una pantalla de triple densidad. El nombre de
    # salida lleva tilde porque es el que apunta contenido-plantilla.json.
    "Master Universitario en Business Analytics.jpeg": (
        "Máster Universitario en Business Analytics.jpeg",
        (0.0, 0.0, 1.0, 1.0), (1200, 900), "reducir",
        "La misma foto de la graduacion, sin recortar, de 488 KB a la mitad."),
}


def preparar(nombre, salida, caja, medida, modo, porque):
    origen = ORIGEN / nombre
    if not origen.exists():
        print(f"  falta {nombre}")
        return False

    img = Image.open(origen).convert("RGB")
    a, h = img.width, img.height
    recorte = img.crop((int(caja[0] * a), int(caja[1] * h),
                        int(caja[2] * a), int(caja[3] * h)))

    if modo == "rellenar":
        # Para fuentes VERTICALES que van en un hueco apaisado. La de Lipton es
        # 375x666: con object-fit:cover en una ficha 16:9 se le corta la lata
        # por arriba y por abajo. En vez de darle a esa ficha un CSS distinto
        # —que romperia que las cuatro sean iguales—, el problema se arregla
        # AQUI: la imagen entera, centrada sobre una copia de si misma ampliada
        # y desenfocada. Es el mismo recurso que usa hacer-video.py con el
        # video vertical de Lipton, y por el mismo motivo.
        from PIL import ImageFilter
        escala = max(medida[0] / recorte.width, medida[1] / recorte.height)
        fondo = recorte.resize((max(1, round(recorte.width * escala)),
                                max(1, round(recorte.height * escala))), Image.LANCZOS)
        izq = (fondo.width - medida[0]) // 2
        arr = (fondo.height - medida[1]) // 2
        final = fondo.crop((izq, arr, izq + medida[0], arr + medida[1]))
        final = final.filter(ImageFilter.GaussianBlur(18))
        e2 = min(medida[0] / recorte.width, medida[1] / recorte.height)
        delante = recorte.resize((max(1, round(recorte.width * e2)),
                                  max(1, round(recorte.height * e2))), Image.LANCZOS)
        final.paste(delante, ((medida[0] - delante.width) // 2,
                              (medida[1] - delante.height) // 2))
    elif modo == "reducir":
        # Ni recorta ni rellena: la misma imagen, mas pequeña. Para las fotos
        # que Pedro quiere enteras y que solo estorban por lo que pesan.
        escala = min(medida[0] / recorte.width, medida[1] / recorte.height, 1.0)
        final = recorte.resize((max(1, round(recorte.width * escala)),
                                max(1, round(recorte.height * escala))), Image.LANCZOS)
    elif modo == "llenar":
        # Se escala hasta cubrir la medida y se recorta el sobrante por el
        # centro: lo mismo que object-fit:cover, pero hecho aquí el archivo
        # pesa lo que tiene que pesar.
        escala = max(medida[0] / recorte.width, medida[1] / recorte.height)
        nueva = recorte.resize((max(1, round(recorte.width * escala)),
                                max(1, round(recorte.height * escala))), Image.LANCZOS)
        izq = (nueva.width - medida[0]) // 2
        arr = (nueva.height - medida[1]) // 2
        final = nueva.crop((izq, arr, izq + medida[0], arr + medida[1]))
    else:
        # Encajar sin recortar, sobre el color del panel. Para las piezas que
        # SON un rótulo: recortarlas por los lados les come las letras, y un
        # letrero a medias se lee como un fallo y no como un encuadre.
        escala = min(medida[0] / recorte.width, medida[1] / recorte.height)
        nueva = recorte.resize((max(1, round(recorte.width * escala)),
                                max(1, round(recorte.height * escala))), Image.LANCZOS)
        final = Image.new("RGB", medida, (19, 21, 25))
        final.paste(nueva, ((medida[0] - nueva.width) // 2,
                            (medida[1] - nueva.height) // 2))

    final.save(DESTINO / salida, "JPEG", quality=84, optimize=True, progressive=True)
    peso = (DESTINO / salida).stat().st_size / 1024
    print(f"  + {salida:<26} {final.size[0]}x{final.size[1]}  ({peso:.0f} KB)")
    print(f"      {porque}")
    return True


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("Fotos del portfolio:")
    hechas = 0
    for nombre, ajuste in RECORTES.items():
        if preparar(nombre, *ajuste):
            hechas += 1

    # Todo lo que hay en la carpeta, no solo los .jpg: aqui conviven .jpeg,
    # .png y .webp, y un total que se deja fuera la mitad no informa de nada.
    archivos = sorted(f for f in DESTINO.iterdir() if f.is_file())
    total = sum(f.stat().st_size for f in archivos)
    print(f"\n{hechas} de {len(RECORTES)} · {len(archivos)} archivos, {total / 1024:.0f} KB")
    print("Para cambiar un encuadre: RECORTES, aquí arriba, y vuelve a ejecutar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
