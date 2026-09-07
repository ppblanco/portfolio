# Portfolio · Pedro Pérez Blanco

**Data & AI** — Máster en Business Analytics (MUBA), Universidad Pontificia Comillas ICADE

Sitio estático con seis casos de estudio: machine learning, NLP, deep learning,
análisis exploratorio y estrategia de marca.

---

## Los seis proyectos

| Proyecto | Qué es | Repositorio |
|---|---|---|
| **Lead scoring y asistente RAG** | TFM. Random Forest que prioriza contactos de admisiones en categorías A/B/C, más un asistente con RAG | [admissions-lead-scoring-rag](https://github.com/ppblanco/admissions-lead-scoring-rag) |
| **Predicción de ventas de videojuegos** | Regresión supervisada, comparación de cuatro modelos e interpretabilidad con SHAP | [video-game-sales-prediction](https://github.com/ppblanco/video-game-sales-prediction) |
| **Predicción de demanda con RNN** | Forecasting con SimpleRNN, LSTM, GRU y Bi-LSTM sobre partición cronológica | [retail-demand-forecasting-rnn](https://github.com/ppblanco/retail-demand-forecasting-rnn) |
| **Letterboxd · topic modeling** | LDA sobre reseñas multilingües; cuando los tópicos son idiomas y no temas | [letterboxd-topic-modeling](https://github.com/ppblanco/letterboxd-topic-modeling) |
| **Ganar a la casa de apuestas** | EDA sobre 11.794 partidos ATP y el margen de la casa | [atp-tennis-betting-analysis](https://github.com/ppblanco/atp-tennis-betting-analysis) |
| **Lipton · The Summer Shake Up** | Estrategia de marca y campaña publicitaria para la generación Z | [lipton-summer-shake-up](https://github.com/ppblanco/lipton-summer-shake-up) |

## Cómo está hecho

**Sin frameworks y sin dependencias en el navegador.** HTML, CSS y JavaScript
a secas. No hay React, ni build de assets, ni librería de gráficos: los SVG de
las páginas de caso los dibuja un generador de Python, a mano y con
`viewBox`, así que escalan solos y no necesitan una sola media query.

**El contenido no vive en el HTML.** Cada página sale de un JSON:

```
contenido-plantilla.json    ->  index.html
contenido-tfm.json          ->  trabajos/tfm-lead-scoring.html
contenido-videojuegos.json  ->  trabajos/videojuegos.html
...
```

Editar el HTML a mano no sirve de nada: se regenera entero.

## Estructura

```
.
├── index.html                 el portfolio
├── 404.html
├── contenido-*.json           todo el texto, uno por página
├── ui/                        CSS y JavaScript
├── tipos/                     tipografías subsetadas (woff2)
├── trabajos/                  las seis páginas de caso y sus PDF
├── medios/                    imágenes, vídeos y CV
├── herramientas/              los generadores
└── pruebas/                   285 pruebas con Playwright
```

## Desarrollo local

```bash
# regenerar las páginas después de tocar un JSON
python herramientas/hacer-plantilla.py     # index.html
python herramientas/hacer-caso.py          # las seis páginas de caso
python herramientas/hacer-informe.py       # portadas, páginas y peso de los PDF

# levantar el sitio y pasar las pruebas
cd pruebas && npm install && npx playwright test
```

Los generadores solo necesitan la librería estándar salvo `hacer-informe.py`
y las herramientas de imagen, que usan `pypdf`, `pypdfium2` y `Pillow`.

## Despliegue

El sitio se publica en Netlify. El flujo completo, en orden, es este:

```
contenido-*.json  ->  herramientas/hacer-*.py  ->  index.html y trabajos/*.html
                                                        |
                                     herramientas/preparar-publicacion.py
                                                        |
                                                    publicar/  ->  Netlify
```

**Los dos pasos son distintos y hacen cosas distintas.** Los generadores
escriben el HTML desde los JSON; `preparar-publicacion.py` solo *empaqueta* el
HTML que ya existe. Empaquetar no regenera: si cambias un JSON y publicas sin
pasar antes por su generador, se sube la versión anterior de la página. Por eso
el orden importa.

```bash
py herramientas/hacer-plantilla.py   # 1. index.html desde su JSON
py herramientas/hacer-caso.py        # 2. las seis páginas de caso
py herramientas/hacer-informe.py     # 3. si ha cambiado algún PDF
py herramientas/preparar-publicacion.py   # 4. monta publicar/
npx netlify-cli deploy --prod --no-build --dir publicar   # 5. sube
```

`preparar-publicacion.py` acepta `--destino RUTA` para montar el paquete
fuera de esta carpeta. Hace falta cuando el proyecto vive dentro de OneDrive:
OneDrive convierte `publicar/` en un marcador de «Archivos a petición» y
entonces el script no puede borrarla para regenerarla. No es un enlace roto y
no hay que tocar el marcador; basta con sacar el paquete del árbol de OneDrive:

```bash
py herramientas/preparar-publicacion.py --destino C:/ruta/local/publicar
npx netlify-cli deploy --prod --no-build --dir C:/ruta/local/publicar
```

`--no-build` es deliberado: el `netlify.toml` declara `python3 …`, y en la
máquina de trabajo (Windows) ese comando no existe. El paquete se genera en
local y se sube ya hecho.

**El despliegue continuo desde GitHub no está conectado.** Un `push` a `main`
no publica nada: hay que lanzar el comando. Es una decisión, no un olvido —
automatizar publicaría también los errores, y el build de Netlify empaquetaría
sin regenerar.

`preparar-publicacion.py` monta `publicar/` con una **lista blanca**: copia
`index.html`, `404.html`, los iconos y las carpetas `tipos/`, `ui/`,
`trabajos/` y `medios/`, y genera `robots.txt` y `_headers` con la CSP. Lo que
no está en esa lista no sale. Esa es la mitad de la seguridad del sitio:
`originales/`, `referencias/`, `herramientas/` y `pruebas/` no se publican
porque nadie las ha apuntado.

## Accesibilidad y movimiento

- Todo el movimiento respeta `prefers-reduced-motion` y un interruptor propio
  de «pausar movimiento» que congela cualquier animación de la página.
- Los gráficos SVG llevan descripción para lector de pantalla con las mismas
  cifras que se ven.
- El hover resalta, nunca revela: ningún dato existe solo al pasar el ratón.

## Créditos

Fotografías, vídeos y memorias son de los proyectos correspondientes. Los
trabajos de **Deep Learning**, **Letterboxd** y **Lipton** son de equipo y su
autoría completa está en el repositorio de cada uno.

Tipografías: Barlow y Barlow Condensed (SIL OFL), IBM Plex Mono (SIL OFL).

## Licencia

Ver [NOTICE](NOTICE). El repositorio se publica **sin licencia**.

## Contacto

**Pedro Pérez Blanco** · [github.com/ppblanco](https://github.com/ppblanco) ·
[LinkedIn](https://linkedin.com/in/pedroperezblanco)
