# -*- coding: utf-8 -*-
"""
Prepara los vídeos de portada de las páginas de trabajo.

Los que trae Pedro vienen del móvil o de un banco de imágenes: 4K, 50
fotogramas por segundo, decenas de megabytes. Eso no se sirve en una página
que se abre desde el móvil de un reclutador. Aquí se convierten en bucles de
alrededor de un mega.

QUÉ HACE, Y POR QUÉ CADA COSA

  · Recorta un trozo corto. Es un fondo, no un cortometraje, y cada segundo
    son kilobytes.
  · Escala a 1440 de ancho y 24 fotogramas por segundo. Detrás de un panel de
    cristal y un velo, más resolución no se ve; más fotogramas, tampoco.
  · LO PEGA CON SU PROPIO REVERSO. Es lo que hace que el bucle no dé un salto:
    el último fotograma es igual al primero por construcción. Un corte seco en
    un fondo se nota muchísimo, y un fundido encadenado es más frágil.
  · Quita el audio (-an). Un fondo con sonido no se reproduce solo en ningún
    navegador, y aquí no hace ninguna falta.
  · +faststart mueve el índice al principio, así el vídeo empieza a verse
    mientras se descarga en vez de al terminar.
  · Y saca un póster. Es lo que se ve con el movimiento parado y mientras el
    vídeo no ha llegado: unos 100 KB en vez de un mega.

DOS MODOS, Y EL SEGUNDO EXISTE POR UN MOTIVO CONCRETO

  "recortar"  El de siempre. La fuente es apaisada y se recorta a 16:9.
  "rellenar"  Para fuentes VERTICALES. El de Lipton es 720x900, y en una
              portada ancha con object-fit:cover se vería una franja estrecha
              del centro con el rótulo cortado. En lugar de darle a esa página
              un CSS distinto —que rompería la regla de tener un solo sistema
              para las cuatro—, el problema se arregla AQUÍ: se pone el vídeo
              centrado sobre una copia de sí mismo ampliada y desenfocada, y
              lo que se sirve ya es apaisado como los demás. La página no se
              entera de que la fuente era vertical.

SE PROBÓ TAMBIÉN VP9/WebM y salió MÁS GRANDE que el H.264 (1,8 MB contra 1,0),
así que no se sirve: un segundo archivo que pesa más no es una optimización.

Hace falta ffmpeg en el PATH. Si no está:  winget install Gyan.FFmpeg

Uso:  python herramientas/hacer-video.py
"""

import shutil
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "medios" / "video"

# original -> (salida, desde, duracion, modo)
# Las fuentes viven en originales/video/, no en la raiz: son 81 MB de material
# de partida y no tienen nada que hacer al lado de index.html. De ahi no se
# publica nada, y lo que sirve la web esta en medios/video/.
VIDEOS = {
    "originales/video/videojuegos.mp4": ("videojuegos", 1, 8, "recortar"),
    "originales/video/apuestas.mp4": ("apuestas", 0.5, 6, "recortar"),
    # Vertical, 720x900. Ver el comentario de arriba.
    "originales/video/lipton.mp4": ("lipton", 0, 4, "rellenar"),
    # Estos dos llegaron ya apaisados y PEQUEÑOS (748x418 y 684x378). Se
    # sirven casi a su medida en vez de subirlos a 1440: el navegador escala
    # igual, el vídeo va detrás de un panel con brightness .34, y encodear el
    # doble de píxeles solo multiplica los kilobytes. De ahí el quinto
    # elemento, que es el ancho de salida.
    "originales/video/deep-learning.mp4": ("deep-learning", 0, 5.2, "recortar", 960),
    "originales/video/letterboxd.mp4": ("letterboxd", 0, 6.0, "recortar", 960),
    # Self-play RL. La fuente es un vertical 720x1280 con el gameplay
    # incrustado en 720x960 a partir de y=160 (medido con cropdetect, no a
    # ojo). De esa ventana se saca la franja 16:9 y se sirve a 960 como los
    # dos de arriba: subir 720 px de origen a 1440 solo multiplica los
    # kilobytes. El trozo elegido, de 1,5 s a 6,5 s, es arena tranquila: deja
    # fuera la explosion de gol del final, que detras de un titular es ruido.
    # CONTEXTO VISUAL, no material del experimento.
    "originales/video/rlgym-contexto.mp4": ("rlgym", 1.5, 5.0, "recortar", 960,
                                            "crop=720:405:0:400"),
    # Los DOS CORTES interiores del mismo caso, del mismo clip y de la misma
    # ventana 16:9, pero de tramos distintos: 7,0-10,5 s y 10,5-13,5 s. Se
    # deja fuera todo lo posterior a 13,5 s, que es la explosion de gol: en
    # una banda estrecha detras de un rotulo es una mancha naranja y no se
    # entiende que es. Van a 720 px y no a 960 porque son cintas decorativas
    # que ademas se descargan en diferido: la mitad de pixeles, la mitad de
    # kilobytes, y detras de un velo al 34% no se nota.
    "originales/video/rlgym-contexto.mp4|corte1": ("rlgym-corte1", 7.0, 3.5, "recortar",
                                                   720, "crop=720:405:0:400"),
    "originales/video/rlgym-contexto.mp4|corte2": ("rlgym-corte2", 10.5, 3.0, "recortar",
                                                   720, "crop=720:405:0:400"),
}

ANCHO, ALTO = 1440, 810
FPS = 24
CALIDAD = 31        # CRF de x264. Mas alto, mas pequeño y menos fino.
DESENFOQUE = 28     # sigma del fondo en modo "rellenar"


def ffmpeg():
    for nombre in ("ffmpeg", "ffmpeg.exe"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    print("No encuentro ffmpeg. Instálalo con:  winget install Gyan.FFmpeg")
    return None


def filtro(desde, dura, modo, ancho=None, alto=None, recorte=None):
    """El grafo de filtros. Los dos modos acaban en el mismo bucle.

    `recorte` es un "crop=W:H:X:Y" que se aplica ANTES que nada. Existe para
    las fuentes que traen la imagen incrustada dentro de otro lienzo: un
    gameplay 3:4 metido en un vertical 9:16, por ejemplo, donde recortar
    despues de escalar deformaria o dejaria las bandas negras dentro.
    Sin este argumento el filtro es exactamente el de siempre.
    """
    ancho = ancho or ANCHO
    alto = alto or ALTO
    corte = f"trim={desde}:{desde + dura},setpts=PTS-STARTPTS"
    if recorte:
        corte += f",{recorte}"

    if modo == "rellenar":
        base = (
            f"[0:v]{corte},split[a][b];"
            # El fondo: la misma imagen ampliada hasta cubrir y desenfocada.
            f"[a]scale={ancho}:{alto}:force_original_aspect_ratio=increase,"
            f"crop={ancho}:{alto},gblur=sigma={DESENFOQUE}[bg];"
            # Y delante, el vídeo entero, sin recortar ni una letra.
            f"[b]scale=-2:{alto}[fg];"
            f"[bg][fg]overlay=(W-w)/2:0,fps={FPS}"
        )
    else:
        base = f"[0:v]{corte},scale={ancho}:-2,fps={FPS}"

    # Ida y vuelta: el bucle cierra solo.
    return base + ",split[f][r];[r]reverse[rv];[f][rv]concat=n=2:v=1:a=0[v]"


def preparar(exe, origen, salida, desde, dura, modo, ancho=None, recorte=None):
    # La clave del diccionario puede llevar un sufijo «|loquesea» para poder
    # sacar DOS trozos distintos del mismo archivo sin duplicarlo en disco.
    origen = origen.split("|")[0]
    o = RAIZ / origen
    if not o.exists():
        print(f"  falta {origen}")
        return False

    mp4 = DESTINO / f"{salida}.mp4"
    poster = DESTINO / f"{salida}-poster.jpg"

    subprocess.run([exe, "-v", "error", "-y", "-i", str(o),
                    "-filter_complex", filtro(desde, dura, modo, ancho, recorte=recorte),
                    "-map", "[v]", "-an",
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(CALIDAD),
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(mp4)], check=True)

    # El póster sale del vídeo YA PREPARADO, no del original: si saliera del
    # original, en modo "rellenar" la imagen fija tendría otro encuadre que el
    # vídeo y se vería el salto justo al arrancar.
    subprocess.run([exe, "-v", "error", "-y", "-ss", str(min(2, dura / 2)),
                    "-i", str(mp4), "-frames:v", "1", "-q:v", "6",
                    str(poster)], check=True)

    print(f"  + {mp4.name:<18} {mp4.stat().st_size / 1024:>5.0f} KB   "
          f"bucle de {dura * 2:.0f}s · {modo} · {ancho or ANCHO}px")
    print(f"    {poster.name:<18} {poster.stat().st_size / 1024:>5.0f} KB")
    return True


def main():
    exe = ffmpeg()
    if not exe:
        return 1
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("Vídeos de portada:")
    hechos = sum(1 for k, v in VIDEOS.items() if preparar(exe, k, *v))
    total = sum(f.stat().st_size for f in DESTINO.iterdir() if f.is_file())
    print(f"\n{hechos} de {len(VIDEOS)} · {total / 1024:.0f} KB en total")
    print("Para cambiar el trozo, el modo o la calidad: VIDEOS y CALIDAD, aquí arriba.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
