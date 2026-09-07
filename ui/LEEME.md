# El CSS y el JavaScript del sitio

Lo que hay en `ui/`: la piel y el comportamiento de las siete paginas. El HTML
no se escribe aqui —lo generan los scripts de `herramientas/` desde los JSON—,
pero todo lo que se ve y todo lo que se mueve, si.

## Por qué es propio y no Bootstrap, Bulma o Shoelace

Lo consideré y lo descarté, y creo que es la decisión correcta. Una librería de
terceros aquí sumaba tres problemas y no resolvía ninguno:

- **El diseño se pelearía con ella.** Bootstrap y Bulma traen su propio aspecto
  —esquinas redondeadas, azules, sombras— y esta identidad es lo contrario:
  negro, filos de 1px, Barlow Condensed. Habría que sobrescribir casi todo, y
  entonces la librería solo aporta peso.
- **El peso y el bloqueo.** Son entre 200 KB y 1 MB. Esta página se abre desde
  la red de una empresa, que puede bloquear dominios externos: por eso las
  tipografías ya se sirven desde aquí y no desde Google. Traer una librería de
  un CDN reabriría justo ese agujero, y traerla dentro engorda el sitio para
  usar el 5% de lo que hace.
- **El build.** Las que valen la pena piden un paso de compilación, y este
  proyecto es HTML plano a propósito: se despliega arrastrando una carpeta.

Lo que sí aporta una librería —consistencia, piezas reutilizables, no repetir
CSS— se consigue igual con tokens y componentes. Eso es lo que hay aquí. Si aun
así prefieres una de terceros, se cambia, pero conviene saber qué se paga.

## Los archivos

Siete archivos, y ninguno sobra. Aqui vivia antes la descripcion de dos juegos
de hojas —el de `index.html` y el del portfolio— con `tokens.css`,
`componentes.css`, `pagina.css`, `claro.css`, `consola.js`, `revelar.js`,
`pagina.js` y `cuaderno.css`. Nada de eso existe ya: se fue con la limpieza
del 01/09/2026, cuando el portfolio paso a ser la unica version y `plantilla`
dejo de ser una plantilla para ser la pagina. Esto es lo que hay de verdad.

| Archivo | Que hace | Quien lo carga |
| --- | --- | --- |
| `tipos.css` | Las caras tipograficas, servidas desde este dominio | todas |
| `plantilla.css` | La piel entera del sitio, con sus tokens dentro. No hereda de nadie | todas |
| `trabajo.css` | Solo lo propio de una pagina de caso: portada, rail de apartados y reparto de texto y grafico. Va **despues** de `plantilla.css` y no define ni un token nuevo | las seis paginas de caso |
| `plantilla.js` | Los bloques de comportamiento: revelado, menu, barra que se aparta, barra de avance, carrusel, montaje del mapa, fichas, saludo, muelle de formacion, titular, anillo del cursor, CTA flotante, interruptor del movimiento, video de portada y visor de documento | todas |
| `fondo.js` | La red de datos que corre por detras de toda la pagina | todas |
| `mapa.js` | El grafo de proyectos y herramientas. Expone `crearMapa` en `window` y recibe el color de senal por opciones | solo `index.html` |
| `LEEME.md` | Esto. `*.md` esta en la lista de exclusion de `preparar-publicacion.py`, asi que no se publica | nadie |

**El HTML no se edita a mano.** `index.html` y las seis paginas de
`trabajos/` las escriben enteras los generadores desde su JSON:

```
contenido-plantilla.json  --hacer-plantilla.py-->  index.html
contenido-<caso>.json     --hacer-caso.py------->  trabajos/<caso>.html
```

Lo de aqui dentro —CSS y JS— si se edita a mano: no lo genera nadie.

## Los componentes

La lista que habia aqui nombraba `.titulo-1`, `.panel`, `.rejilla`, `.pieza` y
`.metrica`, que ya no existen: se quedo vieja y decia cosas que no eran. Una
tabla de clases repetida a mano al lado de la hoja de estilo se desincroniza
sola, asi que no se repite.

**La fuente son las propias hojas**, que van por bloques numerados y con su
comentario: `plantilla.css` para todo el sitio y `trabajo.css` para lo que solo
existe en una pagina de caso. Buscar la clase ahi da la verdad de hoy; buscarla
aqui daba la de hace tres meses.

## El color de senal

Hay **un solo acento por pagina** y se gasta solo en datos y estados: el numero
de seccion, la palabra acentuada del titular, las flechas y el boton principal.
Si se empieza a usar para decorar, deja de significar nada.

El del sitio es el ambar `--senal:#E0A458`. Cada pagina de caso puede pisarlo
con el suyo desde el bloque `paleta` de su JSON —Apuestas va en verde azulado,
Letterboxd en naranja, Deep Learning en azul—, y por eso **ningun CSS esta
duplicado por caso**: toda la hoja pinta con `var(--senal)` y sus tres
hermanas, y lo unico que cambia son esas cuatro variables.

Si tocas un color que se use sobre el acento, comprueba el contraste en los
seis, no solo en el que tengas abierto: el ambar es el mas claro de todos y el
que mejor perdona.

## Movimiento

Todo lo que se mueve pasa por `prefers-reduced-motion`. Quien haya pedido menos
movimiento en su sistema no ve ninguno, y el contenido aparece entero desde el
principio. No es un extra: hay gente a la que el movimiento le provoca mareo.

Y las apariciones al hacer scroll tienen una trampa cuidada: la clase que oculta
los elementos la pone el propio JavaScript. Si el script no llegara a
ejecutarse, no se esconde nada y la página se ve completa.
