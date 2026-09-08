# -*- coding: utf-8 -*-
"""
Genera las páginas de caso de trabajos/ a partir de sus JSON.

    contenido-tfm.json          ->  trabajos/tfm-lead-scoring.html
    contenido-videojuegos.json  ->  trabajos/videojuegos.html

Un caso no es un cuaderno: portada con los datos de la ficha, un raíl de
apartados pegajoso y varios capítulos, cada uno con su gráfico. La
arquitectura viene de las páginas de caso de la web que sirvió de referencia;
la piel, el fondo, la barra y el interruptor de movimiento son los mismos que
los del portfolio, para que se lea como la misma web y no como un anexo.

UN SOLO GENERADOR PARA LAS DOS. La segunda página se parecía tanto a la
primera que copiarla habría dejado dos archivos casi iguales, y el día que
haya que arreglar algo en el raíl o en la portada, uno de los dos se queda
sin arreglar. Lo que cambia entre ellas está en el JSON, no aquí.

LOS GRÁFICOS SON SVG DIBUJADOS AQUÍ, a mano. La referencia usa ApexCharts;
este proyecto no mete dependencias, y además un gráfico de cuatro números no
necesita 400 KB de librería. Al ser SVG en el propio HTML se ven aunque el
JavaScript esté bloqueado, se imprimen bien y heredan los colores del tema.

Y SUS NÚMEROS SALEN DEL JSON, no están escritos aquí. En la primera versión
cada gráfico llevaba sus cifras dentro del Python, y las mismas cifras
estaban otra vez en la tabla de datos de su apartado: dos sitios que hay que
cambiar a la vez, y el día que solo se cambie uno la página dice una cosa y
el dibujo otra, sin que salte nada.

REGLA DE CONFIDENCIALIDAD, la de CLAUDE.md:
    SÍ  métricas del modelo, el 30/96, el lift de la categoría A,
        la validación temporal.
    NO  la tasa de conversión global de Comillas, qué canales funcionan
        mejor, los umbrales concretos, ningún registro del CRM.

Y una consecuencia que no es obvia: la conversión de la categoría A (su
porcentaje absoluto) NO entra, aunque el lift sí. Publicar los dos deja
despejar la tasa global con una división. Por lo mismo, el gráfico de PR-AUC
no lleva línea de base: la base del PR-AUC ES la prevalencia de la clase
positiva, o sea la tasa de conversión.

Uso:  python herramientas/hacer-caso.py
"""

import html as _html
import json
import re
from pathlib import Path
from urllib.parse import quote

RAIZ = Path(__file__).resolve().parent.parent

CASOS = [
    ("contenido-tfm.json", "tfm-lead-scoring.html"),
    ("contenido-rlgym.json", "rlgym-selfplay-pool.html"),
    ("contenido-videojuegos.json", "videojuegos.html"),
    ("contenido-deeplearning.json", "deep-learning.html"),
    ("contenido-letterboxd.json", "letterboxd.html"),
    ("contenido-lipton.json", "lipton.html"),
    ("contenido-apuestas.json", "apuestas.html"),
]

# Lo que no puede aparecer en ninguna pagina, pase lo que pase. Si alguien
# mete uno de estos en un JSON, el generador para y no escribe ese archivo.
#
# Todos los patrones buscan VALORES, no palabras. El primer intento vigilaba
# la expresion "umbrales concretos" y salto con la frase del cierre que dice
# que esos umbrales NO se publican: hablar de que algo no se cuenta no es
# contarlo, y una guarda que no distingue las dos cosas acaba desactivada.
#
# LOS VALORES REALES NO ESTAN EN ESTE ARCHIVO, y ese es el punto. Este script
# viaja al repositorio publico; escribir aqui el umbral de A para poder
# vigilarlo era publicarlo en el mismo gesto de protegerlo. Viven en
# herramientas/confidencial.local.json, que .gitignore deja fuera.
#
# Lo que si se queda aqui son los patrones ESTRUCTURALES: no citan ningun
# valor, describen la forma de un umbral escrito al lado de su palabra.
CONFIDENCIAL = RAIZ / "herramientas" / "confidencial.local.json"

PROHIBIDO_ESTRUCTURAL = [
    (r"umbral[^.]{0,40}?[01][,.]\d{3}", "un umbral con su valor"),
    (r"[01][,.]\d{3}[^.]{0,40}?umbral", "un umbral con su valor"),
]


def cargar_prohibido():
    """Los patrones estructurales mas los valores reales del archivo local.

    Se niega a seguir si el archivo local no esta. Es deliberado: sin el, la
    guarda seguiria pasando y no estaria mirando los tres datos que de verdad
    hay que vigilar, que es exactamente la forma en que una comprobacion deja
    de servir sin que nadie se entere.
    """
    if not CONFIDENCIAL.exists():
        raise SystemExit(
            "\n  ! FALTA herramientas/confidencial.local.json\n"
            "    Sin ese archivo la guarda de confidencialidad no vigila los\n"
            "    valores reales, y este script no genera nada. No se publica:\n"
            "    esta en .gitignore. Recuperalo de tu copia local.\n")
    try:
        datos = json.loads(CONFIDENCIAL.read_text(encoding="utf-8"))
        lista = [(x["patron"], x["que"]) for x in datos["prohibido"]]
    except (ValueError, KeyError, TypeError) as err:
        raise SystemExit(f"\n  ! {CONFIDENCIAL.name} no se puede leer: {err}\n")
    if not lista:
        raise SystemExit(f"\n  ! {CONFIDENCIAL.name} no trae ningun patron.\n")
    return PROHIBIDO_ESTRUCTURAL + lista


PROHIBIDO = cargar_prohibido()

FLECHA = '<span class="flecha" aria-hidden="true">↗</span>'



def recortar(texto, limite=155):
    """Recorta a `limite` caracteres sin partir una palabra por la mitad.

    Antes esto era texto[:155] a secas, y las descripciones de la home, el
    TFM, Videojuegos y Apuestas salian cortadas a media palabra -"producci",
    "conve", "loga", "din"-. Eso es justo lo que ensena Google en el
    resultado y LinkedIn en la tarjeta al compartir.

    Lo correcto es que la descripcion quepa entera. Si esta funcion tiene que
    recortar algo, el arreglo no esta aqui sino en el JSON: por eso avisa por
    consola en vez de recortar en silencio.
    """
    texto = " ".join(str(texto).split())
    if len(texto) <= limite:
        return texto
    corte = texto[:limite - 1]
    if " " in corte:
        corte = corte[:corte.rindex(" ")]
    print(f"    ! descripcion de {len(texto)} caracteres recortada: "
          f"reescribela en su JSON para que quepa en {limite}.")
    return corte.rstrip(" ,;:.") + "…"

def e(t):
    return _html.escape(str(t), quote=True)


def ruta(p):
    """Codifica una ruta de archivo para meterla en un src.

    La misma que usa hacer-plantilla.py. Hoy ninguna de estas rutas lleva
    espacios, pero Pedro nombra sus archivos como los nombra —"Video
    videojuegos.mp4"— y el dia que uno entre sin codificar, el navegador
    corta la URL en el primer espacio y no carga.
    """
    return e(quote(str(p), safe="/."))


def titular(d, clase):
    """Titular con una palabra en ámbar y cursiva, como en el portfolio."""
    partes = [e(d.get("titulo_antes", ""))]
    if d.get("titulo_acento"):
        partes.append(f'<em class="acento">{e(d["titulo_acento"])}</em>')
    if d.get("titulo_despues"):
        partes.append(e(d["titulo_despues"]))
    # El punto final va pegado a la palabra anterior, no separado por un
    # espacio: " ." es un fallo de composición que se ve desde lejos.
    texto = " ".join(p for p in partes if p)
    return f'<h2 class="{clase}">' + re.sub(r"\s+([.,;:])", r"\1", texto) + "</h2>"


# --------------------------------------------------------------- gráficos
#
# Todos van en una caja con viewBox de 640 de ancho, así escalan solos y no
# hace falta ni una media query ni un listener de resize. Las medidas están
# en unidades del viewBox, no en píxeles.
#
# Cada función recibe la lista "datos" de su apartado. Ninguna sabe de qué
# proyecto habla.

# --g más grande de ui/trabajo.css, el del tramo de móvil. El generador dibuja
# para el caso PEOR: un solo SVG sirve a todos los anchos de ventana, así que
# las medidas se calculan con la letra más grande que va a pintarse. Subirlo
# encoge el texto que cabe en TODAS las pantallas, no solo en el móvil.
# Si alguien toca la escalera de --g, esta cuenta se queda vieja; por eso hay
# doce pruebas que miden los textos contra su viewBox en diecinueve anchos.
G_MAX = 2.0

# Lo que ocupa una letra, en unidades del viewBox, con esa letra máxima.
# Se puede calcular porque IBM Plex Mono es MONOESPACIADA: cada carácter
# avanza 0,6 em más el letter-spacing. Comprobado con getBBox(): «registros de
# partida», 20 letras de .g-pie a 12px con 0,08 em, mide 163,1 unidades, y
# 20 x 12 x 0,68 = 163,2. Coincide hasta la décima en las cuatro páginas.
LETRA_PIE = 12 * G_MAX * (0.6 + 0.08)
LETRA_ROT = 13 * G_MAX * (0.6 + 0.12)

# Y lo que ocupa de alto una línea, para poder apilar dos sin que se toquen.
# getBBox() devuelve la caja de la letra ENTERA, subida y bajada incluidas, y
# en IBM Plex Mono eso son 1,32 em. Los 5 de más son holgura a propósito: con
# el alto justo quedaba 1 unidad libre entre dos líneas, y una holgura de 1 no
# es una holgura, es que todavía no ha fallado.
CAJA_LETRA = 1.32
CIFRA_BASE = 24        # el cuerpo de .g-num, en px
LINEA_PIE = round(12 * G_MAX * CAJA_LETRA) + 5
LINEA_ROT = round(13 * G_MAX * CAJA_LETRA) + 5
# Y el paso para el texto GRANDE. Sale de CIFRA, no de 13: una frase de dos
# lineas en .g-num con el paso de los rotulos se solapa consigo misma, y la
# comprobacion de textos pegados lo caza con -182 unidades de hueco.
LINEA_NUM = round(CIFRA_BASE * G_MAX * CAJA_LETRA) + 6

# Las cifras van en Barlow Condensed 600, que NO es monoespaciada, así que
# aquí no vale contar letras: los dos números salen de medir con getBBox().
# Cada carácter avanza 0,475 em y la caja sube 1,01 em sobre la línea base.
# Sirven para saber si una cifra cabe donde va, que es lo único que hace falta
# saber de ellas: dentro de un arco, dentro de una barra, encima de otra.
# El 0,50 de avance está redondeado HACIA ARRIBA a propósito: medido da 0,475,
# y con ese valor exacto la cuenta decía que dos cifras vecinas se separaban
# 11 unidades cuando el navegador las dejaba a 8. Una estimación que se queda
# corta en una comprobación de si algo cabe no sirve para nada: tiene que
# equivocarse del lado de sobrar.
CIFRA_ANCHO, CIFRA_ALTO = 0.50, 1.01
CIFRA = 24           # .g-num
CIFRA_MEDIDOR = 25   # .g-num--grande, en ui/trabajo.css. Los dos a la vez.

# Márgenes del lienzo. Nada de lo que se dibuja los pisa.
IZQ, DER = 50, 590


def lineas(texto):
    """Un rótulo puede venir partido en varias líneas con «|»."""
    return str(texto).split("|")


def ancho_cifra(texto, base=CIFRA):
    return len(str(texto)) * CIFRA_ANCHO * base * G_MAX


def cabe(texto, sitio, letra=LETRA_PIE, donde=""):
    """Avisa AL GENERAR si un rótulo no va a caber con la letra de móvil.

    Es la diferencia entre enterarse aquí y enterarse mirando la web en un
    teléfono, que es como se enteró Pedro: «se cortan cifras o letras y no se
    entiende lo que pone».
    """
    bien = True
    for linea in lineas(texto):
        ancho = len(linea) * letra
        if ancho > sitio:
            print(f'    ! no cabe{donde}: «{linea}» pide {ancho:.0f} y hay '
                  f'{sitio:.0f}. Pártelo con «|» o acórtalo a '
                  f'{int(sitio / letra)} caracteres.')
            bien = False
    return bien


def _svg(cuerpo, alto=360):
    # aria-hidden y SIN role="img": el dibujo no se anuncia, y quien no lo ve
    # recibe el párrafo .oculto que va debajo, que lo describe con palabras.
    # Poner los dos es contradictorio y algunos lectores leen la mitad.
    return (f'<svg class="grafico" viewBox="0 0 640 {alto}" '
            f'preserveAspectRatio="xMidYMid meet" aria-hidden="true">{cuerpo}</svg>')


def _num(x, clave="valor"):
    """El número como se escribe en español, o el texto que mande el JSON.

    La clave "texto" existe porque hay valores que no se escriben como salen:
    el R2 de una linea de base es «0,000» y no «0», y ese cero con tres
    decimales es justo lo que dice que la comparacion es de verdad y no un
    hueco. Lo mismo con un menos cero de coma flotante, que no se enseña.
    """
    if isinstance(x, dict):
        if x.get("texto"):
            return e(x["texto"])
        x = x[clave]
    if isinstance(x, str):
        return e(x)
    s = f"{float(x):.4f}".rstrip("0").rstrip(".") or "0"
    return s.replace(".", ",")


def g_escalones(datos):
    """Un embudo: cada fila con su ancho relativo. La última, destacada.

    EL RÓTULO VA DEBAJO DE SU BARRA, no a la derecha. Estuvo a la derecha, y
    ahí los dos se pelean por el mismo ancho: con el embudo lleno el texto
    empezaba en 606 de un lienzo de 640 y se cortaba a media palabra —«títu»,
    «observacio»—. Encoger la barra hasta que cupiera el texto quitaba el
    corte, pero ataba una cosa a la otra: al agrandar la letra para que se
    leyera en un móvil, la barra se quedaba en un muñón de 140 sobre 640.
    Debajo, cada uno tiene su sitio y ninguno le quita nada al otro.
    """
    ANCHO, FILA, ALTA = DER - IZQ, 122, 64
    # La cifra va dentro de la barra, así que su línea base se centra con la
    # altura de la MAYÚSCULA (0,72 em en Barlow Condensed), no con el alto de
    # la caja: centrar por la caja deja el número visiblemente alto.
    base = round(ALTA / 2 + 0.36 * CIFRA * G_MAX)
    p = []
    for i, x in enumerate(datos):
        y = 30 + i * FILA
        w = ANCHO * float(x["parte"])
        ultimo = i == len(datos) - 1
        p.append(f'<rect x="{IZQ}" y="{y}" width="{w:.0f}" height="{ALTA}" rx="6" '
                 f'fill="{"var(--senal)" if ultimo else "var(--linea-fuerte)"}" '
                 f'opacity="{".9" if ultimo else ".45"}"/>')
        p.append(f'<text x="{IZQ + 16}" y="{y + base}" class="g-num">'
                 f'{e(x["valor"])}</text>')
        p.append(f'<text x="{IZQ}" y="{y + ALTA + 30}" class="g-pie">'
                 f'{e(x["etiqueta"])}</text>')
        cabe(x["etiqueta"], ANCHO, donde=" en un embudo")
        if 16 + ancho_cifra(x["valor"]) > w:
            print(f'    ! la cifra «{x["valor"]}» se sale de su barra del '
                  f'embudo: la barra mide {w:.0f} y la cifra pide '
                  f'{16 + ancho_cifra(x["valor"]):.0f}.')
    return _svg("".join(p), 30 + len(datos) * FILA - 16)


def g_medidores(datos):
    """Arcos de 0 a 1. Sin línea de base: ver la nota de arriba."""
    p = []
    hueco = 640 / max(1, len(datos))
    cy = 205
    # El arco es geometría y NO se escala con --g; la cifra que va dentro sí.
    # Por eso el radio se calcula con sitio de sobra y la cifra se comprueba.
    r = min(108, hueco / 2 - 12)
    for i, x in enumerate(datos):
        cx = hueco * (i + 0.5)
        largo = 3.14159 * r
        v = float(x["valor"])
        p.append(f'<path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}" fill="none" '
                 f'stroke="var(--linea-fuerte)" stroke-width="14" '
                 f'stroke-linecap="round" opacity=".4"/>')
        p.append(f'<path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}" fill="none" '
                 f'stroke="var(--senal)" stroke-width="14" stroke-linecap="round" '
                 f'stroke-dasharray="{largo * v:.1f} {largo:.1f}"/>')
        p.append(f'<text x="{cx:.0f}" y="{cy - 6}" class="g-num g-num--grande" '
                 f'text-anchor="middle">{_num(x)}</text>')
        p.append(f'<text x="{cx:.0f}" y="{cy + 44}" class="g-rotulo" '
                 f'text-anchor="middle">{e(x["etiqueta"])}</text>')
        p.append(f'<text x="{cx:.0f}" y="{cy + 44 + LINEA_ROT}" class="g-pie" '
                 f'text-anchor="middle">{e(x.get("pie", ""))}</text>')

        # ¿Cabe la cifra DENTRO del arco? El trazo mide 14, así que el hueco
        # limpio llega hasta r-7. Se mide a la altura del techo de la cifra,
        # que es donde el arco se ha cerrado más y donde llegó a montarse.
        medio = ancho_cifra(_num(x), CIFRA_MEDIDOR) / 2
        techo = 6 + CIFRA_ALTO * CIFRA_MEDIDOR * G_MAX
        if medio ** 2 + techo ** 2 > (r - 7) ** 2:
            libre = max(0.0, (r - 7) ** 2 - techo ** 2) ** 0.5
            print(f'    ! la cifra «{_num(x)}» se monta en el arco de su '
                  f'medidor: pide {medio:.0f} de medio ancho y el arco da '
                  f'{libre:.0f}.')

        # Centrado: el sitio es el doble de lo que va de aquí al borde.
        sitio = 2 * min(cx, 640 - cx) - 16
        cabe(x["etiqueta"], sitio, LETRA_ROT, " en un medidor")
        cabe(x.get("pie", ""), sitio, donde=" bajo un medidor")
    return _svg("".join(p), cy + 44 + LINEA_ROT + 22)


def g_comparacion(datos):
    """Dos barras de 0 a 100 puestas una encima de otra."""
    ANCHO, FILA, ALTA = DER - IZQ, 170, 62
    p = []
    for i, x in enumerate(datos):
        y = 80 + i * FILA
        pct = float(x["valor"])
        p.append(f'<text x="{IZQ}" y="{y - 20}" class="g-rotulo">{e(x["etiqueta"])}</text>')
        p.append(f'<rect x="{IZQ}" y="{y}" width="{ANCHO}" height="{ALTA}" rx="8" '
                 f'fill="var(--linea-fuerte)" opacity=".32"/>')
        w = ANCHO * pct / 100
        p.append(f'<rect x="{IZQ}" y="{y}" width="{w:.1f}" height="{ALTA}" rx="8" '
                 f'fill="var(--senal)" opacity="{".55" if i == 0 else ".92"}"/>')
        # El número va dentro de la barra si cabe, y fuera si no. «Si cabe» se
        # calcula, no se estima con un número redondo: depende de --g.
        texto = _num(x) + "%"
        dentro = w > ancho_cifra(texto) + 36
        base = round(ALTA / 2 + 0.36 * CIFRA * G_MAX)
        p.append(f'<text x="{IZQ + w - 18 if dentro else IZQ + w + 18:.0f}" y="{y + base}" '
                 f'class="{"g-num g-num--sobre" if dentro else "g-num"}" '
                 f'text-anchor="{"end" if dentro else "start"}">{texto}</text>')
        p.append(f'<text x="{IZQ}" y="{y + ALTA + 34}" class="g-pie">'
                 f'{e(x.get("pie", ""))}</text>')
        cabe(x["etiqueta"], ANCHO, LETRA_ROT, " sobre una barra")
        cabe(x.get("pie", ""), ANCHO, donde=" bajo una barra")
    return _svg("".join(p), 80 + len(datos) * FILA - 24)


def g_barras(datos):
    """Barras verticales comparables. La marcada, en ámbar fuerte."""
    SUELO, HUECO_CIFRA = 250, 14
    # La cifra va ENCIMA de la barra más alta, así que el techo de la barra lo
    # decide la cifra: con --g a 2 y 190 de barra, el número se salía del
    # lienzo por arriba. Se resta lo que ocupa en vez de escribir un tope.
    TOPE = round(SUELO - (HUECO_CIFRA + CIFRA_ALTO * CIFRA * G_MAX) - 10)
    tope = max(float(x["valor"]) for x in datos) * 1.25 or 1
    n = len(datos)
    hueco = (DER - IZQ) / n
    ancho = min(120, hueco * 0.62)
    p = [f'<line x1="{IZQ}" y1="{SUELO}" x2="{DER}" y2="{SUELO}" '
         f'stroke="var(--linea)" stroke-width="1"/>']
    filas = 1
    for i, x in enumerate(datos):
        v = float(x["valor"])
        cx = IZQ + hueco * (i + 0.5)
        # Un valor negativo o cero (una línea de base) se dibuja como una raya
        # al ras: una barra de altura cero no se ve y parece que falta un dato.
        alto = max(3, TOPE * (v / tope)) if v > 0 else 3
        y = SUELO - alto
        fuerte = x.get("destacada")
        p.append(f'<rect x="{cx - ancho / 2:.0f}" y="{y:.0f}" width="{ancho:.0f}" '
                 f'height="{alto:.0f}" rx="5" fill="var(--senal)" '
                 f'opacity="{".92" if fuerte else ".45"}"/>')
        p.append(f'<text x="{cx:.0f}" y="{y - HUECO_CIFRA:.0f}" class="g-num" '
                 f'text-anchor="middle">{_num(x)}</text>')
        trozos = lineas(x["etiqueta"])
        filas = max(filas, len(trozos))
        for j, linea in enumerate(trozos):
            p.append(f'<text x="{cx:.0f}" y="{SUELO + 32 + j * LINEA_ROT}" '
                     f'class="g-rotulo" text-anchor="middle">{e(linea)}</text>')
        cabe(x["etiqueta"], 2 * min(cx - 4, 636 - cx), LETRA_ROT, " bajo una barra")

    # Y ahora lo que de verdad aprieta: el rótulo de al lado. Dos rótulos
    # centrados en columnas contiguas se tocan mucho antes de llegar al borde
    # del lienzo, y pegados se leen como una sola palabra. Se comprueba por
    # PAREJAS, con el hueco mínimo que separa dos palabras a la vista.
    HUECO_MINIMO = 10
    for i in range(len(datos) - 1):
        for clave, letra in ((lambda d: max(lineas(d["etiqueta"]), key=len), LETRA_ROT),
                             (lambda d: _num(d), CIFRA_ANCHO * CIFRA * G_MAX)):
            if letra is LETRA_ROT:
                a = len(clave(datos[i])) * letra / 2
                b = len(clave(datos[i + 1])) * letra / 2
            else:
                a = ancho_cifra(clave(datos[i])) / 2
                b = ancho_cifra(clave(datos[i + 1])) / 2
            if a + b + HUECO_MINIMO > hueco:
                print(f'    ! se pegan dos textos de barras vecinas: '
                      f'«{clave(datos[i])}» y «{clave(datos[i + 1])}» piden '
                      f'{a + b:.0f} y la columna da {hueco - HUECO_MINIMO:.0f}. '
                      f'Acórtalos o pártelos con «|».')
    return _svg("".join(p), SUELO + 32 + filas * LINEA_ROT + 8)


def g_veredictos(datos):
    """Una lista de sí/no. Para hipótesis: lo que se confirma y lo que no."""
    MARCA, RADIO, TEXTO = 74, 20, 116
    filas = max(len(lineas(x["etiqueta"])) for x in datos)
    paso = 30 + LINEA_ROT + LINEA_PIE * filas
    p = []
    for i, x in enumerate(datos):
        y = 26 + i * paso
        si = bool(x.get("si"))
        color = "var(--senal)" if si else "var(--linea-fuerte)"
        p.append(f'<circle cx="{MARCA}" cy="{y + 22}" r="{RADIO}" fill="none" '
                 f'stroke="{color}" stroke-width="1.8" opacity="{"1" if si else ".8"}"/>')
        if si:
            p.append(f'<path d="M {MARCA - 10} {y + 22} l 8 8 l 14 -16" fill="none" '
                     f'stroke="var(--senal)" stroke-width="2.4" stroke-linecap="round"/>')
        else:
            p.append(f'<path d="M {MARCA - 9} {y + 13} l 18 18 m 0 -18 l -18 18" '
                     f'fill="none" stroke="var(--linea-fuerte)" stroke-width="2.4" '
                     f'stroke-linecap="round"/>')
        p.append(f'<text x="{TEXTO}" y="{y + 20}" class="g-rotulo">'
                 f'{e("Se confirma" if si else "Se cae")}</text>')
        for j, linea in enumerate(lineas(x["etiqueta"])):
            p.append(f'<text x="{TEXTO}" y="{y + 20 + LINEA_ROT + j * LINEA_PIE}" '
                     f'class="g-pie">{e(linea)}</text>')
        cabe(x["etiqueta"], DER - TEXTO, donde=" en un veredicto")
    return _svg("".join(p), 26 + len(datos) * paso)


def g_resto(datos):
    """Cuánto explica el modelo y cuánto no. Un solo dato, dicho entero."""
    ANCHO, ARRIBA, ALTA = DER - IZQ, 86, 86
    x = datos[0]
    v = float(x["valor"])
    base = ARRIBA + round(ALTA / 2 + 0.36 * CIFRA * G_MAX)
    p = [f'<rect x="{IZQ}" y="{ARRIBA}" width="{ANCHO}" height="{ALTA}" rx="8" '
         f'fill="var(--linea-fuerte)" opacity=".3"/>']
    w = ANCHO * v / 100
    p.append(f'<rect x="{IZQ}" y="{ARRIBA}" width="{w:.1f}" height="{ALTA}" rx="8" '
             f'fill="var(--senal)" opacity=".9"/>')
    p.append(f'<text x="{IZQ + w / 2:.0f}" y="{base}" class="g-num g-num--sobre" '
             f'text-anchor="middle">{_num(x)}%</text>')
    p.append(f'<text x="{IZQ + w + (ANCHO - w) / 2:.0f}" y="{base}" class="g-num" '
             f'text-anchor="middle">{_num(round(100 - v, 4))}%</text>')
    # Los dos rótulos van en LÍNEAS DISTINTAS, no uno a cada lado de la misma.
    # Juntos suman más de cincuenta caracteres y con la letra de móvil se
    # daban un cabezazo en mitad del dibujo. Cada uno sigue del lado de su
    # trozo de barra: el que explica a la izquierda, el resto a la derecha.
    pie = ARRIBA + ALTA + 34
    p.append(f'<text x="{IZQ}" y="{pie}" class="g-pie">{e(x["etiqueta"])}</text>')
    p.append(f'<text x="{DER}" y="{pie + LINEA_PIE}" class="g-pie" text-anchor="end">'
             f'{e(x.get("resto", ""))}</text>')
    cabe(x["etiqueta"], ANCHO, donde=" bajo un reparto")
    cabe(x.get("resto", ""), ANCHO, donde=" bajo un reparto")
    return _svg("".join(p), pie + LINEA_PIE + 22)


def g_flujo(datos):
    """Tres pasos en fila y una rama que se sale. datos: 3 cajas + la rama.

    Es el gráfico más apretado de los siete, y con diferencia: tres cajas en
    fila dejan 190 unidades a cada una, o sea DIEZ caracteres por línea con la
    letra de móvil. Cualquier rótulo más largo hay que partirlo o acortarlo, y
    el generador lo dice al dibujar en vez de dejarlo salir a la web.
    """
    CAJA, PASO, X0 = 190, 207, 16
    ARRIBA, ALTA, MEDIO = 64, 96, 112
    cajas, rama = datos[:3], datos[3]
    p = []
    for i, x in enumerate(cajas):
        px = X0 + i * PASO
        trozos = lineas(x["etiqueta"])
        base = MEDIO + 8 - (LINEA_ROT // 2) * (len(trozos) - 1)
        p.append(f'<rect x="{px}" y="{ARRIBA}" width="{CAJA}" height="{ALTA}" rx="8" '
                 f'fill="none" stroke="var(--linea-fuerte)" stroke-width="1.5"/>')
        for j, linea in enumerate(trozos):
            p.append(f'<text x="{px + CAJA // 2}" y="{base + j * LINEA_ROT}" '
                     f'class="g-rotulo" text-anchor="middle">{e(linea)}</text>')
        cabe(x["etiqueta"], CAJA, LETRA_ROT, " en una caja del flujo")
    for i in range(2):
        px = X0 + CAJA + i * PASO
        p.append(f'<path d="M {px} {MEDIO} l {PASO - CAJA} 0 m -6 -5 l 6 5 l -6 5" '
                 f'fill="none" stroke="var(--senal)" stroke-width="1.5"/>')

    centro = X0 + PASO + CAJA // 2
    rama_x, rama_y = X0 + 2 * PASO, ARRIBA + ALTA + 48
    trozos = lineas(rama["etiqueta"])
    rama_alta = 40 + LINEA_ROT * len(trozos)
    p.append(f'<path d="M {centro} {ARRIBA + ALTA} L {centro} {rama_y + rama_alta // 2} '
             f'L {rama_x} {rama_y + rama_alta // 2}" fill="none" stroke="var(--senal)" '
             f'stroke-width="1.5" stroke-dasharray="5 5" opacity=".8"/>')
    p.append(f'<rect x="{rama_x}" y="{rama_y}" width="{CAJA}" height="{rama_alta}" '
             f'rx="8" fill="none" stroke="var(--senal)" stroke-width="1.5" opacity=".8"/>')
    base = rama_y + rama_alta // 2 + 8 - (LINEA_ROT // 2) * (len(trozos) - 1)
    for j, linea in enumerate(trozos):
        p.append(f'<text x="{rama_x + CAJA // 2}" y="{base + j * LINEA_ROT}" '
                 f'class="g-rotulo" text-anchor="middle">{e(linea)}</text>')
    cabe(rama["etiqueta"], CAJA, LETRA_ROT, " en la rama del flujo")

    pie = rama_y + rama_alta + 44
    for j, linea in enumerate(lineas(rama.get("pie", ""))):
        p.append(f'<text x="320" y="{pie + j * LINEA_PIE}" class="g-pie" '
                 f'text-anchor="middle">{e(linea)}</text>')
    cabe(rama.get("pie", ""), DER - IZQ, donde=" bajo un flujo")
    return _svg("".join(p), pie + LINEA_PIE * len(lineas(rama.get("pie", ""))) + 10)


def g_escalas(datos):
    """DOS reglas graduadas, una encima de otra, para dos escalas distintas.

    Existe por un fallo concreto: la página de videojuegos decía «explica el
    45,5% de la variabilidad de las ventas» cuando ese porcentaje era del
    LOGARITMO de las ventas. Una barra al lado de otra invita justo a esa
    confusión, porque parecen la misma medida. Aquí cada regla lleva su propia
    graduación de 0 a 100 y su propio rótulo de qué mide, y entre las dos hay
    una línea de separación: son dos preguntas, no dos resultados.

    datos: [{"valor": 49.8, "texto": "49,8%", "etiqueta": "...", "pie": "..."}]
    """
    alto = 380
    x0, x1 = 60, 590
    ancho = x1 - x0
    p = [f'<rect x="0" y="0" width="640" height="{alto}" fill="none"/>']

    for i, d in enumerate(datos[:2]):
        cy = 132 + i * 168
        val = float(d["valor"])
        # la regla completa, de 0 a 100: el hueco vacío es parte del dato
        p.append(f'<rect x="{x0}" y="{cy}" width="{ancho}" height="26" rx="4" '
                 f'fill="var(--linea)" opacity=".55"/>')
        p.append(f'<rect x="{x0}" y="{cy}" width="{ancho * val / 100:.1f}" height="26" '
                 f'rx="4" fill="var(--senal)" opacity="{0.95 if i == 0 else 0.6}"/>')
        # graduación cada 25, para que se lea que la escala es de 0 a 100
        for m in (25, 50, 75):
            mx = x0 + ancho * m / 100
            p.append(f'<line x1="{mx:.0f}" y1="{cy - 6}" x2="{mx:.0f}" y2="{cy + 32}" '
                     f'stroke="var(--linea)" stroke-width="1" opacity=".7"/>')
        p.append(f'<line x1="{x0}" y1="{cy - 6}" x2="{x0}" y2="{cy + 32}" '
                 f'stroke="var(--linea-fuerte)" stroke-width="1.4"/>')
        p.append(f'<line x1="{x1}" y1="{cy - 6}" x2="{x1}" y2="{cy + 32}" '
                 f'stroke="var(--linea-fuerte)" stroke-width="1.4"/>')
        # La cifra manda y el rótulo va debajo, en pequeño. Compartiendo línea
        # quedaban a 10 unidades, y dos textos pegados se leen como uno.
        p.append(f'<text class="g-num" x="{x0}" y="{cy - 58}">{_num(d)}</text>')
        p.append(f'<text class="g-pie" x="{x0}" y="{cy - 14}">{e(d["etiqueta"])}</text>')
        if d.get("pie"):
            p.append(f'<text class="g-pie" x="{x1}" y="{cy + 52}" '
                     f'text-anchor="end" opacity=".8">{e(d["pie"])}</text>')

    # la raya que dice «esto de arriba y esto de abajo no son lo mismo»
    p.append(f'<line x1="{x0}" y1="{132 + 96}" x2="{x1}" y2="{132 + 96}" '
             f'stroke="var(--linea-fuerte)" stroke-width="1" stroke-dasharray="3 5" '
             f'opacity=".6"/>')
    return _svg("".join(p), alto)


def g_secuencia(datos):
    """Una serie temporal con la ventana deslizante encima.

    Es el gráfico de deep learning: explica de un vistazo lo que cuestan tres
    párrafos —que el modelo no ve la serie entera, ve una ventana que avanza—
    y de paso enseña dónde caen los tres tramos de la partición cronológica.

    La ventana se mueve con una animación CSS, no con JavaScript, así que la
    para el mismo interruptor que todo lo demás y desaparece sola con
    prefers-reduced-motion. Quieta sigue explicando lo mismo.

    datos: [{"etiqueta": "Entrenamiento", "parte": 0.70}, ...]
    """
    alto = 300
    x0, x1 = 40, 600
    ancho = x1 - x0
    base, amplitud = 168, 46
    p = []

    # los tres tramos, de fondo
    corte = x0
    for i, d in enumerate(datos):
        w = ancho * float(d["parte"])
        p.append(f'<rect x="{corte:.1f}" y="70" width="{w:.1f}" height="150" '
                 f'fill="var(--senal)" opacity="{0.05 + i * 0.045:.3f}"/>')
        if i:
            p.append(f'<line x1="{corte:.1f}" y1="62" x2="{corte:.1f}" y2="228" '
                     f'stroke="var(--linea-fuerte)" stroke-width="1" '
                     f'stroke-dasharray="4 4"/>')
        # Una banda estrecha no admite su rotulo en horizontal: «Validacion»
        # pide 163 unidades y la banda mide 84. Ahi va girado, dentro.
        # Sin rotar. getBBox() —lo que mide la prueba y lo que usa el propio
        # generador para comprobar que algo cabe— devuelve la caja ANTES del
        # transform, así que un texto girado no se puede verificar: pasaría
        # una comprobación que en realidad no se ha hecho. El rótulo de una
        # banda estrecha se abrevia, y el nombre entero está en la tabla de
        # al lado y en la descripción para lectores de pantalla.
        cxb = corte + w / 2
        p.append(f'<text class="g-pie" x="{cxb:.0f}" y="52" text-anchor="middle">'
                 f'{e(d["etiqueta"])}</text>')
        if d.get("pie"):
            p.append(f'<text class="g-pie" x="{corte + w / 2:.0f}" y="252" '
                     f'text-anchor="middle" opacity=".75">{e(d["pie"])}</text>')
        corte += w

    # la serie: una onda con dos periodos, determinista, sin datos inventados
    # (es una ilustración de la forma de una serie, y el sr lo dice)
    import math
    puntos = []
    for k in range(0, 113):
        x = x0 + ancho * k / 112
        y = (base
             - amplitud * math.sin(k / 112 * math.pi * 6)
             - amplitud * 0.35 * math.sin(k / 112 * math.pi * 17))
        puntos.append(f"{x:.1f},{y:.1f}")
    p.append(f'<polyline points="{" ".join(puntos)}" fill="none" '
             f'stroke="var(--senal)" stroke-width="1.8" opacity=".85" '
             f'stroke-linejoin="round"/>')

    # la ventana que avanza
    vw = ancho * 0.13
    p.append(f'<g class="ventana">'
             f'<rect x="{x0}" y="78" width="{vw:.1f}" height="134" rx="3" '
             f'fill="var(--senal)" opacity=".16"/>'
             f'<rect x="{x0}" y="78" width="{vw:.1f}" height="134" rx="3" '
             f'fill="none" stroke="var(--senal)" stroke-width="1.6"/>'
             + "".join(
                 f'<rect class="celda" x="{x0 + 7 + k * ((vw - 14) / 4):.1f}" '
                 f'y="84" width="{(vw - 14) / 4 - 3:.1f}" height="6" rx="2" '
                 f'fill="var(--senal)" style="--i:{k}"/>' for k in range(4))
             + f'</g>')
    return _svg("".join(p), alto)


def g_tira(datos):
    """Una tira de película. Cada fotograma es un tópico.

    Para el trabajo de Letterboxd: los tópicos del modelo puestos como los
    fotogramas de un trozo de celuloide, con sus perforaciones. Los que
    separan idiomas en lugar de temas van marcados, que es el hallazgo.

    Van TRES POR FILA y no seis seguidos, y el motivo es aritmético: con seis
    en fila cada fotograma mide 87 unidades del viewBox y una palabra como
    «festivales» pide 163. Con tres son 184 y entra. Dos tiras en lugar de
    una siguen leyéndose como película.

    Todo se ve de entrada —etiqueta, porcentaje y marca—; al señalar un
    fotograma solo se resalta. Nada se esconde detrás del ratón.
    """
    por_fila = 3
    x0, hueco = 30, 14
    w = (640 - 2 * x0 - hueco * (por_fila - 1)) / por_fila
    marco_alto = 112
    filas = (len(datos) + por_fila - 1) // por_fila
    alto = 40 + filas * (marco_alto + 122) + 30
    p = []

    for fila in range(filas):
        arriba = 46 + fila * (marco_alto + 122)
        trozo = datos[fila * por_fila:(fila + 1) * por_fila]
        # el celuloide de esta tira
        p.append(f'<rect x="{x0 - 14}" y="{arriba - 20}" '
                 f'width="{640 - 2 * (x0 - 14)}" height="{marco_alto + 40}" rx="4" '
                 f'fill="var(--linea)" opacity=".35"/>')
        xper = x0 - 6
        while xper < 640 - x0 + 6:
            for yper in (arriba - 15, arriba + marco_alto + 4):
                p.append(f'<rect x="{xper:.0f}" y="{yper}" width="12" height="9" '
                         f'rx="2" fill="var(--fondo)" opacity=".9"/>')
            xper += 30

        for i, d in enumerate(trozo):
            x = x0 + i * (w + hueco)
            idioma = bool(d.get("idioma"))
            p.append(f'<g class="foto{" foto--idioma" if idioma else ""}" tabindex="0">')
            p.append(f'<rect class="foto__marco" x="{x:.1f}" y="{arriba}" '
                     f'width="{w:.1f}" height="{marco_alto}" rx="3" '
                     f'fill="var(--senal)" opacity="{".13" if idioma else ".07"}"/>')
            p.append(f'<rect class="foto__filo" x="{x:.1f}" y="{arriba}" '
                     f'width="{w:.1f}" height="{marco_alto}" rx="3" fill="none" '
                     f'stroke="var(--senal)" stroke-width="{1.8 if idioma else 1}" '
                     f'opacity="{".95" if idioma else ".45"}"/>')
            cx = x + w / 2
            p.append(f'<text class="g-num" x="{cx:.0f}" y="{arriba + 56}" '
                     f'text-anchor="middle">{_num(d)}</text>')
            p.append(f'<text class="g-pie" x="{cx:.0f}" y="{arriba + 92}" '
                     f'text-anchor="middle">{e(d["etiqueta"])}</text>')
            # El descriptor va DEBAJO del celuloide, no dentro del fotograma:
            # dentro no cabe sin apretar la cifra contra el rotulo.
            if d.get("pie"):
                for k, linea in enumerate(str(d["pie"]).split("|")):
                    p.append(f'<text class="g-pie" x="{cx:.0f}" '
                             f'y="{arriba + marco_alto + 46 + k * 34}" '
                             f'text-anchor="middle" opacity=".8">{e(linea)}</text>')
            if idioma:
                p.append(f'<circle cx="{x + 12:.0f}" cy="{arriba + 13}" r="3.6" '
                         f'fill="var(--senal)"/>')
            p.append('</g>')

    p.append(f'<text class="g-pie" x="320" y="{alto - 12}" text-anchor="middle" '
             f'opacity=".8">el punto marca los tópicos de idioma</text>')
    return _svg("".join(p), alto)


def g_hud(datos):
    """Un panel de estadísticas con medidores por bloques.

    Para videojuegos. La diferencia con una barra normal no es decorativa: un
    medidor partido en bloques se puede CONTAR, y contar es lo que hace que
    «0,291 frente a 0,498» deje de ser dos números y pase a ser seis bloques
    frente a diez. Es la forma en que un juego enseña una estadística desde
    hace cuarenta años, y funciona por el mismo motivo.

    La cruceta de la esquina es la marca temática y no lleva dato ninguno:
    está para decir de qué habla el panel, no para explicar nada.

    datos: [{"valor": .4976, "texto": "0,498", "etiqueta": "Boosting",
             "destacada": true}]
    """
    alto = 400
    p = [f'<rect x="30" y="50" width="580" height="304" rx="10" '
         f'fill="var(--senal)" opacity=".045"/>',
         f'<rect x="30" y="50" width="580" height="304" rx="10" fill="none" '
         f'stroke="var(--senal-linea)" stroke-width="1"/>']

    # El recorrido, por el canal de la izquierda: un punto por modelo y una
    # figura que baja parándose en cada uno. Los puntos NO llevan dato: el
    # dato son los bloques y la cifra, que están escritos desde el principio.
    x_via = 54
    for i_p in range(len(datos)):
        p.append(f'<circle class="punto" cx="{x_via}" cy="{140 + i_p * 62}" '
                 f'r="4" fill="var(--senal)" style="--i:{i_p}"/>')
    # Dos mandíbulas que giran en sentidos opuestos: eso es una boca. El
    # centro de giro va escrito en el CSS y es este mismo punto, porque el
    # grupo de fuera solo traslada.
    p.append('<g class="come">'
             f'<path class="come__quijada come__quijada--izq" '
             f'd="M{x_via},129 A11,11 0 0 0 {x_via},151 Z" fill="var(--senal)"/>'
             f'<path class="come__quijada come__quijada--der" '
             f'd="M{x_via},129 A11,11 0 0 1 {x_via},151 Z" fill="var(--senal)"/>'
             '</g>')

    BLOQUES, ancho_b, hueco_b = 20, 9.5, 2.0
    x_med = 236
    tope = max([float(d["valor"]) for d in datos] + [0.001])
    escala = 0.5 if tope <= 0.5 else 1.0

    for i, d in enumerate(datos):
        y = 140 + i * 62
        mejor = bool(d.get("destacada"))
        if mejor:
            p.append(f'<rect x="68" y="{y - 26}" width="530" height="38" rx="5" '
                     f'fill="var(--senal)" opacity=".07"/>')
            p.append(f'<path d="M72 {y - 12} L78 {y - 7} L72 {y - 2} Z" '
                     f'fill="var(--senal)"/>')
        p.append(f'<text class="g-pie" x="{88 if mejor else 76}" y="{y - 2}">'
                 f'{e(d["etiqueta"])}</text>')

        llenos = round(float(d["valor"]) / escala * BLOQUES)
        for k in range(BLOQUES):
            bx = x_med + k * (ancho_b + hueco_b)
            lleno = k < llenos
            p.append(f'<rect x="{bx:.1f}" y="{y - 20}" width="{ancho_b}" '
                     f'height="20" rx="1.5" fill="var(--senal)" '
                     f'opacity="{".92" if lleno and mejor else (".62" if lleno else ".13")}"/>')
        p.append(f'<text class="g-num" x="598" y="{y}" text-anchor="end">'
                 f'{_num(d)}</text>')

    # El pie va fuera del panel, a la izquierda: centrado no cabria.
    p.append(f'<text class="g-pie" x="50" y="{alto - 11}" opacity=".75">'
             f'cada bloque, cinco centésimas de R²</text>')
    return _svg("".join(p), alto)


def g_botella(datos):
    """Las fases de la campaña apiladas con perfil de envase.

    Para Lipton. Las cuatro fases ya estaban, en un embudo; aquí son las
    cuatro franjas de una botella vista de frente —cuello estrecho arriba,
    cuerpo abajo—, que es la pieza central de la propia campaña y lo dice su
    ficha: «botella con cubitos de metal».

    No es una botella dibujada: son cuatro rectángulos de anchos distintos.
    La forma la pone quien mira.

    datos: [{"valor": "01", "etiqueta": "Expectación|dos semanas", "parte": .46}]
    """
    n = max(1, len(datos))
    alto = 160 + n * 72
    cx = 150
    anchos = [56, 108, 152, 152, 152, 152][:n]
    p = [f'<rect x="{cx - 20}" y="70" width="40" height="22" rx="4" '
         f'fill="var(--senal)" opacity=".55"/>']

    for i, d in enumerate(datos):
        w = anchos[i]
        y = 92 + i * 72
        p.append(f'<rect x="{cx - w / 2:.0f}" y="{y}" width="{w}" height="72" '
                 f'rx="4" fill="var(--senal)" '
                 f'opacity="{0.16 + i * 0.13:.2f}"/>')
        p.append(f'<rect x="{cx - w / 2:.0f}" y="{y}" width="{w}" height="72" '
                 f'rx="4" fill="none" stroke="var(--senal)" stroke-width="1" '
                 f'opacity=".5"/>')
        p.append(f'<text class="g-num" x="{cx}" y="{y + 48}" '
                 f'text-anchor="middle">{_num(d)}</text>')
        # Los cubitos de metal. Están en la ficha del proyecto —«botella con
        # cubitos de metal»— y son la razón de que la botella suene al
        # agitarla, que es el nombre de la campaña. Solo van en las franjas
        # anchas, que es donde cabe algo sin tocar la cifra.
        if w >= 140:
            for k in range(2):
                p.append(f'<rect class="cubito" x="{cx + w / 2 - 24 - k * 24:.0f}" '
                         f'y="{y + 22 + k * 16}" width="15" height="15" rx="3" '
                         f'fill="var(--senal)" opacity=".55" '
                         f'style="--i:{i * 2 + k}"/>')
        for k, linea in enumerate(str(d["etiqueta"]).split("|")):
            p.append(f'<text class="g-pie" x="268" y="{y + 20 + k * 34}">'
                     f'{e(linea)}</text>')

    p.append(f'<text class="g-pie" x="140" y="{alto - 22}" opacity=".75">'
             f'la campaña, fase a fase</text>')
    return _svg("".join(p), alto)


def g_pista(datos):
    """Tres pistas de tenis vistas desde arriba, una por superficie.

    Para el trabajo de apuestas. La forma es la que hace que se entienda de
    qué se habla sin leer nada; el dato es el tono del suelo, que se llena
    tanto más cuanto más gana el jugador más alto. La línea de red y las de
    saque están porque sin ellas un rectángulo no es una pista.

    El 50% —el punto en que la altura daría igual— va marcado en las tres.

    datos: [{"valor": 56.96, "texto": "56,96%", "etiqueta": "Hierba",
             "destacada": true}]
    """
    alto = 412
    n = max(1, len(datos))
    x0, hueco = 60, 34
    w = (640 - 2 * x0 - hueco * (n - 1)) / n
    arriba, h = 92, 200

    for_p = []
    for i, d in enumerate(datos):
        x = x0 + i * (w + hueco)
        val = float(d["valor"])
        # cuánto se aparta del 50: es el dato, y va del tono del suelo
        fuerza = max(0.0, min(1.0, (val - 50) / 10))
        destacada = bool(d.get("destacada"))
        for_p.append(f'<g class="pista{" pista--gana" if destacada else ""}" tabindex="0">')
        for_p.append(f'<text class="g-pie" x="{x + w / 2:.0f}" y="{arriba - 24}" '
                     f'text-anchor="middle">{e(d["etiqueta"])}</text>')
        # el suelo
        for_p.append(f'<rect class="pista__suelo" x="{x:.1f}" y="{arriba}" '
                     f'width="{w:.1f}" height="{h}" rx="3" fill="var(--senal)" '
                     f'opacity="{0.07 + fuerza * 0.20:.3f}"/>')
        # el marco de dobles y el de individuales
        for_p.append(f'<rect x="{x:.1f}" y="{arriba}" width="{w:.1f}" height="{h}" '
                     f'rx="3" fill="none" stroke="var(--senal)" stroke-width="1.4" '
                     f'opacity=".75"/>')
        m = w * 0.13
        for_p.append(f'<line x1="{x + m:.1f}" y1="{arriba}" x2="{x + m:.1f}" '
                     f'y2="{arriba + h}" stroke="var(--senal)" stroke-width="1" '
                     f'opacity=".4"/>')
        for_p.append(f'<line x1="{x + w - m:.1f}" y1="{arriba}" '
                     f'x2="{x + w - m:.1f}" y2="{arriba + h}" '
                     f'stroke="var(--senal)" stroke-width="1" opacity=".4"/>')
        # la red, en medio
        for_p.append(f'<line x1="{x - 6:.1f}" y1="{arriba + h / 2:.0f}" '
                     f'x2="{x + w + 6:.1f}" y2="{arriba + h / 2:.0f}" '
                     f'stroke="var(--senal)" stroke-width="2.2" opacity=".9" '
                     f'stroke-dasharray="2 3"/>')
        # las de saque
        for lado in (0.26, 0.74):
            for_p.append(f'<line x1="{x + m:.1f}" y1="{arriba + h * lado:.0f}" '
                         f'x2="{x + w - m:.1f}" y2="{arriba + h * lado:.0f}" '
                         f'stroke="var(--senal)" stroke-width="1" opacity=".4"/>')
        for_p.append(f'<line x1="{x + w / 2:.1f}" y1="{arriba + h * 0.26:.0f}" '
                     f'x2="{x + w / 2:.1f}" y2="{arriba + h * 0.74:.0f}" '
                     f'stroke="var(--senal)" stroke-width="1" opacity=".4"/>')
        # la cifra, sobre la red
        for_p.append(f'<text class="g-num" x="{x + w / 2:.0f}" '
                     f'y="{arriba + h / 2 - 26:.0f}" text-anchor="middle">'
                     f'{_num(d)}</text>')
        # La pelota, solo en la pista que gana. Un bote y para: es un
        # gesto, no una animación deportiva. Va en la mitad de abajo, que
        # es la única parte de la pista donde no hay ningún texto.
        if destacada:
            for_p.append(f'<circle class="pelota" cx="{x + w / 2:.0f}" '
                         f'cy="{arriba + h / 2 + 12:.0f}" r="6" '
                         f'fill="var(--senal)"/>')
        # El pie va en dos líneas —la cifra y la palabra— porque en una
        # sola dos pistas vecinas se tocarían.
        for k, linea in enumerate(str(d.get("pie") or "").split("|")):
            if not linea:
                continue
            for_p.append(f'<text class="g-pie" x="{x + w / 2:.0f}" '
                         f'y="{arriba + h + 30 + k * 34}" text-anchor="middle" '
                         f'opacity=".8">{e(linea)}</text>')
        for_p.append('</g>')

    for_p.append(f'<text class="g-pie" x="320" y="{alto - 8}" '
                 f'text-anchor="middle" opacity=".75">'
                 f'gana el más alto · 50% sin ventaja</text>')
    return _svg("".join(for_p), alto)


def g_ascensor(datos):
    """Las fases del trabajo, de arriba abajo, con una luz que las recorre.

    Para el TFM, que es el único de los seis que está organizado por fases de
    verdad y no por apartados de una memoria. La forma es un raíl vertical con
    una parada por fase; la luz baja, se detiene en cada una el tiempo de
    leerla, llega abajo y vuelve arriba.

    Las paradas NO se encienden solas: están todas escritas y legibles desde
    el primer momento. Lo que hace la luz es marcar por dónde va, que es un
    añadido, no el dato. Por eso con el movimiento parado —o con
    prefers-reduced-motion— se quedan las seis encendidas y la pieza sigue
    contando exactamente lo mismo.

    El paso entre paradas es 72 y la luz se mueve en unidades del viewBox, no
    en píxeles de pantalla: dentro de un SVG un translateY(72px) de CSS son 72
    unidades del sistema local, así que la animación escala con el dibujo.

    datos: [{"etiqueta": "El dataset", "dato": "24.365 leads · 44 variables"}]
    """
    n = max(1, len(datos))
    x_rail, x_txt, paso, y0 = 88, 126, 72, 64
    alto = y0 + (n - 1) * paso + 82

    p = [f'<line x1="{x_rail}" y1="{y0 - 26}" x2="{x_rail}" '
         f'y2="{y0 + (n - 1) * paso + 26}" stroke="var(--senal-linea)" '
         f'stroke-width="2"/>']

    for i, d in enumerate(datos):
        y = y0 + i * paso
        p.append(f'<g class="parada" tabindex="0" style="--i:{i}">')
        p.append(f'<g class="parada__cuerpo">')
        p.append(f'<circle cx="{x_rail}" cy="{y}" r="13" fill="var(--fondo)" '
                 f'stroke="var(--senal-linea)" stroke-width="1.5"/>')
        p.append(f'<circle class="parada__punto" cx="{x_rail}" cy="{y}" r="6" '
                 f'fill="var(--senal)"/>')
        p.append(f'<text class="g-pie" x="{x_txt}" y="{y - 6}">'
                 f'{e(d["etiqueta"])}</text>')
        p.append(f'<text class="g-pie" x="{x_txt}" y="{y + 28}" opacity=".72">'
                 f'{e(d["dato"])}</text>')
        p.append('</g></g>')

    # La luz. Va la última para quedar por encima de las paradas, y no lleva
    # texto: es un adorno con sentido, no un dato.
    p.append(f'<g class="ascensor" style="--paradas:{n}">'
             f'<circle class="ascensor__halo" cx="{x_rail}" cy="{y0}" r="20" '
             f'fill="var(--senal)" opacity=".16"/>'
             f'<circle class="ascensor__nucleo" cx="{x_rail}" cy="{y0}" r="9" '
             f'fill="none" stroke="var(--senal)" stroke-width="2.5"/></g>')

    p.append(f'<text class="g-pie" x="{x_txt}" y="{alto - 14}" opacity=".75">'
             f'el trabajo, fase a fase</text>')
    return _svg("".join(p), alto)


def g_matriz(datos):
    """Modelos por métricas, en celdas teñidas. Una tabla que no es una tabla.

    Para el TFM. Tres modelos y tres métricas caben en una tabla, y la tabla
    se lee bien; lo que la tabla NO hace es dejar ver de un vistazo cuál gana
    en cada columna. Aquí el tono de cada celda sale de su columna: el mejor
    de los tres queda más encendido, el peor más apagado.

    «Mejor» no siempre es «más grande»: en la caída de validación a test, el
    mejor es el más pequeño. Eso lo dice la columna con "menor_mejor", y no
    se deduce del número. Teñir al revés esa columna sería decir que caer
    mucho está bien.

    datos: {"columnas": [{"etiqueta": "CV"}, ...],
            "filas": [{"etiqueta": "Random Forest", "destacada": true,
                       "valores": [.698, .691, .007],
                       "textos": ["0,698", "0,691", "0,007"]}]}
    """
    cols, filas = datos["columnas"], datos["filas"]
    nc, nf = len(cols), len(filas)
    x0, ancho_c, hueco_c = 280, 110, 10
    y0, paso = 118, 78
    alto = y0 + (nf - 1) * paso + 62

    def centro(j):
        return x0 + j * (ancho_c + hueco_c) + ancho_c / 2

    p = []
    for j, c in enumerate(cols):
        p.append(f'<text class="g-pie" x="{centro(j):.0f}" y="{y0 - 54}" '
                 f'text-anchor="middle" opacity=".7">{e(c["etiqueta"])}</text>')

    for j, c in enumerate(cols):
        vals = [float(fi["valores"][j]) for fi in filas]
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or 1.0
        for i, fi in enumerate(filas):
            v = float(fi["valores"][j])
            bien = (hi - v) / span if c.get("menor_mejor") else (v - lo) / span
            y = y0 + i * paso
            x = x0 + j * (ancho_c + hueco_c)
            p.append(f'<rect x="{x}" y="{y - 46}" width="{ancho_c}" height="60" '
                     f'rx="6" fill="var(--senal)" '
                     f'opacity="{0.09 + bien * 0.27:.3f}"/>')
            p.append(f'<rect x="{x}" y="{y - 46}" width="{ancho_c}" height="60" '
                     f'rx="6" fill="none" stroke="var(--senal-linea)" '
                     f'stroke-width="1" opacity=".5"/>')
            p.append(f'<text class="g-pie" x="{x + ancho_c / 2:.0f}" y="{y - 8}" '
                     f'text-anchor="middle">{e(fi["textos"][j])}</text>')

    for i, fi in enumerate(filas):
        y = y0 + i * paso
        if fi.get("destacada"):
            p.append(f'<rect x="26" y="{y - 50}" width="4" height="68" rx="2" '
                     f'fill="var(--senal)"/>')
        p.append(f'<text class="g-pie" x="40" y="{y - 8}" '
                 f'opacity="{"1" if fi.get("destacada") else ".78"}">'
                 f'{e(fi["etiqueta"])}</text>')

    p.append(f'<text class="g-pie" x="40" y="{alto - 12}" opacity=".75">'
             f'mejor de la columna, más encendido</text>')
    return _svg("".join(p), alto)


def g_pantalla(datos):
    """Una pantalla de cine con dos cifras dentro y butacas delante.

    Para Letterboxd. La comparación A/B ya estaba, en dos medidores; en
    medidores podría ser de cualquier cosa. Aquí es lo que es: dos versiones
    del mismo corpus proyectadas una al lado de la otra.

    Las butacas de abajo son siluetas, no un dibujo: seis rectángulos de
    alturas distintas hacen una fila de espaldas de butaca y no hacen falta
    más. La pantalla se enciende al entrar en el viewport, y se enciende una
    vez: no parpadea.

    datos: [{"texto": "0,6038", "etiqueta": "Multilingüe"}, ...]
    """
    alto = 430
    izq, der = 190, 450
    p = [f'<rect x="60" y="56" width="520" height="250" rx="8" '
         f'fill="var(--senal)" opacity=".04"/>',
         f'<rect class="pantalla__luz" x="68" y="64" width="504" height="234" '
         f'rx="6" fill="var(--senal)" opacity=".10"/>',
         f'<rect x="60" y="56" width="520" height="250" rx="8" fill="none" '
         f'stroke="var(--senal-linea)" stroke-width="1.5"/>']

    # La barra bajo cada cifra. Es lo que hacían los medidores que había
    # antes: sin ella son dos números sueltos y el ojo no ve que uno es
    # menor. Van proporcionales al mayor de los dos, no a 1.
    tope = max(float(x["valor"]) for x in datos) or 1.0
    for cx, d in zip((izq, der), datos):
        p.append(f'<text class="g-num" x="{cx}" y="170" text-anchor="middle">'
                 f'{_num(d)}</text>')
        p.append(f'<text class="g-pie" x="{cx}" y="232" text-anchor="middle">'
                 f'{e(d["etiqueta"])}</text>')
        bw = 180 * float(d["valor"]) / tope
        p.append(f'<rect x="{cx - 90}" y="190" width="180" height="8" rx="4" '
                 f'fill="var(--senal)" opacity=".14"/>')
        p.append(f'<rect x="{cx - 90}" y="190" width="{bw:.1f}" height="8" '
                 f'rx="4" fill="var(--senal)" opacity=".8"/>')
    p.append('<text class="g-pie" x="320" y="274" text-anchor="middle" '
             'opacity=".72">coherencia c_v · seis tópicos</text>')

    # La fila de butacas. Alturas distintas para que sea una fila y no una
    # regla; van por debajo de la pantalla, que es donde está el público.
    for k, altura in enumerate((34, 46, 38, 48, 36, 44, 34)):
        bx = 96 + k * 66
        p.append(f'<path d="M{bx},372 v-{altura - 12} a12,12 0 0 1 12,-12 '
                 f'h20 a12,12 0 0 1 12,12 v{altura - 12} Z" '
                 f'fill="var(--senal)" opacity=".22"/>')

    p.append(f'<text class="g-pie" x="320" y="{alto - 8}" text-anchor="middle" '
             f'opacity=".75">el corpus entero contra solo inglés</text>')
    return _svg("".join(p), alto)


def g_recorrido(datos):
    """El camino real de un lead, etapa a etapa, con el final marcado.

    Reconstruye el diagrama de la defensa: cinco etapas encadenadas de la
    captación a la solicitud. NO es el ascensor de las fases y no se parece:
    allí el texto va fuera de un raíl fino y una luz se detiene en cada
    parada; aquí cada etapa es una caja con su texto dentro y entre caja y
    caja hay una flecha, que es como se dibuja un proceso de negocio.

    Lo que se mueve es un pulso que baja por los conectores, no un marcador
    que viaja. Los conectores están pintados SIEMPRE —hay una línea fija
    debajo y una brillante encima—, así que sin animación el diagrama sigue
    completo.

    El ancho manda sobre todo lo demás: con 460 unidades de texto útil caben
    28 caracteres por línea, y por eso los rótulos largos vienen partidos con
    «|» desde el JSON en vez de partirse solos.

    datos: [{"etiqueta": "Zona MQL", "detalle": "Alta → Nurturing →|Scoring",
             "enfasis": "fuerte"}]
    """
    X, ANCHO, HUECO = 60, 500, 28
    cajas, y = [], 40
    for d in datos:
        trozos = [l for l in lineas(d.get("detalle", "")) if l]
        alta = 40 + 34 * max(1, len(trozos))
        cajas.append((y, alta, trozos, d))
        y += alta + HUECO
    alto = y - HUECO + 56

    p = []
    for i, (cy, alta, trozos, d) in enumerate(cajas):
        enf = d.get("enfasis", "")
        relleno = {"fuerte": ".30", "medio": ".13"}.get(enf, ".05")
        p.append(f'<rect x="{X}" y="{cy}" width="{ANCHO}" height="{alta}" rx="8" '
                 f'fill="var(--senal)" opacity="{relleno}"/>')
        p.append(f'<rect x="{X}" y="{cy}" width="{ANCHO}" height="{alta}" rx="8" '
                 f'fill="none" stroke="var(--senal)" stroke-width="1.4" '
                 f'opacity="{".85" if enf else ".45"}"/>')
        if enf == "fuerte":
            p.append(f'<rect x="{X}" y="{cy + 10}" width="4" height="{alta - 20}" '
                     f'rx="2" fill="var(--senal)"/>')
        p.append(f'<text class="g-pie" x="{X + 20}" y="{cy + 28}">'
                 f'{e(d["etiqueta"])}</text>')
        # Sobre el relleno fuerte el texto sube: es donde menos
        # contraste queda y es justo la etapa que hay que leer.
        tinta = ".92" if enf == "fuerte" else ".72"
        for k, linea in enumerate(trozos):
            p.append(f'<text class="g-pie" x="{X + 20}" y="{cy + 62 + k * 34}" '
                     f'opacity="{tinta}">{e(linea)}</text>')

        # El conector con la etapa siguiente: una línea fija y encima otra
        # que se enciende. La fija es la que garantiza que el diagrama se
        # entienda con el movimiento parado.
        if i < len(cajas) - 1:
            cx, y1, y2 = X + ANCHO / 2, cy + alta, cy + alta + HUECO
            p.append(f'<line x1="{cx}" y1="{y1}" x2="{cx}" y2="{y2 - 7}" '
                     f'stroke="var(--senal)" stroke-width="2.4" opacity=".4"/>')
            p.append(f'<line class="tramo" x1="{cx}" y1="{y1}" x2="{cx}" '
                     f'y2="{y2 - 7}" stroke="var(--senal)" stroke-width="2" '
                     f'style="--i:{i}"/>')
            p.append(f'<path d="M{cx - 7} {y2 - 11} L{cx} {y2} L{cx + 7} {y2 - 11} Z" '
                     f'fill="var(--senal)" opacity=".7"/>')

    p.append(f'<text class="g-pie" x="{X}" y="{alto - 14}" opacity=".75">'
             f'de la captación a la solicitud</text>')
    return _svg("".join(p), alto)


def g_nodos(datos):
    """El asistente, como grafo: un centro y cuatro piezas alrededor.

    Para el segundo módulo del TFM. Antes era un flujo de cajas en fila, que
    es la misma forma que el recorrido del lead; y el recorrido del lead
    explica mejor el trabajo, así que se queda con esa forma. El asistente
    pasa a lo que es: una arquitectura, no un camino. Un grafo radial no
    tiene principio ni final, y eso es exactamente lo que se quiere decir.

    Es además la pieza más pequeña de la página —372 de alto frente a 680 del
    recorrido y 506 del ascensor—, que es la jerarquía que le toca.

    datos: {"centro": "RAG", "arriba": {...}, "izq": {...}, "der": {...},
            "abajo": {...}, "nota": "..."}
    """
    alto = 382
    CX, CY, R = 320, 166, 46
    p = []

    def pastilla(x, ancho, base, texto, guion=False):
        p.append(f'<rect x="{x}" y="{base - 40}" width="{ancho}" height="54" '
                 f'rx="12" fill="var(--senal)" opacity=".07"/>')
        p.append(f'<rect x="{x}" y="{base - 40}" width="{ancho}" height="54" '
                 f'rx="12" fill="none" stroke="var(--senal)" stroke-width="1.3" '
                 f'opacity=".55"'
                 + (' stroke-dasharray="5 4"' if guion else "") + '/>')
        p.append(f'<text class="g-pie g-pie--nodo" x="{x + ancho / 2:.0f}" '
                 f'y="{base}" text-anchor="middle">{e(texto)}</text>')

    # Los cuatro radios. El de abajo va de puntos: es el que se usa cuando la
    # documentación NO da para responder, y eso no es el camino normal.
    for x1, y1, x2, y2, guion in ((CX - R, CY, 202, CY, False),
                                  (CX + R, CY, 428, CY, False),
                                  (CX, CY - R, CX, 80, False),
                                  (CX, CY + R, CX, 246, True)):
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                 f'stroke="var(--senal)" stroke-width="1.6" opacity=".45"'
                 + (' stroke-dasharray="5 4"' if guion else "") + '/>')

    pastilla(104, 432, 66, datos["arriba"])
    pastilla(18, 184, 176, datos["izq"])
    pastilla(428, 204, 176, datos["der"])
    pastilla(198, 244, 286, datos["abajo"], guion=True)

    p.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="var(--senal)" '
             f'opacity=".16"/>')
    p.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" '
             f'stroke="var(--senal)" stroke-width="1.8"/>')
    p.append(f'<text class="g-pie g-pie--nodo" x="{CX}" y="{CY + 12}" '
             f'text-anchor="middle">{e(datos["centro"])}</text>')

    p.append(f'<text class="g-pie" x="320" y="328" text-anchor="middle" '
             f'opacity=".72">{e(datos["nota"])}</text>')
    p.append(f'<text class="g-pie" x="320" y="{alto - 20}" text-anchor="middle" '
             f'opacity=".75">{e(datos["pie"])}</text>')
    return _svg("".join(p), alto)


# =====================================================================
# PIEZAS DE CABINA
# =====================================================================
#
# Cinco graficos con aire de telemetria de simulador. Son tipos normales
# del registro GRAFICOS: se piden desde el JSON como cualquier otro y no
# hay una sola rama que mire de que proyecto se trata.
#
# LA REGLA QUE MANDA EN TODOS: el dibujo no puede decir mas de lo que dicen
# los numeros. Un velocimetro que marca 5,00 frente a 4,17 sugiere que A
# gana, y lo que el experimento midio es que NO se pueden separar. Por eso
# la pieza de H1 no son dos agujas: son dos agujas MAS la banda del
# intervalo cruzando el cero, que es el dato de verdad.


def _arco(cx, cy, r, t0, t1):
    """Camino de un arco entre dos angulos en grados, 0 = a la izquierda."""
    import math
    x0 = cx + r * math.cos(math.radians(t0))
    y0 = cy + r * math.sin(math.radians(t0))
    x1 = cx + r * math.cos(math.radians(t1))
    y1 = cy + r * math.sin(math.radians(t1))
    grande = 1 if abs(t1 - t0) > 180 else 0
    return f"M {x0:.1f} {y0:.1f} A {r} {r} 0 {grande} 1 {x1:.1f} {y1:.1f}"


def _aguja(cx, cy, r, frac):
    """Punta de la aguja para una fraccion 0..1 sobre el semicirculo alto."""
    import math
    a = math.radians(180 + 180 * max(0.0, min(1.0, frac)))
    return cx + r * math.cos(a), cy + r * math.sin(a)


def g_dial(datos):
    """H1 como cuadro de instrumentos. La incertidumbre es la protagonista.

    Arriba, dos diales con la tasa de cada brazo. Abajo, y ocupando mas
    sitio que los dos diales juntos, el intervalo de confianza sobre un eje
    con el CERO marcado. Esa jerarquia es deliberada: si los diales fueran
    lo mayor, la pieza contaria «A marca mas que B», que es justo la lectura
    que el resultado no admite.
    """
    d = datos[0] if isinstance(datos, list) else datos
    a, b = float(d["a"]), float(d["b"])
    dif = float(d["dif"])
    ic0, ic1 = float(d["ic"][0]), float(d["ic"][1])
    tope = float(d.get("tope", 10))          # fondo de escala de los diales
    p = []

    # --- los dos diales -------------------------------------------------
    R = 74
    for i, (rot, val) in enumerate((("Brazo A", a), ("Brazo B", b))):
        cx, cy = 172 + i * 296, 128
        p.append(f'<path d="{_arco(cx, cy, R, 180, 360)}" fill="none" '
                 f'stroke="var(--linea-fuerte)" stroke-width="7" opacity=".34" '
                 f'stroke-linecap="round"/>')
        # Ticks: dan lectura de escala sin escribir once numeros.
        for k in range(11):
            import math
            ang = math.radians(180 + 18 * k)
            r0, r1 = R - 11, R - 4
            p.append(f'<line x1="{cx + r0 * math.cos(ang):.1f}" '
                     f'y1="{cy + r0 * math.sin(ang):.1f}" '
                     f'x2="{cx + r1 * math.cos(ang):.1f}" '
                     f'y2="{cy + r1 * math.sin(ang):.1f}" '
                     f'stroke="var(--linea)" stroke-width="1.4" opacity=".7"/>')
        frac = max(0.0, min(1.0, val / tope))
        p.append(f'<path d="{_arco(cx, cy, R, 180, 180 + 180 * frac)}" fill="none" '
                 f'stroke="var(--senal)" stroke-width="7" opacity=".92" '
                 f'stroke-linecap="round"/>')
        ax, ay = _aguja(cx, cy, R - 16, frac)
        p.append(f'<line x1="{cx}" y1="{cy}" x2="{ax:.1f}" y2="{ay:.1f}" '
                 f'stroke="var(--senal-viva)" stroke-width="2.4" stroke-linecap="round"/>')
        p.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="var(--senal-viva)"/>')
        # Dos decimales SIEMPRE: 5,00 y 4,17 se comparan de un vistazo, y
        # «5» a secas al lado de «4,17» sugiere una precision distinta.
        texto = f"{val:.2f}".replace(".", ",")
        p.append(f'<text x="{cx}" y="{cy + 42}" class="g-num" text-anchor="middle">'
                 f'{texto}%</text>')
        p.append(f'<text x="{cx}" y="{cy + 100}" class="g-pie" text-anchor="middle">'
                 f'{e(rot)}</text>')
        cabe(rot, 240, donde=" bajo un dial")

    # --- el intervalo, que es la pieza principal ------------------------
    Y = 296
    x0, x1 = IZQ + 6, DER - 6
    lo, hi = -5.0, 3.0                        # eje fijo, con holgura a los dos lados
    def X(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    p.append(f'<line x1="{x0}" y1="{Y}" x2="{x1}" y2="{Y}" '
             f'stroke="var(--linea)" stroke-width="1.4"/>')
    for v in (-5, -4, -3, -2, -1, 0, 1, 2, 3):
        p.append(f'<line x1="{X(v):.1f}" y1="{Y - 5}" x2="{X(v):.1f}" y2="{Y + 5}" '
                 f'stroke="var(--linea)" stroke-width="1.2" opacity=".8"/>')
    # La banda del intervalo.
    p.append(f'<rect x="{X(ic0):.1f}" y="{Y - 19}" width="{X(ic1) - X(ic0):.1f}" '
             f'height="38" rx="7" fill="var(--senal)" opacity=".26"/>')
    p.append(f'<line x1="{X(ic0):.1f}" y1="{Y - 19}" x2="{X(ic0):.1f}" y2="{Y + 19}" '
             f'stroke="var(--senal-viva)" stroke-width="2.2"/>')
    p.append(f'<line x1="{X(ic1):.1f}" y1="{Y - 19}" x2="{X(ic1):.1f}" y2="{Y + 19}" '
             f'stroke="var(--senal-viva)" stroke-width="2.2"/>')
    # El cero, en blanco y a toda altura: es la linea que el intervalo cruza.
    p.append(f'<line x1="{X(0):.1f}" y1="{Y - 34}" x2="{X(0):.1f}" y2="{Y + 34}" '
             f'stroke="#FFFFFF" stroke-width="2" opacity=".9"/>')
    p.append(f'<text x="{X(0):.1f}" y="{Y - 42}" class="g-pie" text-anchor="middle">0</text>')
    # La diferencia observada.
    p.append(f'<circle cx="{X(dif):.1f}" cy="{Y}" r="6" fill="var(--senal-viva)"/>')

    p.append(f'<text x="{X(ic0):.1f}" y="{Y + 42}" class="g-pie" text-anchor="middle">'
             f'{_num(ic0)}</text>')
    p.append(f'<text x="{X(ic1):.1f}" y="{Y + 42}" class="g-pie" text-anchor="middle">'
             f'{_num(ic1)}</text>')
    # Va una linea MAS ARRIBA que el rotulo del cero. Con los dos a la misma
    # altura se leian pegados —«-0,83 pp 0»—, porque solo los separan 0,83
    # unidades de un eje de ocho y el texto es mas ancho que ese hueco.
    # Y bastante mas arriba que el rotulo del cero. Con 26 unidades de
    # separacion las dos CAJAS de texto seguian solapandose 11 unidades —la
    # caja de .g-pie mide unas 32 de alto, no 12—, y «-0,83 pp» se leia
    # pegado al «0». Con 40 no comparten franja y la comprobacion las ignora.
    p.append(f'<text x="{X(dif):.1f}" y="{Y - 82}" class="g-pie" text-anchor="middle">'
             f'{_num(dif)} pp</text>')
    p.append(f'<line x1="{X(dif):.1f}" y1="{Y - 72}" x2="{X(dif):.1f}" y2="{Y - 24}" '
             f'stroke="var(--senal-viva)" stroke-width="1" opacity=".55"/>')

    # El veredicto, escrito. No se deduce del dibujo: se dice.
    # El veredicto va MUY por debajo de los extremos del intervalo. La caja de
    # .g-num sube casi 50 unidades sobre su linea base, asi que con +86 se
    # solapaba con «-3,89», que esta en +42. Aqui la aritmetica es la que
    # manda y no el ojo: 42 (extremos) + 32 (media caja de .g-pie) + 48 (caja
    # de .g-num) = 122, y se redondea hacia arriba.
    ver = d.get("veredicto", "INCONCLUYENTE")
    p.append(f'<text x="320" y="{Y + 128}" class="g-num" text-anchor="middle">{e(ver)}</text>')
    p.append(f'<text x="320" y="{Y + 164}" class="g-pie" text-anchor="middle">'
             f'{e(d.get("pie", "el intervalo cruza el cero"))}</text>')
    cabe(d.get("pie", ""), DER - IZQ, donde=" bajo el intervalo")
    return _svg("".join(p), Y + 190)


def g_telemetria(datos):
    """Tres canales de estado, con su anillo, su cifra y su pie.

    Son MEDIDAS del estado en que quedo el experimento, no causas. El pie de
    cada tarjeta lo dice y el texto de al lado tambien; aqui la forma ayuda:
    tres anillos identicos y ninguna flecha entre ellos, porque no hay
    relacion demostrada que dibujar.
    """
    n = len(datos)
    hueco = 640 / n
    R = 46
    p = []
    for i, x in enumerate(datos):
        cx = hueco * (i + 0.5)
        cy = 112
        p.append(f'<circle cx="{cx:.0f}" cy="{cy}" r="{R}" fill="none" '
                 f'stroke="var(--linea-fuerte)" stroke-width="6" opacity=".34"/>')
        # El anillo SOLO se llena si el JSON trae "parte", y "parte" solo se
        # pone cuando hay una escala de verdad detras. Rellenar un anillo con
        # una fraccion inventada para que la tarjeta quede bonita es dibujar
        # una cantidad que nadie ha medido: las que no la tienen se quedan con
        # el aro como marco y la cifra hace todo el trabajo.
        if x.get("parte") is not None:
            frac = max(0.0, min(1.0, float(x["parte"])))
            p.append(f'<path d="{_arco(cx, cy, R, 135, 135 + 270 * frac)}" fill="none" '
                     f'stroke="var(--senal)" stroke-width="6" stroke-linecap="round" '
                     f'opacity=".92"/>')
        else:
            p.append(f'<circle cx="{cx:.0f}" cy="{cy - R}" r="4" '
                     f'fill="var(--senal-viva)"/>')
        p.append(f'<text x="{cx:.0f}" y="{cy + 9}" class="g-num" text-anchor="middle">'
                 f'{_num(x)}</text>')
        p.append(f'<text x="{cx:.0f}" y="{cy - R - 18}" class="g-rotulo" '
                 f'text-anchor="middle">{e(x["clave"])}</text>')
        for j, linea in enumerate(lineas(x.get("pie", ""))):
            p.append(f'<text x="{cx:.0f}" y="{cy + R + 30 + j * LINEA_PIE}" '
                     f'class="g-pie" text-anchor="middle">{e(linea)}</text>')
        cabe(x["clave"], hueco - 8, LETRA_ROT, " sobre un anillo")
        cabe(x.get("pie", ""), hueco - 8, donde=" bajo un anillo")
    filas = max(len(lineas(x.get("pie", ""))) for x in datos)
    return _svg("".join(p), 112 + R + 30 + filas * LINEA_PIE + 10)


def g_cockpit(datos):
    """H2 como panel de sistemas: cuatro testigos y un indicador maestro.

    Los testigos se encienden en orden al entrar en pantalla. La animacion es
    CSS con un retardo por fila en --i, y el estado FINAL es el estado por
    defecto: si no hay JS, si el navegador no anima o si el visitante pide
    menos movimiento, el panel se ve entero y encendido desde el primer
    fotograma. Animar es anadir, nunca esconder.
    """
    d = datos[0] if isinstance(datos, list) else datos
    puertas = d["puertas"]
    FILA = 74
    p = []
    for i, g in enumerate(puertas):
        y = 22 + i * FILA
        ok = bool(g.get("si"))
        color = "var(--ok)" if ok else "var(--mal)"
        p.append(f'<g class="ck-fila" style="--i:{i}">')
        p.append(f'<rect x="{IZQ - 34}" y="{y}" width="{DER - IZQ + 68}" height="{FILA - 14}" '
                 f'rx="9" fill="var(--linea-fuerte)" opacity=".16"/>')
        p.append(f'<circle cx="{IZQ - 6}" cy="{y + 30}" r="15" fill="none" '
                 f'stroke="{color}" stroke-width="2"/>')
        if ok:
            p.append(f'<path d="M {IZQ - 14} {y + 30} l 6 6 l 11 -13" fill="none" '
                     f'stroke="{color}" stroke-width="2.6" stroke-linecap="round"/>')
        else:
            p.append(f'<path d="M {IZQ - 13} {y + 23} l 14 14 m 0 -14 l -14 14" '
                     f'fill="none" stroke="{color}" stroke-width="2.6" '
                     f'stroke-linecap="round"/>')
        p.append(f'<text x="{IZQ + 22}" y="{y + 24}" class="g-rotulo">{e(g["clave"])}</text>')
        p.append(f'<text x="{IZQ + 22}" y="{y + 24 + LINEA_PIE}" class="g-pie">'
                 f'{e(g.get("pie", ""))}</text>')
        p.append(f'<text x="{DER + 24}" y="{y + 36}" class="g-rotulo" text-anchor="end">'
                 f'{e("CUMPLE" if ok else "FALLA")}</text>')
        p.append("</g>")
        cabe(g["clave"], 330, LETRA_ROT, " en un testigo")
        cabe(g.get("pie", ""), 330, donde=" bajo un testigo")

    y = 22 + len(puertas) * FILA + 14
    p.append(f'<g class="ck-maestro" style="--i:{len(puertas)}">')
    # El alto del cajon se CALCULA: «NO-GO» va en .g-num, que mide 24 px y con
    # la letra de movil ocupa casi 50 unidades de viewBox. Con el alto escrito
    # a mano (86) el pie se le montaba encima, y la comprobacion de textos
    # pegados lo cazo con -109 unidades de hueco.
    lin = lineas(d.get("pie", ""))
    alto_m = 96 + LINEA_PIE * len(lin) + 14
    p.append(f'<rect x="{IZQ + 60}" y="{y}" width="{DER - IZQ - 120}" height="{alto_m}" '
             f'rx="12" fill="var(--mal)" opacity=".14"/>')
    p.append(f'<rect x="{IZQ + 60}" y="{y}" width="{DER - IZQ - 120}" height="{alto_m}" '
             f'rx="12" fill="none" stroke="var(--mal)" stroke-width="1.6" opacity=".7"/>')
    p.append(f'<text x="320" y="{y + 58}" class="g-num" text-anchor="middle">'
             f'{e(d.get("maestro", "NO-GO"))}</text>')
    for j, linea in enumerate(lin):
        p.append(f'<text x="320" y="{y + 96 + j * LINEA_PIE}" class="g-pie" '
                 f'text-anchor="middle">{e(linea)}</text>')
    p.append("</g>")
    cabe(d.get("pie", ""), DER - IZQ - 130, donde=" bajo el indicador maestro")
    return _svg("".join(p), y + alto_m + 18)


def g_canales(datos):
    """Reward diagnostic: tres canales de senal sobre la MISMA escala.

    Tres pistas apiladas, una por configuracion, con los tres hitos en la
    misma posicion horizontal. Comparten eje vertical a proposito: si cada
    pista se escalara a su propio maximo, tres curvas de aspecto identico
    dirian cosas distintas, que es la forma mas facil de mentir con una
    grafica sin tocar un solo numero.
    """
    HITOS = datos[0]["hitos"] if isinstance(datos, list) else datos["hitos"]
    canales = datos[0]["canales"] if isinstance(datos, list) else datos["canales"]
    tope = max(float(v) for c in canales for v in c["valores"]) * 1.18
    ALTA, PASO = 88, 118
    p = []
    # El primer hito arranca en +130 y no en +70: el rotulo del canal («D_C»)
    # ocupa la izquierda, y con 70 la cifra del primer punto le quedaba a tres
    # unidades, que en pantalla se lee «D_C56,5».
    ini, fin = IZQ + 130, DER - 30
    xs = [ini + i * ((fin - ini) / (len(HITOS) - 1)) for i in range(len(HITOS))]

    for ci, c in enumerate(canales):
        y0 = 34 + ci * PASO
        p.append(f'<rect x="{IZQ - 34}" y="{y0 - 6}" width="{DER - IZQ + 68}" '
                 f'height="{ALTA + 12}" rx="9" fill="var(--linea-fuerte)" opacity=".13"/>')
        p.append(f'<text x="{IZQ - 22}" y="{y0 + 18}" class="g-rotulo">{e(c["clave"])}</text>')
        pts = []
        for i, v in enumerate(c["valores"]):
            yy = y0 + ALTA - (float(v) / tope) * (ALTA - 16)
            pts.append((xs[i], yy))
        p.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
                 '" fill="none" stroke="var(--senal)" stroke-width="2.2" opacity=".85"/>')
        for i, (x, y) in enumerate(pts):
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6" fill="var(--senal-viva)"/>')
            p.append(f'<text x="{x:.1f}" y="{y - 13:.1f}" class="g-pie" '
                     f'text-anchor="middle">{_num(c["valores"][i])}</text>')
        cabe(c["clave"], 150, LETRA_ROT, " en un canal")

    yb = 34 + len(canales) * PASO
    for i, h in enumerate(HITOS):
        p.append(f'<text x="{xs[i]:.1f}" y="{yb}" class="g-pie" text-anchor="middle">'
                 f'{e(h)}</text>')
    return _svg("".join(p), yb + 18)


def g_falsacion(datos):
    """La hipotesis que se cayo, como una serie de medidores que colapsan.

    Cinco anillos de izquierda a derecha, cada uno con su fraccion. Los dos
    ultimos son las configuraciones que la prediccion decia que subirian.
    No hay flecha de causa entre ellos: es una comparacion, no un proceso.
    """
    d = datos[0] if isinstance(datos, list) else datos
    items = d["items"]
    n = len(items)
    hueco = 640 / n
    R = min(40, hueco / 2 - 10)
    tope = max(float(x["valor"]) for x in items)
    p = []
    for i, x in enumerate(items):
        cx, cy = hueco * (i + 0.5), 76
        frac = float(x["valor"]) / tope
        marca = bool(x.get("marcada"))
        p.append(f'<circle cx="{cx:.0f}" cy="{cy}" r="{R}" fill="none" '
                 f'stroke="var(--linea-fuerte)" stroke-width="5" opacity=".3"/>')
        p.append(f'<path d="{_arco(cx, cy, R, 135, 135 + 270 * frac)}" fill="none" '
                 f'stroke="{"var(--mal)" if marca else "var(--senal)"}" stroke-width="5" '
                 f'stroke-linecap="round" opacity="{".95" if marca else ".7"}"/>')
        p.append(f'<text x="{cx:.0f}" y="{cy + 8}" class="g-num" text-anchor="middle">'
                 f'{_num(x)}</text>')
        for j, linea in enumerate(lineas(x["etiqueta"])):
            p.append(f'<text x="{cx:.0f}" y="{cy + R + 26 + j * LINEA_PIE}" '
                     f'class="g-pie" text-anchor="middle">{e(linea)}</text>')
        cabe(x["etiqueta"], hueco - 6, donde=" bajo un medidor")
    filas = max(len(lineas(x["etiqueta"])) for x in items)
    # +50 y no +16: debajo va el titular en .g-num, cuya caja sube casi 50
    # unidades sobre la linea base y se comia el ultimo rotulo de los aros.
    y = 76 + R + 26 + filas * LINEA_PIE + 50
    # El titular tambien se parte con «|»: es la frase mas larga del grafico
    # y en una sola linea no cabe con la letra de movil.
    tit = lineas(d["titular"])
    for j, linea in enumerate(tit):
        p.append(f'<text x="320" y="{y + j * LINEA_NUM}" class="g-num" '
                 f'text-anchor="middle">{e(linea)}</text>')
    p.append(f'<text x="320" y="{y + (len(tit) - 1) * LINEA_NUM + 62}" '
             f'class="g-pie" text-anchor="middle">{e(d["pie"])}</text>')
    cabe(d["titular"], DER - IZQ, LETRA_ROT, " en el titular de la falsacion")
    cabe(d["pie"], DER - IZQ, donde=" bajo la falsacion")
    return _svg("".join(p), y + (len(tit) - 1) * LINEA_NUM + 84)


def g_pool(datos):
    """El ciclo del opponent pool, dibujado para entenderse sin leer.

    Politica actual -> snapshot -> pool historico -> se sortea un rival ->
    rival congelado contra aprendiz -> episodio -> actualizacion -> y vuelta.

    TODO EL DIBUJO ES ESTATICO Y COMPLETO. La animacion son cuatro puntos que
    recorren las flechas y un aro que marca el rival elegido, y vive entera en
    ui/trabajo.css dentro de una consulta de movimiento. Sin JavaScript, con
    prefers-reduced-motion o si el navegador no anima, se ve exactamente el
    mismo esquema con todo en su sitio: aqui animar solo ANADE.
    """
    d = datos[0] if isinstance(datos, list) else datos
    nodos = d.get("nodos", ["C0", "t−4", "t−3", "t−2", "t−1"])
    elegido = int(d.get("elegido", 3))
    p = []

    def caja(x, y, w, h, rotulo, fuerte=False):
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" '
                 f'fill="{"var(--senal-tenue)" if fuerte else "none"}" '
                 f'stroke="{"var(--senal)" if fuerte else "var(--linea-fuerte)"}" '
                 f'stroke-width="1.6"/>')
        trozos = lineas(rotulo)
        base = y + h / 2 + 6 - (LINEA_ROT // 2) * (len(trozos) - 1)
        for j, l in enumerate(trozos):
            p.append(f'<text x="{x + w / 2:.0f}" y="{base + j * LINEA_ROT:.0f}" '
                     f'class="g-rotulo" text-anchor="middle">{e(l)}</text>')
        cabe(rotulo, w - 10, LETRA_ROT, " en una caja del pool")

    def flecha(x1, y1, x2, y2):
        p.append(f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" '
                 f'stroke="var(--linea-fuerte)" stroke-width="1.5"/>')
        if y2 > y1:
            p.append(f'<path d="M {x2 - 5} {y2 - 6} l 5 6 l 5 -6" fill="none" '
                     f'stroke="var(--linea-fuerte)" stroke-width="1.5"/>')

    # 1. La politica actual. Las cajas miden 76 y no 52 porque los rotulos
    #    van en DOS lineas: con 52 la segunda linea se sale por debajo del
    #    borde, que es como se veia en la primera version.
    caja(220, 12, 200, 76, "POLÍTICA|ACTUAL", fuerte=True)
    flecha(320, 88, 320, 124)
    p.append('<text x="332" y="112" class="g-pie">snapshot</text>')

    # 2. El pool
    p.append('<rect x="56" y="128" width="528" height="106" rx="11" '
             'fill="var(--linea-fuerte)" opacity=".13"/>')
    p.append('<text x="70" y="150" class="g-pie">POOL HISTÓRICO</text>')
    xs = [110 + i * 92 for i in range(len(nodos))]
    for i, (x, n) in enumerate(zip(xs, nodos)):
        marca = i == elegido
        p.append(f'<circle class="pool-nodo" style="--i:{i}" cx="{x}" cy="{190}" r="15" '
                 f'fill="{"var(--senal)" if marca else "none"}" '
                 f'fill-opacity="{".9" if marca else "0"}" '
                 f'stroke="var(--senal)" stroke-width="1.6" '
                 f'opacity="{"1" if marca else ".55"}"/>')
        p.append(f'<text x="{x}" y="{224}" class="g-pie" text-anchor="middle">{e(n)}</text>')
    p.append(f'<circle class="pool-elegido" cx="{xs[elegido]}" cy="190" r="23" fill="none" '
             f'stroke="var(--senal-viva)" stroke-width="1.6" opacity=".85"/>')

    flecha(320, 234, 320, 272)
    p.append('<text x="332" y="258" class="g-pie">se sortea</text>')

    # 3. El duelo
    caja(40, 276, 240, 76, "RIVAL|CONGELADO")
    caja(360, 276, 240, 76, "APRENDIZ", fuerte=True)
    p.append('<path d="M 284 314 L 356 314 M 290 309 l -6 5 l 6 5 '
             'M 350 309 l 6 5 l -6 5" fill="none" stroke="var(--senal)" '
             'stroke-width="1.5"/>')
    p.append('<text x="320" y="378" class="g-pie" text-anchor="middle">'
             'episodio 1v1</text>')

    # 4. La vuelta: sale del aprendiz, rodea por la izquierda y vuelve arriba.
    p.append('<path class="pool-vuelta" d="M 480 352 L 480 398 L 20 398 L 20 50 L 216 50" '
             'fill="none" stroke="var(--senal)" stroke-width="1.5" opacity=".55" '
             'stroke-dasharray="5 5"/>')
    p.append('<path d="M 210 45 l 6 5 l -6 5" fill="none" stroke="var(--senal)" '
             'stroke-width="1.5" opacity=".55"/>')
    p.append('<text x="250" y="416" class="g-pie">actualización</text>')

    # 5. Los cuatro puntos que viajan. Sin animacion se quedan quietos en el
    #    principio de su tramo, que es un estado legible y no un error.
    for i, (x, y) in enumerate(((320, 94), (320, 240), (300, 314), (470, 358))):
        p.append(f'<circle class="pool-pulso pool-pulso--{i + 1}" cx="{x}" cy="{y}" '
                 f'r="3.4" fill="var(--senal-viva)"/>')

    cabe("episodio 1v1", 300, donde=" bajo el duelo")
    return _svg("".join(p), 436)


def g_arquitectura(datos):
    """Tres zonas: lo heredado, lo mio y lo que salio. En ese orden.

    Es la pieza que contesta de un vistazo a «cuanto de esto has hecho tu».
    Cada zona lleva su distintivo y su color: lo heredado va en gris, mi
    aportacion en el color del caso y los resultados en blanco.

    Al pasar el raton por una zona, las otras dos bajan de intensidad. Eso es
    CSS puro sobre el SVG, no hay JavaScript detras, y el dibujo entero se lee
    igual sin pasar el raton por ningun sitio: el realce es una ayuda, no la
    forma de acceder a la informacion. El SVG va aria-hidden, asi que no se
    le pone tabindex: quien no lo ve recibe el parrafo que lo describe.
    """
    d = datos[0] if isinstance(datos, list) else datos
    zonas = d["zonas"]
    ANCHO, COLS, PASO = DER - IZQ + 68, 2, 40
    p = []
    y = 12
    for zi, z in enumerate(zonas):
        filas = (len(z["items"]) + COLS - 1) // COLS
        alto = 76 + filas * PASO + 14
        color = z.get("color", "senal")
        trazo = {"senal": "var(--senal)", "gris": "var(--linea-fuerte)",
                 "blanco": "#FFFFFF"}[color]
        p.append(f'<g class="arq-zona">')
        p.append(f'<rect x="{IZQ - 34}" y="{y}" width="{ANCHO}" height="{alto}" rx="11" '
                 f'fill="var(--linea-fuerte)" opacity=".12"/>')
        # El filete de la izquierda es lo que distingue una zona de otra de un
        # vistazo, antes incluso de leer el distintivo.
        p.append(f'<rect x="{IZQ - 34}" y="{y}" width="4" height="{alto}" rx="2" '
                 f'fill="{trazo}" opacity=".8"/>')
        p.append(f'<text x="{IZQ - 18}" y="{y + 28}" class="g-rotulo">{e(z["distintivo"])}</text>')
        for i, it in enumerate(z["items"]):
            col, fila = i % COLS, i // COLS
            tx = IZQ - 14 + col * ((ANCHO - 40) / COLS)
            ty = y + 76 + fila * PASO
            p.append(f'<circle cx="{tx + 4:.0f}" cy="{ty - 5}" r="3" fill="{trazo}" '
                     f'opacity=".75"/>')
            p.append(f'<text x="{tx + 18:.0f}" y="{ty}" class="g-pie">{e(it)}</text>')
            cabe(it, (ANCHO - 40) / COLS - 26, donde=" en la arquitectura")
        p.append("</g>")
        y += alto + 16
        cabe(z["distintivo"], ANCHO - 40, LETRA_ROT, " como distintivo")
    return _svg("".join(p), y)



def g_correcciones(datos):
    """Una lista de rectificaciones, en vertical.

    VERTICAL Y NO HORIZONTAL, y es una decision, no una limitacion. Siete
    paradas repartidas a lo ancho de un lienzo de 640 dejan noventa unidades
    por parada: con la letra de movil eso son cinco caracteres. En vertical
    cada rectificacion tiene la anchura entera para su nombre y se lee igual
    a 390 que a 1440, que es justo lo que se le pide a esto.

    Arriba, las tres fases por las que pasa cada una. No se repiten en cada
    fila porque son siempre las mismas: enunciarlas una vez es la forma de que
    la seccion no ocupe mil pixeles.
    """
    d = datos[0] if isinstance(datos, list) else datos
    fases = d.get("fases", ["Supuesto", "Prueba", "Correcci\u00f3n"])
    hitos = d["hitos"]
    p = []

    # Las tres fases, en fila, como cabecera.
    x = IZQ - 30
    for i, f in enumerate(fases):
        ancho = len(f) * LETRA_ROT + 26
        p.append(f'<rect x="{x:.0f}" y="14" width="{ancho:.0f}" height="34" rx="17" '
                 f'fill="none" stroke="var(--linea-fuerte)" stroke-width="1.3"/>')
        p.append(f'<text x="{x + ancho / 2:.0f}" y="37" class="g-rotulo" '
                 f'text-anchor="middle">{e(f)}</text>')
        x += ancho + 8
        if i < len(fases) - 1:
            p.append(f'<path d="M {x - 4:.0f} 31 l 10 0 m -4 -4 l 4 4 l -4 4" fill="none" '
                     f'stroke="var(--senal)" stroke-width="1.4"/>')
            x += 16
    cabe(" ".join(fases), DER - IZQ + 60, LETRA_ROT, " en las fases")

    # El rail y las paradas.
    # El paso sale del rotulo mas alto, no de un numero escrito a mano: con
    # 54 fijo, una parada de dos lineas se comia la siguiente.
    FILA = max(54, LINEA_ROT * max(len(lineas(h)) for h in hitos) + 16)
    Y0 = 92
    # El rail deja sitio a su izquierda para el numero de la parada: con
    # RX = IZQ - 14 el «01» empezaba en -5 y el lienzo se lo comia.
    RX = IZQ + 8
    p.append(f'<line x1="{RX}" y1="{Y0 - 14}" x2="{RX}" y2="{Y0 + (len(hitos) - 1) * FILA + 14}" '
             f'stroke="var(--linea-fuerte)" stroke-width="1.4" opacity=".6"/>')
    for i, h in enumerate(hitos):
        y = Y0 + i * FILA
        p.append(f'<circle cx="{RX}" cy="{y}" r="7" fill="var(--fondo)" '
                 f'stroke="var(--senal)" stroke-width="1.8"/>')
        p.append(f'<text x="{RX - 20}" y="{y + 6}" class="g-pie" text-anchor="end">'
                 f'{i + 1:02d}</text>')
        trozos = lineas(h)
        base = y + 6 - (LINEA_ROT // 2) * (len(trozos) - 1)
        for j, l in enumerate(trozos):
            p.append(f'<text x="{RX + 22}" y="{base + j * LINEA_ROT}" class="g-rotulo">'
                     f'{e(l)}</text>')
        cabe(h, DER - RX - 30, LETRA_ROT, " en una correccion")
    return _svg("".join(p), Y0 + (len(hitos) - 1) * FILA + 40)


GRAFICOS = {
    # --- piezas de cabina, estrenadas en el caso de self-play ---------
    "pool": g_pool,
    "correcciones": g_correcciones,
    "arquitectura": g_arquitectura,
    "dial": g_dial,
    "telemetria": g_telemetria,
    "cockpit": g_cockpit,
    "canales": g_canales,
    "falsacion": g_falsacion,
    "escalones": g_escalones, "medidores": g_medidores, "comparacion": g_comparacion,
    "barras": g_barras, "veredictos": g_veredictos, "resto": g_resto, "flujo": g_flujo,
    "escalas": g_escalas,
    "secuencia": g_secuencia,
    "tira": g_tira,
    "hud": g_hud,
    "botella": g_botella,
    "pista": g_pista,
    "ascensor": g_ascensor,
    "matriz": g_matriz,
    "pantalla": g_pantalla,
    "recorrido": g_recorrido,
    "nodos": g_nodos,
}


# Las composiciones que entiende el CSS. Están aquí y no solo en la hoja de
# estilo para que un nombre mal escrito en un JSON salte al generar la página
# y no se quede en un apartado que se pinta raro y nadie mira.
#
#   dividido   texto a la izquierda, figura a la derecha  (el de siempre)
#   invertido  figura a la izquierda, texto a la derecha
#   ancho      una sola columna: se lee y debajo la figura a todo lo ancho
#   centrado   columna estrecha centrada, figura centrada y más pequeña
#   editorial  texto ancho y figura estrecha al lado
COMPOSICIONES = ("dividido", "invertido", "ancho", "centrado", "editorial")


# --------------------------------------------------------------- piezas

def ledger(filas):
    if not filas:
        return ""
    p = []
    for f in filas:
        clase = "lectura lectura--destacada" if f.get("destacada") else "lectura"
        p.append(f'<div class="{clase}"><span class="lectura__clave">{e(f["clave"])}</span>'
                 f'<span class="lectura__valor">{e(f["valor"])}</span></div>')
    return '<div class="lecturas">' + "".join(p) + "</div>"


def seccion(s):
    g = s["grafico"]
    if g["tipo"] not in GRAFICOS:
        raise SystemExit(f'El apartado "{s["id"]}" pide el gráfico "{g["tipo"]}", '
                         f'que no existe. Los que hay: ' + ", ".join(sorted(GRAFICOS)))
    dibujo = GRAFICOS[g["tipo"]](g["datos"])
    parrafos = "".join(f'<p class="parrafo">{e(t)}</p>' for t in s.get("parrafos", []))
    # La composición del apartado. Por defecto "dividido", que es lo que
    # había: texto a la izquierda y figura a la derecha. Las demás las pone
    # el CSS moviendo la rejilla; el HTML sale igual en todas, y sale en el
    # orden en que se lee. Un apartado que pida una que no existe es un
    # error del JSON y se dice al generar, no en la web.
    comp = s.get("composicion", "dividido")
    if comp not in COMPOSICIONES:
        raise SystemExit(f'El apartado "{s["id"]}" pide la composición '
                         f'"{comp}", que no existe. Las que hay: '
                         + ", ".join(sorted(COMPOSICIONES)))
    return f"""
  <section class="caso" id="{e(s['id'])}" data-caso="{e(s['etiqueta'])}">
    <div class="marco">
      <div class="caso__reparto caso__reparto--{comp}">
        <div class="caso__texto" data-revelar>
          <p class="rotulo eyebrow">{e(s['eyebrow'])}</p>
          {titular(s, "titulo-menor")}
          <p class="parrafo parrafo--lead">{e(s['lead'])}</p>
          {parrafos}
          {ledger(s.get("ledger", []))}
        </div>
        <figure class="caso__figura" data-revelar>
          {dibujo}
          <figcaption class="caso__pie">{e(s['figcaption'])}</figcaption>
          <p class="oculto">{e(s['sr'])}</p>
        </figure>
      </div>
    </div>
  </section>"""



def corte(c):
    """Un CORTE: una banda de video entre dos apartados.

    Que es y que NO es. Es contexto visual: imagenes del juego sobre el que
    corre el experimento, puestas para dar respiro entre dos bloques densos.
    NO es material del experimento, y por eso lleva su nota escrita encima y
    va deliberadamente tratada —velo, rejilla, poco brillo— para que se lea
    como ambiente y no como una grabacion que demuestre algo.

    Lo que se sirve de entrada es el POSTER. El <video> nace sin src: lo pone
    plantilla.js cuando el corte entra en pantalla, y lo pausa cuando sale.
    Sin JavaScript, con el movimiento parado o con prefers-reduced-motion no
    se pide nunca el archivo y lo que queda es la imagen fija con su rotulo,
    que sigue contando lo mismo.

    No lleva id ni entra en el rail: es una transicion, no un apartado.
    """
    v = c["video"]
    etiquetas = "".join(
        f'<span class="corte__etiqueta">{e(x)}</span>' for x in c.get("etiquetas", []))
    titular = (f'<p class="corte__titular">{e(c["titular"])}</p>'
               if c.get("titular") else "")
    return f"""
  <div class="corte" data-revelar>
    <div class="marco">
      <figure class="corte__figura">
      <div class="corte__caja">
        <img class="corte__quieta" src="{ruta(v['poster'])}" width="1440" height="810"
             alt="" decoding="async" loading="lazy">
        <video class="corte__video" data-video-ambiental muted loop playsinline
               preload="none" poster="{ruta(v['poster'])}"
               data-src="{ruta(v['src'])}" aria-hidden="true"></video>
        <span class="corte__velo" aria-hidden="true"></span>
        <span class="corte__rejilla" aria-hidden="true"></span>
        <div class="corte__hud" aria-hidden="true">{etiquetas}</div>
        {titular}
      </div>
      <!-- La nota va FUERA de la caja: dentro quedaba tapada por el video y
           recortada por el overflow, y una nota de procedencia que no se ve no
           sirve de nada. -->
      <figcaption class="corte__nota">{e(c['nota'])}</figcaption>
      </figure>
    </div>
  </div>"""


def visor(inf):
    """El documento del trabajo, leible dentro de la propia pagina.

    La arquitectura viene del bloque .pd-embed de la web de referencia, y su
    idea buena es LA FACHADA: lo que se pinta de entrada no es el PDF, es la
    portada rasterizada de su primera pagina. El documento —aqui 8,5 MB— no
    se pide hasta que alguien lo pulsa. Sin eso hay que elegir entre
    descargarle el archivo entero a todo el que pase por la pagina o
    ensenarle un rectangulo gris, y las dos opciones son malas.

    Al pulsar, plantilla.js cambia la fachada por un <iframe> con el PDF, en
    el mismo sitio y con la misma altura. En pantallas estrechas no: ahi el
    visor embebido del navegador es incomodo, asi que el enlace hace lo que
    dice y abre el PDF en otra pestana. Es un <a> con href de verdad, asi que
    tambien funciona con el JavaScript bloqueado y con el teclado.

    Las paginas y el peso NO se escriben a mano: los pone
    herramientas/hacer-informe.py leyendo el archivo, y hay una prueba que
    compara lo que dice la pagina con el PDF real.
    """
    if not inf:
        return ""
    meta = " · ".join(filter(None, [
        e(inf.get("tipo", "PDF")),
        f'{inf["paginas"]} páginas' if inf.get("paginas") else "",
        e(inf.get("peso", "")),
    ]))
    return f"""
        <figure class="visor" data-revelar>
          <figcaption class="visor__barra visor__barra--alta">
            <span class="visor__rotulo">{e(inf['titulo'])}</span>
            <span class="visor__meta">{meta}</span>
          </figcaption>

          <div class="visor__lienzo">
            <a class="visor__fachada" href="{ruta(inf['archivo'])}"
               target="_blank" rel="noopener noreferrer"
               data-visor="{e(inf['titulo'])}, {inf.get('paginas', 0)} páginas">
              <img class="visor__portada" src="{ruta(inf['portada'])}"
                   width="{inf.get('ancho', 1000)}" height="{inf.get('alto', 1415)}"
                   loading="lazy" decoding="async"
                   alt="{e(inf['alt'])}">
              <span class="visor__cta">{e(inf['cta'])}
                <span class="visor__peso">{e(inf.get('peso', ''))}</span>
                <span class="oculto" data-visor-nota>, se abre en otra pestaña</span>
              </span>
            </a>
          </div>

          <div class="visor__barra visor__barra--baja">
            <a class="visor__accion" href="{ruta(inf['archivo'])}"
               download="{e(inf['descarga'])}">
              <span class="visor__icono" aria-hidden="true">&#8595;</span>{e(inf['descargar'])}
              <span class="visor__peso">{e(inf.get('peso', ''))}</span>
            </a>
            <a class="visor__accion visor__accion--fin" href="{ruta(inf['archivo'])}"
               target="_blank" rel="noopener noreferrer">
              {e(inf['ampliar'])} <span class="flecha" aria-hidden="true">↗</span>
              <span class="oculto">, se abre en otra pestaña</span>
            </a>
          </div>
        </figure>"""


def portada(d):
    """La portada del caso. Dos formas, según lo que pida el JSON.

    "simple" es texto sobre el fondo de datos de siempre. "animada" añade un
    lienzo propio detrás y monta el texto sobre un panel de cristal, que es
    lo que hacía la referencia con un vídeo en bucle. Aquí no hay vídeo: un
    MP4 de fondo son megabytes que se descargan siempre, no se puede parar
    con el botón de movimiento y no dice nada del proyecto. El lienzo pesa
    tres kilobytes, dibuja algo que SÍ habla del trabajo y obedece al mismo
    interruptor que todo lo demás.
    """
    h = d["hero"]
    animada = h.get("tipo") == "animada"
    datos = "".join(f'<div class="dato"><span class="dato__k">{e(x["k"])}</span>'
                    f'<span class="dato__v">{e(x["v"])}</span></div>'
                    for x in h["datos"])
    cifras = "".join(f'<div class="cifra"><span class="cifra__n">{e(x["valor"])}</span>'
                     f'<span class="cifra__pie">{e(x["pie"])}</span></div>'
                     for x in h["cifras"])

    # Una linea pequena bajo la portada para decir DE DONDE sale el metraje.
    # Es opcional: sin la clave en el JSON no se pinta nada y las cinco
    # portadas animadas que ya existen no cambian ni un pixel. Existe porque
    # un video de contexto que no dice que es de contexto se lee como
    # material del propio trabajo, y eso seria mentir por omision.
    # El salto de linea va DENTRO del valor, no en la plantilla: si estuviera
    # en la plantilla, un caso sin nota dejaria una linea en blanco suelta en
    # su HTML, y eso sale en el diff de las otras seis paginas sin significar
    # nada. Sin nota, salida identica byte a byte a la de antes.
    nota_video = ("\n      "
                  f'<p class="portada__nota">{e(h["nota_video"])}</p>'
                  if h.get("nota_video") else "")

    lienzo = ""
    panel_abre, panel_cierra = "", ""
    if animada:
        v = h["video"]
        # autoplay lo enciende plantilla.js, no el atributo: asi el video
        # obedece al mismo boton que todo lo demas. muted y playsinline SI
        # van aqui —sin muted el navegador bloquea la reproduccion, y sin
        # playsinline iOS lo abre a pantalla completa encima de la pagina—.
        #
        # preload="none" y el poster delante: el archivo no se pide hasta que
        # hace falta. Con el movimiento parado o con prefers-reduced-motion no
        # se descarga NUNCA, y lo que se ve es el poster: 128 KB en vez de un
        # mega. La imagen de respaldo va debajo por si el video no llega.
        lienzo = (f'<div class="relieve" aria-hidden="true">'
                  f'<img class="relieve__quieta" src="{ruta(v["poster"])}"'
                  f' width="1440" height="810" alt="" decoding="async">'
                  # data-video-ambiental: lo que gobierna plantilla.js. Y
                  # data-arranca-visible porque la portada YA se ve al cargar;
                  # los cortes de mas abajo no lo llevan y por eso no piden su
                  # archivo hasta que alguien baja hasta ellos.
                  f'<video id="portada-video" data-video-ambiental data-arranca-visible'
                  f' muted loop playsinline preload="none"'
                  f' poster="{ruta(v["poster"])}" data-src="{ruta(v["src"])}"></video>'
                  f'<span class="relieve__velo"></span></div>')
        # El panel de cristal: una cara translúcida y cuatro filos que recogen
        # la luz. Es lo que hace legible un texto sobre algo que se mueve.
        panel_abre = ('<div class="cristal">'
                      '<span class="cristal__fx" aria-hidden="true">'
                      '<span class="cristal__cara"></span>'
                      '<span class="cristal__filo cristal__filo--t"></span>'
                      '<span class="cristal__filo cristal__filo--b"></span>'
                      '<span class="cristal__filo cristal__filo--i"></span>'
                      '<span class="cristal__filo cristal__filo--d"></span></span>'
                      '<div class="cristal__dentro">')
        panel_cierra = "</div></div>"

    return f"""
  <section class="caso-portada{' caso-portada--animada' if animada else ''}">{lienzo}
    <div class="marco">
      <a class="volver" href="{e(d['volver']['href'])}">
        <span aria-hidden="true">&larr;</span> {e(d['volver']['texto'])}
      </a>
      {panel_abre}
      <div class="caso-portada__panel" data-revelar>
        <p class="rotulo eyebrow">{e(h['categoria'])}</p>
        <h1 class="caso-portada__titulo" data-partir>{e(h['titulo'])}</h1>
        <p class="parrafo parrafo--lead">{e(h['sub'])}</p>
        <div class="datos">{datos}</div>
      </div>
      {panel_cierra}{nota_video}
      <div class="cifras" data-revelar>{cifras}</div>
    </div>
  </section>"""


def hacer(nombre_json, nombre_salida):
    datos_f = RAIZ / nombre_json
    salida = RAIZ / "trabajos" / nombre_salida
    d = json.loads(datos_f.read_text(encoding="utf-8"))
    m, h, c = d["meta"], d["hero"], d["cierre"]

    rail = "".join(f'<a href="#{e(r["ancla"])}" data-rail>{e(r["texto"])}</a>'
                   for r in d["rail"])
    nav = "".join(f'<li><a href="#{e(r["ancla"])}" data-nav>{e(r["texto"])}</a></li>'
                  for r in d["rail"])
    # Los cortes viven en su propia lista y declaran delante de que apartado
    # van. No entran en d["secciones"] a proposito: ahi cambiarian la cuenta
    # de apartados, la del rail y la de figuras, que son invariantes que las
    # pruebas vigilan y que un separador decorativo no tiene por que tocar.
    # ct y no c: en esta funcion «c» ya es el bloque de cierre del caso, y
    # reutilizar el nombre lo pisaba.
    cortes = {}
    for ct in d.get("cortes", []):
        cortes.setdefault(ct["antes"], []).append(ct)
    ids = {s["id"] for s in d["secciones"]}
    for clave in cortes:
        if clave not in ids:
            raise SystemExit(f'Un corte dice ir antes de "{clave}", que no es '
                             f'ningun apartado de este caso.')
    secciones = "".join(
        "".join(corte(ct) for ct in cortes.get(s["id"], [])) + seccion(s)
        for s in d["secciones"])
    cierre_p = "".join(f'<p class="parrafo">{e(t)}</p>' for t in c["parrafos"])
    # PENDIENTE es la convencion del proyecto: mientras un enlace valga eso,
    # NO se pinta y el generador avisa al terminar. Un boton que lleva a un
    # repositorio que todavia no existe, delante de un reclutador, es peor
    # que no tener boton. La estructura queda lista: se pone la URL en el
    # JSON, se vuelve a ejecutar esto y aparece.
    vivos = [b for b in c["botones"] if b["href"] != "PENDIENTE"]
    pendientes = [b["texto"] for b in c["botones"] if b["href"] == "PENDIENTE"]
    botones = "".join(
        f'<a class="boton {"boton--solido" if i == 0 else ""}" href="{e(b["href"])}"'
        f'{" target=\"_blank\" rel=\"noopener noreferrer\"" if b.get("nueva_pestana") else ""}>'
        f'{e(b["texto"])} {FLECHA}</a>'
        for i, b in enumerate(vivos))
    # El flotante sale de contenido-plantilla.json y no de aquí: es el mismo
    # de todo el sitio, y tenerlo escrito en tres archivos es como acaban
    # diciendo tres cosas distintas.
    fl = json.loads((RAIZ / "contenido-plantilla.json")
                    .read_text(encoding="utf-8"))["flotante"]

    # El color del caso. Todo el CSS de una pagina de trabajo pinta con
    # var(--senal) y sus tres hermanas, asi que la personalidad de un proyecto
    # cabe en cuatro variables: no hay una sola regla duplicada por caso. Sin
    # bloque "paleta" en el JSON se queda el ambar del sitio.
    pal = d.get("paleta") or {}
    estilo_caso = ""
    if pal:
        estilo_caso = (
            "\n<style>\n"
            "  /* Paleta de este trabajo. " + e(pal.get("_porque", "")) + " */\n"
            "  :root{\n"
            f"    --senal:{e(pal['senal'])};\n"
            f"    --senal-viva:{e(pal['senal_viva'])};\n"
            f"    --senal-tenue:{e(pal['senal_tenue'])};\n"
            f"    --senal-linea:{e(pal['senal_linea'])};\n"
            "  }\n"
            "  /* El cursor NO cambia con el caso: es del sitio. Si cambiara,\n"
            "     al pasar de un trabajo a otro pareceria otro puntero. Hay\n"
            "     una prueba que lo compara con el del portfolio. */\n"
            "  .nodo-cursor{ border-color:rgba(224,164,88,.34) }\n"
            "  .nodo-cursor::after{ background:#E0A458 }\n"
            "  .nodo-cursor.esta-activo{ border-color:#E0A458;\n"
            "                            background:rgba(224,164,88,.07) }\n"
            "</style>")

    doc = f"""<!DOCTYPE html>
<html lang="es" data-caso="{e(Path(str(salida)).stem)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- GENERADO por herramientas/hacer-caso.py desde {e(nombre_json)}.
     No lo edites a mano: se sobrescribe entero en cada ejecución. -->
<title>{e(m['titulo_pestana'])}</title>
<meta name="description" content="{e(recortar(m['descripcion']))}">
<meta name="theme-color" content="#0B0C0F">

<link rel="icon" href="../favicon.ico" sizes="32x32">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">

<meta property="og:type" content="article">
<meta property="og:title" content="{e(m['titulo_pestana'])}">
<meta property="og:description" content="{e(recortar(m['descripcion']))}">
<meta property="og:image" content="https://{e(m['dominio'])}/medios/og.jpg">
<meta property="og:image:alt" content="Tarjeta con el nombre de Pedro Pérez Blanco y el titular del portfolio.">
<meta property="og:url" content="https://{e(m['dominio'])}/trabajos/{e(nombre_salida)}">
<link rel="canonical" href="https://{e(m['dominio'])}/trabajos/{e(nombre_salida)}">
<meta name="twitter:card" content="summary_large_image">

<link rel="stylesheet" href="../ui/tipos.css">
<link rel="stylesheet" href="../ui/plantilla.css">
<!-- Después de plantilla.css, porque se apoya en sus tokens y solo añade lo
     que es propio de una página de caso. -->
<link rel="stylesheet" href="../ui/trabajo.css">{estilo_caso}
</head>
<body>

<canvas class="fondo" id="fondo" aria-hidden="true"></canvas>

<a class="saltar" href="#contenido">Saltar al contenido</a>

<header class="barra" id="barra">
  <nav class="barra__caja" aria-label="Secciones">
    <a class="barra__marca" href="../index.html">
      <span class="barra__iniciales" aria-hidden="true">PPB</span>
      <span class="barra__nombre">Pedro Pérez Blanco</span>
    </a>
    <ul class="barra__lista" id="menu-lista">{nav}</ul>
    <button class="barra__pausa" id="reanudar" type="button">
      <span class="barra__pausa__punto" aria-hidden="true"></span>Movimiento en pausa
      <span class="oculto">, pulsa para reanudarlo</span>
    </button>
    <a class="barra__cta" href="{e(d['volver']['href'])}">{e(d['volver']['texto'])}</a>
    <button class="barra__menu" id="menu" type="button"
            aria-expanded="true" aria-controls="menu-lista">
      <span aria-hidden="true"></span>
      <span class="oculto">Abrir el menú</span>
    </button>
  </nav>
  <div class="barra__avance" id="avance" aria-hidden="true"></div>
</header>

<main id="contenido">
{portada(d)}
  <!-- El raíl de apartados. Son anclas de verdad, así que funciona con el
       JavaScript bloqueado; lo único que añade el script es marcar en cuál
       estás. Es un índice, no unas pestañas: el caso entero está en la
       página. -->
  <nav class="rail" id="rail" aria-label="Apartados de este trabajo">
    <div class="marco rail__caja">{rail}</div>
  </nav>
{secciones}

  <section class="caso caso--cierre" id="s-cierre">
    <div class="marco">
      <div class="cierre" data-revelar>
        <p class="rotulo eyebrow">{e(c['eyebrow'])}</p>
        {titular(c, "titulo-menor")}
        {cierre_p}
        <div class="botones">{botones}</div>
      </div>
      {visor(c.get("informe"))}
    </div>
  </section>

  <section class="caso caso--siguiente">
    <div class="marco">
      <a class="siguiente" href="{e(d['siguiente']['href'])}">
        <span class="siguiente__rotulo">{e(d['siguiente']['rotulo'])}</span>
        <span class="siguiente__titulo">{e(d['siguiente']['titulo'])}</span>
        <span class="siguiente__flecha" aria-hidden="true">&rarr;</span>
      </a>
    </div>
  </section>

</main>

<!-- Las dos piezas que faltaban aquí y sí estaban en el portfolio, y por eso
     el ratón no se comportaba igual al abrir un trabajo. El anillo lo dibuja
     plantilla.js, que ya venía cargado; sin este div no tenía dónde. -->
<div class="nodo-cursor" id="nodo-cursor" aria-hidden="true"></div>

<a class="flotante" id="flotante" href="{e(fl['href'])}" aria-label="{e(fl['etiqueta'])}">
  <span class="flotante__texto">
    <b>{e(fl['titulo'])}</b>
    <span>{e(fl['sub'])}</span>
  </span>
  <span class="flotante__icono" aria-hidden="true">&#9993;</span>
</a>

<footer class="pie">
  <div class="marco">
    <div class="pie__reparto">
      <div>
        <p class="pie__nombre">Pedro Pérez Blanco</p>
        <p class="pie__nota">Analista de marketing y datos · Madrid</p>
        <button class="pie__quieto" id="quieto" type="button" aria-pressed="false">
          <span class="pie__punto" aria-hidden="true"></span><span data-texto>Parar movimiento</span>
        </button>
      </div>
      <div class="pie__enlaces">
        <a class="pie__enlace" href="../index.html">Volver al portfolio {FLECHA}</a>
      </div>
    </div>
  </div>
</footer>

<script src="../ui/fondo.js" defer></script>
<script src="../ui/plantilla.js" defer></script>
</body>
</html>
"""

    # La red de seguridad. Se pasa a TODAS las páginas, no solo a la del TFM:
    # cuesta nada, y el día que un dato del CRM se cuele en otra, esta es la
    # única línea que lo va a ver.
    fugas = [que for pat, que in PROHIBIDO if re.search(pat, doc, re.I)]
    if fugas:
        print(f"  ! NO SE ESCRIBE {nombre_salida}. Contiene datos confidenciales:")
        for que in fugas:
            # Se dice QUE se ha colado, nunca el patron: el patron es el dato.
            print(f"      · {que}")
        return False

    salida.write_text(doc, encoding="utf-8")
    print(f"  + trabajos/{salida.name:<26} {salida.stat().st_size / 1024:>4.0f} KB · "
          f"{len(d['secciones'])} apartados, {len(d['rail'])} en el raíl"
          f"{' · portada con vídeo' if h.get('tipo') == 'animada' else ''}")
    for x in pendientes:
        print(f"      · «{x}» no se pinta todavía: ponle la URL en {nombre_json}")
    return True


def main():
    print("Páginas de caso:")
    hechas = sum(1 for j, s in CASOS if hacer(j, s))
    print(f"\n{hechas} de {len(CASOS)} · gráficos SVG dibujados a mano, "
          f"sin una sola dependencia")
    print("Confidencialidad: comprobada en todas.")
    print("\nPara cambiar un texto: su contenido-*.json, y vuelve a ejecutar esto.")
    return 0 if hechas == len(CASOS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
