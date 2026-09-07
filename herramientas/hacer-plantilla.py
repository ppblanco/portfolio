# -*- coding: utf-8 -*-
"""
Genera index.html a partir de contenido-plantilla.json.

El portfolio: misma arquitectura de página que la web que sirvió de referencia
—secciones numeradas, carrusel de trabajos, destrezas por categoría, experiencia
y formación en acordeón, columna de texto y llamada final grande— con la
identidad propia (ámbar sobre casi negro, Barlow Condensed / Barlow / Plex Mono)
y el contenido real de Pedro.

Todo el texto está en contenido-plantilla.json, en listas:

    trabajo.proyectos[]      destrezas.grupos[]
    experiencia.puestos[]    formacion.bloques[]
    redes[]                  nav[]

Cambias ahí y vuelves a ejecutar esto. El HTML se sobrescribe entero.

Se genera HTML estático en lugar de pintarlo con JavaScript en el navegador a
propósito: la página tiene que aguantar aunque el JavaScript falle, y un
portfolio en blanco delante de un reclutador no vale nada.

Uso:  python herramientas/hacer-plantilla.py
"""

import html as _html
import json
import re
from pathlib import Path
from urllib.parse import quote

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "contenido-plantilla.json"
SALIDA = RAIZ / "index.html"

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
    """Escapa: el contenido lo escribe una persona, no un programa."""
    return _html.escape(str(t), quote=True)


def ruta(p):
    """Codifica una ruta de archivo para meterla en un src.

    Los nombres que pone Pedro llevan espacios, acentos y algún punto medio
    ("Creative Advertising · intercambio Erasmus.jpeg"). Sin codificar, el
    navegador corta la URL en el primer espacio y la imagen no carga.
    """
    return e(quote(str(p), safe="/"))


def titular(d, clase):
    """Titular con una palabra en ámbar y cursiva, como en la referencia."""
    partes = [e(d.get("titulo_antes", ""))]
    if d.get("titulo_acento"):
        partes.append(f'<em class="acento">{e(d["titulo_acento"])}</em>')
    if d.get("titulo_despues"):
        partes.append(e(d["titulo_despues"]))
    return f'<h2 class="{clase}">' + " ".join(p for p in partes if p) + "</h2>"


def cabecera(d, clase="titulo-mayor"):
    intro = (f'<p class="parrafo seccion__intro">{e(d["entradilla"])}</p>'
             if d.get("entradilla") else "")
    return f"""
    <div class="seccion__cabecera" data-revelar>
      <p class="rotulo eyebrow">
        <span class="rotulo__n">{e(d['numero'])}</span> · {e(d['rotulo'])}
      </p>
      {titular(d, clase)}
      {intro}
    </div>"""


# ---------------------------------------------------------------- piezas

def enlace(l, clase):
    extra = ' target="_blank" rel="noopener"' if l.get("nueva_pestana") else ""
    aviso = f'<span class="oculto">{e(l["aviso"])}</span>' if l.get("aviso") else ""
    accion = f' data-accion="{e(l["accion"])}"' if l.get("accion") else ""
    return (f'<a class="{clase} {clase}--{e(l.get("tipo", "vivo"))}" '
            f'href="{e(l["href"])}"{accion}{extra}>{e(l["texto"])} {FLECHA}{aviso}</a>')


# Aqui vivia lecturas(), que pintaba las cifras de cada proyecto dentro de su
# ficha. La ficha ya no las lleva: es corta y lo explicado esta en la pagina
# del trabajo. Las cifras SIGUEN en contenido-plantilla.json, en la clave
# "lecturas" de cada proyecto, y el texto largo en "resumen": no se han
# borrado porque son el material de esas paginas. Si alguna vez vuelven a la
# ficha, esto es lo que hacia:
#
#     <div class="lectura"><span class="lectura__clave">PR-AUC test</span>
#                          <span class="lectura__valor">0,691</span></div>
#
# El CSS de .lecturas y .chip sigue en plantilla.css por lo mismo.


def obra(p):
    """Una ficha corta que LLEVA al trabajo, no un resumen del trabajo.

    Antes cada ficha traía el párrafo, las dos cifras y los chips. Cuatro
    fichas así son cuatro columnas de texto puestas de lado, y quien las mira
    ya no entra en ninguna porque cree que ya lo ha leído. Ahora la ficha dice
    QUÉ es y DE QUÉ va, y lo explicado está detrás del clic, en la página del
    trabajo, que es donde Pedro puede extenderse.

    La ficha entera es el objetivo del clic, con un recurso viejo: el enlace
    del título estira un ::after invisible por encima de toda la tarjeta. Así
    el HTML sigue teniendo UN enlace con su texto de verdad —"Ganar a la casa
    de apuestas", no "leer más"— y el área pulsable es la tarjeta completa.
    Los enlaces del pie se levantan con z-index para seguir siendo suyos.
    """
    principal = (p.get("enlaces") or [None])[0]
    pie = "".join(enlace(l, "obra__enlace") for l in p.get("enlaces", []))
    if not pie and p.get("nota"):
        pie = f'<span class="obra__nota">{e(p["nota"])}</span>'

    if principal:
        extra = ' target="_blank" rel="noopener"' if principal.get("nueva_pestana") else ""
        accion = f' data-accion="{e(principal["accion"])}"' if principal.get("accion") else ""
        titulo = (f'<a class="obra__ir" href="{e(principal["href"])}"{accion}{extra}>'
                  f'{e(p["titulo"])}</a>')
        # aria-hidden porque no añade nada: el enlace del título ya dice a
        # dónde va, y un segundo anuncio de lo mismo solo alarga el recorrido.
        boton = '<span class="obra__ir-boton" aria-hidden="true">↗</span>'
    else:
        # Sin destino no hay flecha: una tarjeta que parece pulsable y no lo es
        # se lee como un enlace roto. El TFM es ese caso —su memoria lleva
        # datos del CRM y no circula— y lo dice en el pie.
        titulo = e(p["titulo"])
        boton = ""

    return f"""
        <article class="obra{'' if principal else ' obra--sin-destino'}" id="{e(p['id'])}">
          <div class="obra__lienzo">
            <img class="obra__portada{' obra__portada--entera' if p.get('tratamiento') == 'entera' else ''}"
                 src="{ruta(p['imagen'])}" width="1000" height="620"
                 loading="lazy" decoding="async" alt="{e(p['alt'])}">
          </div>
          <div class="obra__cuerpo">
            <div class="obra__cabecera">
              <div class="obra__rotulos">
                <h3 class="obra__titulo">{titulo}</h3>
                <p class="obra__categoria">{e(p['categoria'])} · {e(p['ano'])}</p>
              </div>
              {boton}
            </div>
            <div class="obra__pie">{pie}</div>
          </div>
        </article>"""


def fila_destreza(g):
    fichas = "".join(
        f'<span class="ficha"><span class="ficha__icono" aria-hidden="true">{e(i["icono"])}</span>'
        f'{e(i["nombre"])}</span>'
        for i in g["items"])
    return f"""
      <div class="fila-destreza">
        <p class="rotulo rotulo--micro">{e(g['rotulo'])}</p>
        <div class="fichas">{fichas}</div>
      </div>"""


def puesto(x):
    abierto = " open" if x.get("abierto") else ""
    return f"""
        <details class="puesto"{abierto}>
          <summary class="puesto__resumen">
            <span>
              <span class="puesto__titulo">{e(x['puesto'])}</span>
              <span class="puesto__donde">{e(x['empresa'])} · {e(x['ciudad'])}</span>
            </span>
            <span class="puesto__cuando">{e(x['cuando'])}</span>
            <span class="galon" aria-hidden="true"></span>
          </summary>
          <div class="puesto__cuerpo">
            <p class="parrafo">{e(x['descripcion'])}</p>
          </div>
        </details>"""


def hito(x, n):
    """Una fila de formación: cabecera siempre visible, cuerpo que se abre.

    No es un <details> como la experiencia. Aquí la fila se abre al pasar el
    ratón, y para eso hace falta gobernar la altura fotograma a fotograma: un
    <details> abre de golpe y no hay forma de animarlo sin pelearse con el
    navegador. A cambio hay que poner a mano lo que <details> da gratis, y está
    puesto: la cabecera es un <button> de verdad, con aria-expanded y
    aria-controls apuntando al panel. Sin JavaScript no se colapsa nada y las
    cuatro filas se leen enteras.
    """
    puntos = "".join(f"<li>{e(p)}</li>" for p in x["puntos"])
    etiquetas = "".join(f'<span class="etiqueta">{e(t)}</span>' for t in x["etiquetas"])

    # Una imagen sin poner no deja un hueco: deja una placa de degradado que se
    # ve claramente distinta, para que se note que falta y no parezca un fallo.
    if x["imagen"] == "PENDIENTE":
        placa = '<span class="hito__placa hito__placa--vacia" aria-hidden="true"></span>'
    else:
        # Las fotos se ven ENTERAS: el CSS usa object-fit:contain, así que aquí
        # no hace falta ningún foco. Lo único que se pasa es el tratamiento,
        # para el logotipo, que viene en negro sobre transparente y sobre un
        # panel oscuro sería invisible.
        clase = "hito__placa"
        if x.get("tratamiento"):
            clase += f' hito__placa--{e(x["tratamiento"])}'
        placa = (f'<span class="{clase}" aria-hidden="true">'
                 f'<img src="{ruta(x["imagen"])}"'
                 f' loading="lazy" decoding="async" alt=""></span>')

    return f"""
        <div class="hito" data-fila>
          {placa}
          <div class="hito__dentro">
            <button class="hito__cabeza" type="button"
                    aria-expanded="false" aria-controls="formacion-{n}">
              <span class="hito__titulo">{e(x['titulo'])}</span>
              <span class="hito__meta">{" · ".join(filter(None, [e(x['institucion']), e(x['cuando']), e(x.get('detalle', ''))]))}</span>
            </button>
            <div class="hito__cuerpo" id="formacion-{n}">
              <ul class="hito__puntos">{puntos}</ul>
              <div class="etiquetas">{etiquetas}</div>
            </div>
          </div>
          <span class="hito__n" aria-hidden="true">{n:02d}</span>
        </div>"""


def red(r, clase=""):
    extra = ' target="_blank" rel="noopener"' if r.get("nueva_pestana") else ""
    # "descarga" pone el atributo download con el nombre con el que se guarda.
    # Sin el, el navegador abre el PDF en una pestaña y quien queria el
    # archivo tiene que buscar el boton de guardar del visor.
    if r.get("descarga"):
        extra += f' download="{e(r["descarga"])}"'
    return (f'<a class="{clase}" href="{e(r["href"])}"{extra}>'
            f'<span aria-hidden="true">{e(r["icono"])}</span> {e(r["texto"])}</a>')


# ---------------------------------------------------------------- montaje

def main():
    d = json.loads(DATOS.read_text(encoding="utf-8"))
    s, po, ma = d["sitio"], d["portada"], d["mapa"]
    tr, de, ex = d["trabajo"], d["destrezas"], d["experiencia"]
    fo, sm, co = d["formacion"], d["sobre_mi"], d["contacto"]
    fl = d["flotante"]

    # Los enlaces sin rellenar no se pintan: un enlace a "PENDIENTE" delante de
    # un reclutador es peor que no poner nada. Se cuentan y se avisa al final.
    redes = [r for r in d["redes"] if r["href"] != "PENDIENTE"]
    pendientes = [r["texto"] for r in d["redes"] if r["href"] == "PENDIENTE"]

    nav = "".join(f'<li><a href="#{e(n["ancla"])}" data-nav>{e(n["texto"])}</a></li>'
                  for n in d["nav"])

    # Search Console verifica la propiedad leyendo esta etiqueta en el
    # <head> de la home. Se pinta solo si hay token: si algun dia se quita la
    # propiedad, se vacia la clave del JSON y desaparece sola, sin tocar aqui.
    verificacion = ""
    if s.get("verificacion_google"):
        verificacion = ('<meta name="google-site-verification" content="'
                        + e(s["verificacion_google"]) + '">\n')

    doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- GENERADO por herramientas/hacer-plantilla.py desde contenido-plantilla.json.
     No lo edites a mano: se sobrescribe entero en cada ejecución. -->
<title>{e(s['titulo_pestana'])}</title>
<meta name="description" content="{e(recortar(s['descripcion']))}">
<meta name="author" content="{e(s['nombre'])}">
{verificacion}<meta name="theme-color" content="#0B0C0F">

<link rel="icon" href="favicon.ico" sizes="32x32">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">

<meta property="og:type" content="profile">
<meta property="og:site_name" content="{e(s['nombre'])}">
<meta property="og:locale" content="es_ES">
<meta property="og:title" content="{e(s['titulo_pestana'])}">
<meta property="og:description" content="{e(recortar(s['descripcion']))}">
<meta property="og:image" content="https://{e(s['dominio'])}/medios/og.jpg">
<meta property="og:image:alt" content="Tarjeta con el nombre de Pedro Pérez Blanco y el titular del portfolio.">
<meta property="og:url" content="https://{e(s['dominio'])}/index.html">
<meta name="twitter:card" content="summary_large_image">

<link rel="preload" href="tipos/barlow-condensed-600.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="tipos/barlow-400.woff2" as="font" type="font/woff2" crossorigin>

<link rel="stylesheet" href="ui/tipos.css">
<link rel="stylesheet" href="ui/plantilla.css">
</head>
<body>

<!-- La red de datos del fondo. Va aquí, antes que nada, porque es lo que hay
     detrás de todo; el CSS la fija a la ventana y la saca del flujo. Es
     decoración pura: aria-hidden para que ningún lector de pantalla la
     anuncie, y ui/fondo.js no la monta siquiera si el sistema pide menos
     movimiento. -->
<canvas class="fondo" id="fondo" aria-hidden="true"></canvas>

<a class="saltar" href="#contenido">Saltar al contenido</a>

<header class="barra" id="barra">
  <nav class="barra__caja" aria-label="Secciones">
    <a class="barra__marca" href="#contenido">
      <span class="barra__iniciales" aria-hidden="true">{e(s['iniciales'])}</span>
      <span class="barra__nombre">{e(s['nombre'])}</span>
    </a>
    <ul class="barra__lista" id="menu-lista">{nav}</ul>
    <!-- Solo aparece con el movimiento parado. Sin esto, la unica forma de
         volver a encenderlo es el boton del pie, que esta al 99% de la pagina:
         quien pause sin querer ve una web muerta y no sabe por que. -->
    <button class="barra__pausa" id="reanudar" type="button">
      <span class="barra__pausa__punto" aria-hidden="true"></span>Movimiento en pausa
      <span class="oculto">, pulsa para reanudarlo</span>
    </button>
    <a class="barra__cta" href="#{e(d['nav_cta']['ancla'])}">{e(d['nav_cta']['texto'])}</a>
    <button class="barra__menu" id="menu" type="button"
            aria-expanded="true" aria-controls="menu-lista">
      <span aria-hidden="true"></span>
      <span class="oculto">Abrir el menú</span>
    </button>
  </nav>
  <div class="barra__avance" id="avance" aria-hidden="true"></div>
</header>

<main id="contenido">

<!-- ================= PORTADA ================= -->
<section class="portada">
  <div class="marco">
    <div class="portada__reparto">
      <div class="portada__panel" data-revelar>
        <!-- El saludo se escribe y se corrige solo. La mitad animada va
             aria-hidden: un nodo cuyo texto cambia cada 80ms es ruido en el
             árbol de accesibilidad, y el cursor es un signo de puntuación que
             nadie necesita oír. Al lado va la versión quieta, para ellos.
             "Hola" viene ya escrito en el HTML: así la línea nunca está vacía
             antes de que corra el script, ni con movimiento reducido. -->
        <p class="portada__saludo">
          <span class="oculto">{e(po['saludo'])}{e(po['saludo_cola'])}</span>
          <span class="saludo" id="saludo" aria-hidden="true"
                data-saludos="{e(json.dumps(po['saludos'], ensure_ascii=False))}">
            <span class="saludo__palabra" id="saludo-palabra">{e(po['saludo'])}</span
            ><span class="saludo__cursor">|</span
            ><span class="saludo__cola">{e(po['saludo_cola'])}</span>
          </span>
        </p>
        <h1 class="portada__nombre" data-partir>{e(po['nombre'])}</h1>
        <p class="portada__lema">{e(po['lema_antes'])} <em class="acento">{e(po['lema_acento'])}</em> {e(po['lema_despues'])}</p>
        <p class="parrafo parrafo--lead">{e(po['entradilla'])}</p>
        <div class="botones">
          <a class="boton boton--solido" href="#{e(po['cta_principal']['ancla'])}">{e(po['cta_principal']['texto'])}</a>
          <a class="boton" href="#{e(po['cta_secundaria']['ancla'])}">{e(po['cta_secundaria']['texto'])}</a>
        </div>
        <p class="portada__meta">
          <span><strong>{e(po['meta_fuerte'])}</strong> · {e(po['meta_resto'])}</span>
          <span class="portada__estado">{e(po['disponibilidad'])}</span>
        </p>
      </div>
      <img class="portada__imagen" src="{e(po['imagen'])}" width="720" height="900"
           decoding="async" alt="{e(po['imagen_alt'])}" data-revelar>
    </div>
  </div>
</section>

<!-- ================= MAPA DEL TRABAJO ================= -->
<!-- El grafo es el mismo de index.html: ui/mapa.js, la misma física y los
     mismos catorce nodos. Aquí va entre la portada y los trabajos porque es
     justo la transición que hace: enseña que los seis proyectos comparten
     herramientas, y cada nodo baja a la ficha de su proyecto. -->
<section class="seccion mapa" id="mapa">
  <div class="marco">
    <div class="seccion__cabecera" data-revelar>
      <p class="rotulo eyebrow">{e(ma['rotulo'])}</p>
      {titular(ma, "titulo-menor")}
      <p class="parrafo seccion__intro">{e(ma['entradilla'])}</p>
    </div>
    <div class="mapa__caja" data-revelar>
      <canvas class="mapa__lienzo" id="mapa-portfolio"
              role="img" aria-label="Grafo de los seis proyectos y las herramientas que comparten"></canvas>
    </div>
    <p class="mapa__aviso">{e(ma['aviso_movil'])}</p>
  </div>
</section>

<!-- ================= 01 · TRABAJO ================= -->
<section class="seccion" id="trabajo">
  <div class="marco">
    {cabecera(tr)}
    <div class="carrusel" data-revelar>
      <div class="carrusel__pista" id="pista-trabajos" tabindex="0"
           role="region" aria-label="Proyectos, se desplaza a lo ancho">
        {"".join(obra(p) for p in tr["proyectos"])}
      </div>
      <div class="carrusel__mandos">
        <button class="carrusel__boton" id="carrusel-atras" type="button">
          <span aria-hidden="true">←</span><span class="oculto">Grupo anterior</span>
        </button>
        <button class="carrusel__boton" id="carrusel-alante" type="button">
          <span aria-hidden="true">→</span><span class="oculto">Grupo siguiente</span>
        </button>
        <div class="carrusel__puntos" id="carrusel-puntos" hidden></div>
      </div>
    </div>
    <p class="parrafo aviso" data-revelar>{e(tr['aviso'])}</p>
  </div>
</section>

<!-- ================= 02 · DESTREZAS ================= -->
<section class="seccion" id="destrezas">
  <div class="marco">
    {cabecera(de, "titulo-menor")}
    <div data-revelar>
      {"".join(fila_destreza(g) for g in de["grupos"])}
    </div>
  </div>
</section>

<!-- ================= 03 · EXPERIENCIA ================= -->
<section class="seccion" id="experiencia">
  <div class="marco">
    {cabecera(ex)}
    <div class="experiencia__reparto">
      <img class="experiencia__imagen" src="{ruta(ex['imagen'])}" width="1200" height="900"
           loading="lazy" decoding="async" alt="{e(ex['imagen_alt'])}" data-revelar>
      <div data-revelar>
        {"".join(puesto(x) for x in ex["puestos"])}
      </div>
    </div>
  </div>
</section>

<!-- ================= 04 · FORMACIÓN ================= -->
<section class="seccion" id="formacion">
  <div class="marco">
    {cabecera(fo, "titulo-menor")}
    <div class="hitos" id="hitos" data-revelar>
      {"".join(hito(x, i + 1) for i, x in enumerate(fo["bloques"]))}
    </div>
  </div>
</section>

<!-- ================= 05 · SOBRE MÍ ================= -->
<section class="seccion" id="sobre-mi">
  <div class="marco">
    {cabecera(sm, "titulo-menor")}
    <div class="prosa" data-revelar>
      {"".join(f"<p>{e(t)}</p>" for t in sm["parrafos"])}
    </div>
  </div>
</section>

<!-- ================= LLAMADA FINAL ================= -->
<section class="llamada" id="contacto">
  <div class="marco">
    <div class="llamada__panel" data-revelar>
      <h2 class="llamada__titular">{e(co['titular_antes'])} <em class="acento">{e(co['titular_acento'])}</em>{e(co['titular_despues'])}</h2>
      <p class="parrafo">{e(co['entradilla'])}</p>
      <div class="botones">
        <a class="boton boton--solido" href="{e(co['cta']['href'])}">{e(co['cta']['texto'])} {FLECHA}</a>
        {"".join(red(r, "boton") for r in redes[1:])}
      </div>
    </div>
  </div>
</section>

</main>

<!-- El anillo que acompaña al puntero. Va vacio: lo unico que hace es
     seguirlo, y ui/plantilla.js solo lo enciende si hay raton de verdad. -->
<div class="nodo-cursor" id="nodo-cursor" aria-hidden="true"></div>

<!-- Llamada flotante. Nace invisible de verdad (visibility, no solo
     transform): asi no se puede tabular a un enlace que no esta en pantalla.
     Se aparta sola cuando aparece la llamada final del contacto. -->
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
        <p class="pie__nombre">{e(s['nombre'])}</p>
        <p class="pie__nota">{e(d['pie']['copyright'])}</p>
        <button class="pie__quieto" id="quieto" type="button" aria-pressed="false">
          <span class="pie__punto" aria-hidden="true"></span><span data-texto>Parar movimiento</span>
        </button>
      </div>
      <div class="pie__enlaces">
        {"".join(red(r, "") for r in redes)}
      </div>
    </div>
  </div>
</footer>

<script src="ui/fondo.js" defer></script>
<script src="ui/mapa.js" defer></script>
<script src="ui/plantilla.js" defer></script>
</body>
</html>
"""

    SALIDA.write_text(doc, encoding="utf-8")
    print(f"Escrito {SALIDA.name}  ({SALIDA.stat().st_size / 1024:.0f} KB)")
    print(f"  {len(tr['proyectos'])} proyectos · {len(de['grupos'])} grupos de herramientas · "
          f"{len(ex['puestos'])} puestos · {len(fo['bloques'])} bloques de formación · "
          f"{len(redes)} enlaces")

    sin_repo = [p["titulo"] for p in tr["proyectos"]
                if p.get("github", "PENDIENTE") == "PENDIENTE"]
    if pendientes or sin_repo:
        print("\n  Falta por rellenar (no se pinta hasta que tenga valor):")
        for x in pendientes:
            print(f"    · {x}   -> ponle la URL en contenido-plantilla.json")
        for x in sin_repo:
            print(f"    · GitHub de «{x}»")

    # Un vistazo a lo que queda de la plantilla vieja. Es facil olvidarse un
    # "Elemento 1" en una lista larga y publicarlo.
    texto = SALIDA.read_text(encoding="utf-8")
    # Cadenas EXACTAS de la plantilla de relleno. "Proyecto de datos" y
    # "Proyecto estratégico" son contenido real y no pueden dispararlo.
    restos = sorted(set(re.findall(
        r"Elemento \d|Nombre del proyecto|Nombre Apellido|medios/marcadores/|"
        r"Título o certificación|Puesto (?:uno|dos|tres|cuatro)|PENDIENTE",
        texto)))
    if restos:
        print("\n  AVISO: quedan restos de la plantilla de relleno: " + ", ".join(restos))

    print("\nPara cambiar cualquier texto: contenido-plantilla.json, y vuelve a ejecutar esto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
