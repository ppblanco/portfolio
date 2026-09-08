// =============================================================
// Pruebas de las páginas de caso de trabajos/
// -------------------------------------------------------------
//   trabajos/tfm-lead-scoring.html   el TFM
//   trabajos/videojuegos.html        predicción de ventas
//   trabajos/apuestas.html           ganar a la casa de apuestas
//   trabajos/lipton.html             the summer shake up
//
// Las cuatro salen del mismo generador, así que lo estructural se
// prueba en bucle sobre las cuatro: una prueba escrita cuatro
// veces acaba arreglándose solo en una.
//
// Y hay un grupo que no es compartido: CONFIDENCIALIDAD, solo del
// TFM. Ese trabajo se hizo con el CRM de una universidad y hay
// datos que no pueden salir. "Se me olvidó" no vale cuando la
// página ya está delante de cinco empresas.
//
// Ejecutar:  cd pruebas  &&  npx playwright test casos
// =============================================================

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const TFM = '/trabajos/tfm-lead-scoring.html';

const CASOS = [
  {
    nombre: 'TFM',
    ruta: TFM,
    secciones: ['s-problema', 's-recorrido', 's-fases', 's-modelo', 's-abc', 's-tiempo', 's-asistente', 's-cierre'],
    cifras: ['30,35', '95,82', '8,06', '0,691', '0,947', '×6,8', '24.365',
             '0,698', '0,564', '0,685', '0,007'],
    // El TFM no lleva vídeo: su portada es la del fondo de datos de siempre.
    video: null,
  },
  {
    nombre: 'Opponent Pool Self-Play',
    ruta: '/trabajos/rlgym-selfplay-pool.html',
    secciones: ['s-pregunta', 's-arquitectura', 's-resultado', 's-diagnostico',
                's-puerta', 's-recompensas', 's-falsacion', 's-correcciones', 's-cierre'],
    // El resultado es un intervalo que cruza el cero, y por eso el SIGNO forma
    // parte del dato: −0,83 con el intervalo entero. Dejarlo en 0,83 convierte
    // «no se puede afirmar nada» en «el brazo B gana», que es lo contrario de
    // lo que midió el experimento.
    cifras: ['−0,83', '−3,89', '+2,22', '5,00', '4,17', '1,55', '0,0074',
             '61,5', '22,5', '16,0', '2,0', '2,5', '720',
             // Las puertas de H2: medido y requerido, los dos. Sin el par, la
             // pagina podria decir «falla» sin ensenar por cuanto.
             '0,0310', '0,0465', '0,0135', '0,0148',
             // Y los tres canales del diagnostico de recompensa.
             '72,0', '67,5', '14,0', '37,5', '56,5', '52,5',
             // Lo que separa lo heredado de lo mio, que es la cifra que
             // mas le importa a quien lee esta pagina.
             '5.401'],
    // Portada con vídeo. El metraje es gameplay de terceros usado como
    // CONTEXTO VISUAL y va rotulado como tal en la propia portada: entra en
    // las pruebas de vídeo como los otros cinco.
    video: 'rlgym',
  },
  {
    nombre: 'Videojuegos',
    ruta: '/trabajos/videojuegos.html',
    secciones: ['s-pregunta', 's-hipotesis', 's-modelos', 's-shap', 's-limites', 's-uso', 's-cierre'],
    // Las dos escalas del R² tienen que estar las dos: 0,498 es sobre
    // log(ventas+1) y 0,227 sobre millones. Si alguien vuelve a dejar solo la
    // primera, la página miente otra vez.
    cifras: ['16.719', '16.444', '0,498', '0,227', '0,291', '0,347', '51'],
    video: 'videojuegos',
  },
  {
    nombre: 'Deep learning',
    ruta: '/trabajos/deep-learning.html',
    secciones: ['s-problema', 's-particion', 's-modelos', 's-resultados', 's-limites', 's-cierre'],
    cifras: ['274', '20,95', '4,550', '4,867', '5,125', '56'],
    // Tiene portada con vídeo como los demás. Estuvo en null y eso lo dejaba
    // fuera del grupo de pruebas de vídeo sin que nada lo dijera.
    video: 'deep-learning',
  },
  {
    nombre: 'Letterboxd',
    ruta: '/trabajos/letterboxd.html',
    secciones: ['s-corpus', 's-nlp', 's-hallazgo', 's-experimento', 's-limites', 's-cierre'],
    cifras: ['11.968', '111.798', '32,3', '62,4', '0,6038', '0,5107'],
    video: 'letterboxd',
  },
  {
    nombre: 'Apuestas',
    ruta: '/trabajos/apuestas.html',
    secciones: ['s-pregunta', 's-datos', 's-hipotesis', 's-simulacion', 's-limites', 's-cierre'],
    cifras: ['11.794', '56,96', '55,33', '53,24', '47,62', '45,68', '68,18', '−4,54', '5,46'],
    video: 'apuestas',
  },
  {
    nombre: 'Lipton',
    ruta: '/trabajos/lipton.html',
    secciones: ['s-encargo', 's-marca', 's-investigacion', 's-concepto', 's-numeros', 's-cierre'],
    cifras: ['68', '184.000', '210.000', '26.000', '14,13'],
    video: 'lipton',
  },
];

const MOVIL = { width: 375, height: 800 };
const ESCRITORIO = { width: 1440, height: 900 };

async function irConMovimientoReducido(page, ruta) {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(ruta);
  const activo = await page.evaluate(() =>
    matchMedia('(prefers-reduced-motion: reduce)').matches);
  expect(activo, 'la emulación de movimiento reducido no se aplicó').toBe(true);
}

// Mide el contraste REAL de cada texto: color efectivo contra el fondo
// compuesto de sus ancestros, respetando la transparencia. Sin componer el
// alfa, un distintivo con fondo ambar al 14% parece 1:1 y es un falso aviso.
async function textosConPocoContraste(page) {
  return page.evaluate(() => {
    const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
    const leer = (s) => { const m = (s || '').match(/[\d.]+/g); if (!m) return null;
      return [ +m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1 ]; };
    const sobre = (f, d) => [0, 1, 2].map((i) => f[3] * f[i] + (1 - f[3]) * d[i]);

    const fondoDe = (el) => {
      const capas = [];
      for (let n = el; n; n = n.parentElement) {
        const c = leer(getComputedStyle(n).backgroundColor);
        if (c && c[3] > 0) { capas.push(c); if (c[3] === 1) break; }
      }
      let base = [11, 12, 15];
      for (let i = capas.length - 1; i >= 0; i--) base = sobre(capas[i], base);
      return base;
    };

    const malos = [];
    for (const el of document.querySelectorAll('*')) {
      if (el.children.length || !(el.textContent || '').trim()) continue;
      if (el.closest('[aria-hidden="true"]')) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      const fg = leer(cs.color); if (!fg) continue;
      const bg = fondoDe(el);
      const l1 = lum(sobre(fg, bg)), l2 = lum(bg);
      const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
      const px = parseFloat(cs.fontSize), peso = parseInt(cs.fontWeight) || 400;
      const minimo = (px >= 24 || (px >= 18.66 && peso >= 700)) ? 3 : 4.5;
      if (ratio + 0.005 < minimo) {
        malos.push(`${cs.color} sobre rgb(${bg.map(Math.round).join(',')}) · ${px}px · `
          + `${ratio.toFixed(2)}:1 (mínimo ${minimo}) · «${(el.textContent || '').trim().slice(0, 30)}»`);
      }
    }
    return [...new Set(malos)];
  });
}

// =============================================================
// SOLO DEL TFM
// =============================================================
test.describe('Confidencialidad', () => {
  /* Los valores reales que hay que vigilar NO viven en este archivo.
     Vivian, y ese era el fallo: este spec se publica en el repositorio, asi
     que escribir aqui el umbral de A para comprobar que no sale era
     publicarlo en el mismo gesto de protegerlo. Ahora vienen de
     herramientas/confidencial.local.json, que .gitignore deja fuera.

     Si el archivo no esta, estas pruebas FALLAN. No se saltan: una guarda que
     pasa sin mirar nada es peor que no tener guarda, porque ademas tranquiliza. */
  const RUTA_CONF = path.join(__dirname, '..', 'herramientas', 'confidencial.local.json');

  function patronesProhibidos() {
    expect(fs.existsSync(RUTA_CONF),
      'falta herramientas/confidencial.local.json: sin el no se vigila nada')
      .toBe(true);
    const lista = JSON.parse(fs.readFileSync(RUTA_CONF, 'utf8')).prohibido;
    expect(Array.isArray(lista) && lista.length > 0,
      'la lista de datos prohibidos esta vacia').toBe(true);
    return lista;
  }

  test('no aparece ningún umbral ni la conversión de la universidad', async ({ page }) => {
    await page.goto(TFM);
    const texto = await page.locator('body').innerText();

    /* La trampa que no se ve esta en la lista: ademas de los dos umbrales va
       la conversion ABSOLUTA de la categoria A. Por si sola parece inocente,
       pero el lift esta publicado, y dividir una por otro da la tasa de
       conversion global de la universidad, que es justo el dato que no puede
       salir. Se publica el lift o se publica la conversion de A, nunca los dos. */
    for (const { patron, que } of patronesProhibidos()) {
      expect(texto, `se ha colado ${que}`).not.toMatch(new RegExp(patron, 'i'));
    }

    // Y que el lift sí está: si desapareciera, esta prueba seguiría en verde
    // sin proteger nada, porque estaría comprobando una página vacía.
    expect(texto).toMatch(/×6,8/);
  });

  test('ni el generador ni esta prueba llevan escritos los valores reales', async () => {
    // La regresion del fallo que motivo este cambio. Los dos archivos se
    // publican; el dia que alguien vuelva a pegar un umbral aqui dentro para
    // "tenerlo a mano", esta linea lo ve.
    const publicos = {
      'herramientas/hacer-caso.py': fs.readFileSync(
        path.join(__dirname, '..', 'herramientas', 'hacer-caso.py'), 'utf8'),
      'pruebas/casos.spec.js': fs.readFileSync(__filename, 'utf8'),
    };
    for (const { patron, que } of patronesProhibidos()) {
      // Tres formas de que el dato acabe escrito en un archivo publico.
      // Los ejemplos van con un numero INVENTADO a proposito: escribir aqui
      // el de verdad para ilustrar el fallo seria volver a cometerlo, y esta
      // misma prueba se lee a si misma y lo cazaria.
      //   1. el valor de verdad          0,9999
      //   2. el patron copiado tal cual  0[,.]9999   <- asi estaba antes
      //   3. los digitos sueltos         9999
      const digitos = (patron.match(/\d{4,}/g) || []);
      for (const [nombre, texto] of Object.entries(publicos)) {
        expect(texto, `${nombre} lleva escrito ${que}`)
          .not.toMatch(new RegExp(patron, 'i'));
        expect(texto, `${nombre} lleva el patron de ${que} copiado tal cual`)
          .not.toContain(patron);
        for (const d of digitos) {
          expect(texto, `${nombre} lleva los digitos de ${que}`).not.toContain(d);
        }
      }
    }
  });

  test('el generador se niega a escribir si entra un dato prohibido', async () => {
    // La prueba de arriba mira el resultado; esta mira la red que hay debajo.
    // Sin ella, el día que alguien edite el JSON el único aviso llegaría
    // cuando alguien se acordara de pasar las pruebas.
    const gen = fs.readFileSync(
      path.join(__dirname, '..', 'herramientas', 'hacer-caso.py'), 'utf8');
    expect(gen, 'el generador ya no comprueba nada antes de escribir')
      .toContain('PROHIBIDO');

    // Y que la comprobación ocurre ANTES de escribir el archivo.
    const iCheck = gen.indexOf('fugas = [');
    const iEscribe = gen.indexOf('salida.write_text');
    expect(iCheck).toBeGreaterThan(0);
    expect(iCheck, 'se escribe el archivo antes de comprobar las fugas')
      .toBeLessThan(iEscribe);
  });

  test('el generador se planta si falta la lista de datos prohibidos', async () => {
    // Fallar cerrado. Si el archivo local no esta, hacer-caso.py no genera:
    // lo contrario seria seguir publicando con la guarda apagada.
    const gen = fs.readFileSync(
      path.join(__dirname, '..', 'herramientas', 'hacer-caso.py'), 'utf8');
    const iExiste = gen.indexOf('CONFIDENCIAL.exists()');
    const iCorta = gen.indexOf('raise SystemExit', iExiste);
    expect(iExiste, 'ya no se comprueba que la lista exista').toBeGreaterThan(0);
    expect(iCorta, 'falta la lista y aun así genera').toBeGreaterThan(iExiste);
  });

  test('la guarda se aplica a TODAS las páginas, no solo a la del TFM', async () => {
    // El día que un dato del CRM se cuele en otra página, esta es la única
    // línea que lo va a ver. Se comprueba que la comprobación vive dentro de
    // la función que hace cada página, no en un sitio que solo pisa una.
    const gen = fs.readFileSync(
      path.join(__dirname, '..', 'herramientas', 'hacer-caso.py'), 'utf8');
    const iFun = gen.indexOf('def hacer(');
    const iCheck = gen.indexOf('fugas = [');
    const iMain = gen.indexOf('def main(');
    expect(iFun).toBeGreaterThan(0);
    expect(iCheck > iFun && iCheck < iMain,
      'la comprobación de fugas no está dentro de hacer()').toBe(true);
  });

  test('no se enlaza la memoria ni nada de originales/', async ({ page }) => {
    await page.goto(TFM);
    const hrefs = await page.$$eval('a[href]', (as) => as.map((a) => a.getAttribute('href')));
    hrefs.forEach((h) => {
      expect(h, `${h} apunta a la carpeta que no se publica`).not.toMatch(/originales/i);
      expect(h, `${h} parece la memoria del TFM`).not.toMatch(/memoria|\.docx$/i);
    });
  });
});

// =============================================================
// COMPARTIDO POR LAS DOS
// =============================================================
for (const c of CASOS) {
  test.describe(`${c.nombre} · estructura`, () => {
    test('los rótulos y las etiquetas se leen: 4,5:1 mínimo', async ({ page }) => {
      // La regresión de B9. El gris de los rótulos (--bruma-tenue) estaba en
      // #6E747D y daba 4,15:1 sobre el fondo y 3,63:1 sobre el panel alto,
      // con textos de 10 a 14 px que son texto normal, no texto grande.
      await page.goto(c.ruta);
      await page.waitForTimeout(400);
      const malos = await textosConPocoContraste(page);
      expect(malos, 'textos por debajo del mínimo: ' + malos.join(' | '))
        .toEqual([]);
    });

    test('los apartados están, y en orden', async ({ page }) => {
      await page.goto(c.ruta);
      const ids = await page.$$eval('main section[id]', (ss) => ss.map((s) => s.id));
      expect(ids).toEqual(c.secciones);
      await expect(page.locator('.siguiente')).toBeVisible();
    });

    test('cada apartado tiene su gráfico, y no se repiten', async ({ page }) => {
      await page.goto(c.ruta);
      const svgs = page.locator('svg.grafico');
      // Un gráfico por apartado, menos el cierre. El número sale de la lista
      // de secciones del caso: no todos los trabajos tienen los mismos.
      const nGraficos = c.secciones.length - 1;
      await expect(svgs).toHaveCount(nGraficos);
      // Cinco dibujos distintos: copiar y pegar un apartado y olvidarse de
      // cambiar el gráfico deja dos secciones contando lo mismo.
      const huellas = await svgs.evaluateAll((els) => els.map((e) => e.innerHTML));
      expect(new Set(huellas).size, 'hay gráficos repetidos').toBe(nGraficos);
    });

    test('cada gráfico se puede leer sin verlo', async ({ page }) => {
      await page.goto(c.ruta);
      // El SVG va aria-hidden a propósito; quien no lo ve necesita el párrafo
      // que lo describe. Un dibujo sin equivalente en texto es un dato que
      // solo existe para quien puede mirarlo.
      const figuras = await page.$$eval('.caso__figura', (fs2) => fs2.map((f) => ({
        oculto: !!f.querySelector('svg.grafico[aria-hidden="true"]'),
        descripcion: (f.querySelector('.oculto') || {}).textContent || '',
        pie: (f.querySelector('.caso__pie') || {}).textContent || '',
      })));
      expect(figuras).toHaveLength(c.secciones.length - 1);
      figuras.forEach((f, i) => {
        expect(f.oculto, `el gráfico ${i + 1} no está marcado como decorativo`).toBe(true);
        expect(f.descripcion.trim().length,
          `el gráfico ${i + 1} no tiene descripción en texto`).toBeGreaterThan(60);
        expect(f.pie.trim().length, `el gráfico ${i + 1} no tiene pie`).toBeGreaterThan(10);
      });
    });

    test('las cifras del trabajo están en la página', async ({ page }) => {
      await page.goto(c.ruta);
      const texto = await page.locator('body').innerText();
      for (const cifra of c.cifras) {
        expect(texto, `falta la cifra ${cifra}`).toContain(cifra);
      }
    });

    test('el raíl usa anclas de verdad y todas existen', async ({ page }) => {
      await page.goto(c.ruta);
      const anclas = await page.$$eval('#rail [data-rail]',
        (as) => as.map((a) => a.getAttribute('href')));
      expect(anclas.length).toBe(c.secciones.length - 1);
      for (const a of anclas) {
        expect(a, 'el raíl no usa anclas reales').toMatch(/^#/);
        await expect(page.locator(a), `${a} no lleva a ninguna sección`).toHaveCount(1);
      }
    });

    test('el raíl marca el apartado en el que estás, y solo uno', async ({ page }) => {
      await page.setViewportSize(ESCRITORIO);
      await page.goto(c.ruta);
      const cuarto = c.secciones[3];
      await page.locator(`#${cuarto}`).scrollIntoViewIfNeeded();
      await page.waitForTimeout(800);
      await expect(page.locator(`#rail [href="#${cuarto}"]`))
        .toHaveAttribute('aria-current', 'true');
      // Dos marcados es peor que ninguno: el lector deja de fiarse.
      expect(await page.locator('#rail [aria-current="true"]').count()).toBe(1);
    });

    test('se lee entera sin JavaScript', async ({ browser }) => {
      // El caso completo está en el HTML. El script solo marca en qué apartado
      // vas; si falla, no se pierde ni un dato.
      const ctx = await browser.newContext({ javaScriptEnabled: false });
      const page = await ctx.newPage();
      await page.goto(c.ruta);
      await expect(page.locator('main section[id]')).toHaveCount(c.secciones.length);
      await expect(page.locator('svg.grafico')).toHaveCount(c.secciones.length - 1);
      await expect(page.locator('.caso-portada__titulo')).toBeVisible();
      await page.locator(`#rail [href="#${c.secciones[4]}"]`).click();
      expect(await page.evaluate(() => location.hash)).toBe('#' + c.secciones[4]);
      await ctx.close();
    });

    test('el botón de parar el movimiento está y funciona', async ({ page }) => {
      await page.goto(c.ruta);
      const boton = page.locator('#quieto');
      await expect(boton).toBeVisible();
      await boton.click();
      await expect(page.locator('html')).toHaveClass(/sin-movimiento/);
      await expect(page.locator('#reanudar')).toBeVisible();
      await page.locator('#reanudar').click();
      await expect(page.locator('html')).not.toHaveClass(/sin-movimiento/);
    });

    test('con movimiento reducido no se anima nada', async ({ page }) => {
      await irConMovimientoReducido(page, c.ruta);
      /* El div del anillo SÍ está en el HTML —es el mismo de todo el sitio—;
         lo que no pasa es que se encienda. La versión anterior de esta prueba
         exigía que no existiera, y pasaba por el motivo equivocado: en estas
         páginas no existía porque faltaba, que era justo el fallo. */
      await page.mouse.move(500, 400);
      await page.waitForTimeout(400);
      const anillo = page.locator('#nodo-cursor');
      await expect(anillo).toHaveCount(1);
      await expect(anillo).not.toHaveClass(/esta-visible/);
      expect(await anillo.evaluate((e) => Number(getComputedStyle(e).opacity)))
        .toBe(0);
      await expect(page.locator('#quieto')).toBeDisabled();
    });

    test('el cursor es EL MISMO que en el portfolio', async ({ page }) => {
      /* Lo que notó Pedro: al abrir un trabajo, el ratón dejaba de comportarse
         como en la página principal. La causa no era que hubiera dos sistemas
         de cursor, sino que aquí faltaba el div donde plantilla.js dibuja el
         anillo, así que sencillamente no había ninguno.

         Se compara contra el del portfolio en vez de contra números escritos
         aquí: si mañana cambia el anillo, cambia en los dos o esto salta. */
      const leer = async (ruta) => {
        await page.goto(ruta);
        await page.mouse.move(500, 400);
        await page.waitForTimeout(400);
        return page.evaluate(() => {
          const a = document.getElementById('nodo-cursor');
          if (!a) return null;
          const s = getComputedStyle(a);
          return {
            medidas: s.width + '/' + s.height,
            borde: s.borderTopWidth + ' ' + s.borderTopColor,
            radio: s.borderRadius,
            transicion: s.transitionDuration,
            zeta: s.zIndex,
            posicion: s.position,
            // Que no capture clics es parte del comportamiento, no un detalle.
            eventos: s.pointerEvents,
          };
        });
      };

      const enPortfolio = await leer('/index.html');
      const enTrabajo = await leer(c.ruta);
      expect(enPortfolio, 'el portfolio no tiene anillo de cursor').not.toBeNull();
      expect(enTrabajo, 'esta página no tiene anillo de cursor: falta #nodo-cursor')
        .not.toBeNull();
      expect(enTrabajo).toEqual(enPortfolio);
      expect(enTrabajo.eventos).toBe('none');
    });

    test('la llamada flotante también está, y es la misma', async ({ page }) => {
      // Sale de contenido-plantilla.json, no está escrita en el generador:
      // el mismo texto en tres archivos acaba diciendo tres cosas.
      // Se compara el marcado completo, no unas clases concretas: si aquí se
      // escribieran los selectores a mano, el día que las dos versiones usen
      // etiquetas distintas la prueba seguiría en verde comparando nada.
      const leer = async (ruta) => {
        await page.goto(ruta);
        return page.locator('#flotante').evaluate((e) => ({
          href: e.getAttribute('href'),
          etiqueta: e.getAttribute('aria-label'),
          texto: e.querySelector('.flotante__texto').textContent.replace(/\s+/g, ' ').trim(),
          estructura: e.innerHTML.replace(/\s+/g, ' ').trim(),
        }));
      };
      const enPortfolio = await leer('/index.html');
      const aqui = await leer(c.ruta);
      expect(enPortfolio.texto.length, 'el flotante del portfolio está vacío')
        .toBeGreaterThan(10);
      expect(aqui).toEqual(enPortfolio);
    });

    test('ningún botón lleva al cuaderno de la web antigua', async ({ page }) => {
      await page.goto(c.ruta);
      const hrefs = await page.$$eval('a[href]', (as) => as.map((a) => a.getAttribute('href')));
      hrefs.forEach((h) => {
        expect(h, `${h} sigue enlazando el cuaderno viejo`)
          .not.toMatch(/prediccion-ventas-videojuegos|ganar-a-la-casa-de-apuestas/);
      });
    });

    test('el botón de GitHub no se pinta mientras no haya URL', async ({ page }) => {
      await page.goto(c.ruta);
      // PENDIENTE es la convención del proyecto. Un botón que lleva a un
      // repositorio que no existe, delante de un reclutador, es peor que no
      // tener botón. La estructura está lista: se pone la URL y aparece.
      const hrefs = await page.$$eval('.caso--cierre a[href]',
        (as) => as.map((a) => a.getAttribute('href')));
      hrefs.forEach((h) => {
        expect(h, 'hay un enlace con el marcador sin rellenar').not.toBe('PENDIENTE');
      });
      const texto = await page.locator('.caso--cierre').innerText();
      expect(texto, 'se ve la palabra PENDIENTE en la página').not.toContain('PENDIENTE');
    });

    test('se puede volver al portfolio por tres sitios', async ({ page }) => {
      await page.goto(c.ruta);
      for (const sitio of ['.volver', '.barra__cta', '.barra__marca']) {
        const href = await page.locator(sitio).getAttribute('href');
        expect(href, `${sitio} no vuelve al portfolio`).toContain('index.html');
      }
    });

    test('no hay errores de consola ni peticiones fallidas', async ({ page }) => {
      const fallos = [];
      page.on('console', (m) => { if (m.type() === 'error') fallos.push(m.text()); });
      page.on('pageerror', (e) => fallos.push(String(e)));
      page.on('response', (r) => { if (r.status() >= 400) fallos.push(`${r.status()} ${r.url()}`); });
      await page.goto(c.ruta);
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 600) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 60));
        }
      });
      await page.waitForTimeout(600);
      expect(fallos).toEqual([]);
    });

    for (const ancho of [375, 430, 768, 1024, 1440]) {
      test(`a ${ancho}px no se desborda a lo ancho`, async ({ page }) => {
        await page.setViewportSize({ width: ancho, height: 900 });
        await page.goto(c.ruta);
        // Arrastrando, no midiendo: scrollWidth miente cuando algo está
        // recortado, y aquí hay un raíl con desplazamiento propio.
        const movido = await page.evaluate(() => {
          window.scrollTo(9999, 0);
          const x = window.scrollX;
          window.scrollTo(0, 0);
          return x;
        });
        expect(movido, 'la página se puede arrastrar a la derecha').toBe(0);
      });
    }

    test('en móvil el raíl se puede recorrer entero', async ({ page }) => {
      await page.setViewportSize(MOVIL);
      await page.goto(c.ruta);
      // Poder desplazar no es poder llegar. Es el mismo fallo que tuvo la
      // barra de index.html con justify-content:flex-end.
      const alcanzable = await page.evaluate(() => {
        const caja = document.querySelector('.rail__caja');
        caja.scrollLeft = caja.scrollWidth;
        const ultimo = caja.lastElementChild.getBoundingClientRect();
        return ultimo.left >= -1 && ultimo.right <= window.innerWidth + 1;
      });
      expect(alcanzable, 'el último apartado del raíl no se puede alcanzar').toBe(true);
    });
  });
}

// =============================================================
// SOLO DE LAS QUE LLEVAN VÍDEO
// =============================================================
for (const c of CASOS.filter((x) => x.video)) {
  test.describe(`${c.nombre} · portada con vídeo`, () => {
    test('es el vídeo de Pedro, en bucle, mudo y en línea', async ({ page }) => {
      await page.goto(c.ruta);
      const v = page.locator('#portada-video');
      await expect(v).toHaveCount(1);
      const at = await v.evaluate((e) => ({
        loop: e.loop,
        muted: e.muted,
        enLinea: e.hasAttribute('playsinline'),
        // autoplay NO va en el HTML a propósito: lo enciende plantilla.js, y
        // por eso obedece al botón de parar el movimiento.
        autoplayEnHtml: e.hasAttribute('autoplay'),
        preload: e.getAttribute('preload'),
        poster: e.getAttribute('poster'),
        src: e.getAttribute('data-src'),
      }));
      expect(at.loop, 'el vídeo no se repite').toBe(true);
      expect(at.muted, 'un vídeo con sonido no se reproduce solo').toBe(true);
      expect(at.enLinea, 'sin playsinline, iOS lo abre a pantalla completa').toBe(true);
      expect(at.autoplayEnHtml,
        'con autoplay en el HTML se salta el botón de parar el movimiento').toBe(false);
      expect(at.preload).toBe('none');
      expect(at.poster).toMatch(/poster\.jpg$/);
      expect(at.src).toMatch(/\.mp4$/);
  });

  test('no pesa como un vídeo sin preparar', async () => {
    // El original son 60 MB. Esta página se abre desde el móvil de alguien
    // que está en el metro, y ese archivo se descarga entero.
    const st = fs.statSync(path.join(__dirname, '..', 'medios', 'video', `${c.video}.mp4`));
    expect(st.size, 'el vídeo de portada pesa demasiado').toBeLessThan(3 * 1024 * 1024);
    const poster = fs.statSync(
      path.join(__dirname, '..', 'medios', 'video', `${c.video}-poster.jpg`));
    expect(poster.size).toBeLessThan(400 * 1024);
  });

  test('arranca y da fotogramas de verdad', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto(c.ruta);
    const v = page.locator('#portada-video');
    // currentTime avanzando es la prueba de que se está reproduciendo; que el
    // elemento exista no dice nada.
    await expect.poll(async () => v.evaluate((e) => e.currentTime),
      { message: 'el vídeo no llega a reproducirse', timeout: 12000 }).toBeGreaterThan(0.2);
    // Y solo entonces se enseña: entre que llega el archivo y sale el primer
    // fotograma, un <video> vacío es un rectángulo negro sobre el póster.
    await expect(v).toHaveClass(/esta-encendido/);
  });

  test('el mismo botón lo para, y al reanudar sigue', async ({ page }) => {
    await page.goto(c.ruta);
    const v = page.locator('#portada-video');
    await expect.poll(async () => v.evaluate((e) => e.currentTime),
      { timeout: 12000 }).toBeGreaterThan(0.2);

    // El botón de parar está en el pie, así que al pulsarlo la página baja y
    // el vídeo se queda fuera de pantalla. Eso importa para lo de después.
    await page.locator('#quieto').click();
    await page.waitForTimeout(400);
    expect(await v.evaluate((e) => e.paused), 'sigue corriendo con el movimiento parado')
      .toBe(true);

    const donde = await v.evaluate((e) => e.currentTime);
    await page.locator('#reanudar').click();
    await page.waitForTimeout(300);

    // Reanudar NO tiene que arrancarlo estando fuera de pantalla: eso era
    // gastar descarga y decodificación en algo que nadie ve. Se comprueba
    // aparte, en el grupo de regresiones de más abajo.
    await page.locator('.portada, #portada-video').first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(700);

    // Ya a la vista: vuelve, y sigue donde estaba en vez de empezar de cero.
    expect(await v.evaluate((e) => e.paused),
      'no vuelve al reanudar ni volviendo a la portada').toBe(false);
    expect(await v.evaluate((e) => e.currentTime),
      'al reanudar ha vuelto al principio').toBeGreaterThanOrEqual(donde);
  });

  test('reanudar no arranca el vídeo si está fuera de pantalla', async ({ page }) => {
    // La regresión de B10. El observador de intersección solo avisa cuando la
    // visibilidad CAMBIA; desde el pie no cambiaba nada, así que reanudar
    // ponía a reproducir un vídeo tres pantallas más arriba.
    await page.goto(c.ruta);
    const v = page.locator('#portada-video');
    await expect.poll(async () => v.evaluate((e) => e.currentTime),
      { timeout: 12000 }).toBeGreaterThan(0.2);

    await page.locator('#quieto').click();
    await page.waitForTimeout(400);
    await page.locator('#reanudar').click();
    await page.waitForTimeout(700);

    const fuera = await v.evaluate((e) => {
      const r = e.getBoundingClientRect();
      return r.bottom <= 0 || r.top >= window.innerHeight;
    });
    expect(fuera, 'el vídeo no llegó a quedarse fuera de pantalla: la prueba no vale')
      .toBe(true);
    expect(await v.evaluate((e) => e.paused),
      'reanudar ha puesto a reproducir un vídeo que nadie está viendo').toBe(true);
  });

  test('con la pausa guardada, el vídeo no se pide siquiera', async ({ page }) => {
    // La otra regresión: el bloque del vídeo corría ANTES de que el
    // interruptor leyera localStorage, así que con el movimiento parado y
    // guardado el archivo se descargaba igual y se paraba un instante
    // después. preload="none" y el data-src existen justo para evitar eso.
    const pedidos = [];
    page.on('request', (r) => { if (/\.mp4/.test(r.url())) pedidos.push(r.url()); });
    await page.addInitScript(() => {
      try { window.localStorage.setItem('plantilla-sin-movimiento', '1'); } catch (e) { /* */ }
    });
    await page.goto(c.ruta);
    await page.waitForTimeout(1500);

    expect(await page.locator('#portada-video').evaluate((e) => e.paused),
      'el vídeo corre pese a la pausa guardada').toBe(true);
    expect(pedidos, `se ha descargado ${c.video}.mp4 con el movimiento parado`)
      .toEqual([]);
  });

  test('con movimiento reducido no se descarga siquiera', async ({ page }) => {
    const pedidos = [];
    page.on('request', (r) => { if (/\.mp4/.test(r.url())) pedidos.push(r.url()); });
    await irConMovimientoReducido(page, c.ruta);
    await page.waitForTimeout(1500);
    // preload="none" + el src en data-src: con la preferencia puesta, el mega
    // del vídeo no viaja. Lo que se ve es el póster.
    expect(pedidos, 'se descarga el vídeo con movimiento reducido').toEqual([]);
    await expect(page.locator('.relieve__quieta')).toBeVisible();
  });

  test('la portada no se queda negra con el vídeo parado', async ({ page }) => {
    await page.goto(c.ruta);
    // El póster va debajo y no se quita nunca. Sin él, parar el movimiento
    // deja la primera pantalla del trabajo en negro.
    const img = page.locator('.relieve__quieta');
    await expect(img).toBeVisible();
    expect(await img.evaluate((e) => e.naturalWidth),
      'el póster no carga').toBeGreaterThan(0);
  });

  test('el texto va sobre un panel que lo hace legible', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto(c.ruta);
    const panel = page.locator('.cristal');
    await expect(panel).toHaveCount(1);
    // El respaldo importa: donde no exista backdrop-filter, el panel tiene
    // que seguir siendo opaco de sobra para leer encima.
    const fondo = await panel.evaluate((e) => getComputedStyle(e).backgroundColor);
    const alfa = Number((fondo.match(/[\d.]+\)$/) || ['1)'])[0].replace(')', ''));
    expect(alfa, 'el panel es demasiado transparente').toBeGreaterThan(0.35);
  });

  test('el vídeo es fondo, no protagonista', async ({ page }) => {
    await page.goto(c.ruta);
    // Sin tratar, un plano de dos monitores encendidos es lo más luminoso de
    // toda la web y se lleva por delante la identidad de la página.
    const f = await page.locator('#portada-video').evaluate((e) => getComputedStyle(e).filter);
    expect(f, 'el vídeo va sin atenuar').toMatch(/brightness/);
    await expect(page.locator('.relieve__velo')).toHaveCount(1);
  });
  });
}

// =============================================================
// SOLO DE LIPTON · el visor del informe
// =============================================================
test.describe('El informe de Lipton', () => {
  const LIPTON = '/trabajos/lipton.html';
  const PDF = path.join(__dirname, '..', 'trabajos', 'lipton-summer-shake-up.pdf');

  test('es el PDF de verdad, y está dentro del proyecto', async ({ page }) => {
    // Ni un enlace externo, ni una captura, ni un marcador: el documento real.
    expect(fs.existsSync(PDF), 'falta trabajos/lipton-summer-shake-up.pdf').toBe(true);
    await page.goto(LIPTON);
    const href = await page.locator('.visor__fachada').getAttribute('href');
    expect(href).toBe('lipton-summer-shake-up.pdf');
    // Relativo, no absoluto ni de otro dominio: la página tiene que seguir
    // funcionando esté donde esté el sitio.
    expect(href).not.toMatch(/^https?:|^\/\//);
  });

  test('las páginas y el peso que enseña son los del archivo', async ({ page }) => {
    /* Esto es lo que impide que la página mienta. Las dos cifras las escribe
       herramientas/hacer-informe.py leyendo el PDF; esta prueba las vuelve a
       leer del archivo y las compara con lo que hay pintado. El día que
       alguien cambie el PDF y se olvide de regenerar, salta aquí y no delante
       de un reclutador que se descarga 8 MB esperando otra cosa. */
    const bytes = fs.statSync(PDF).size;
    const crudo = fs.readFileSync(PDF, 'latin1');
    const paginas = (crudo.match(/\/Type\s*\/Page[^s]/g) || []).length;
    expect(paginas, 'no he sabido contar las páginas del PDF').toBeGreaterThan(0);

    const mb = (bytes / (1024 * 1024)).toFixed(1).replace('.', ',');

    await page.goto(LIPTON);
    const meta = await page.locator('.visor__meta').innerText();
    expect(meta, `la barra dice "${meta}" y el PDF tiene ${paginas} páginas`)
      .toContain(String(paginas));
    expect(meta, `la barra dice "${meta}" y el PDF pesa ${mb} MB`).toContain(mb);

    // Y el peso que va junto al botón de descarga, el mismo.
    const pesos = await page.$$eval('.visor__peso', (els) => els.map((e) => e.textContent.trim()));
    pesos.forEach((p) => expect(p).toContain(mb));
  });

  test('el PDF NO se descarga hasta que alguien lo pide', async ({ page }) => {
    // Son 8,5 MB. Puesto en un iframe de entrada, se los lleva todo el que
    // pase por la página, lo vaya a leer o no.
    const pedidos = [];
    page.on('request', (r) => { if (/\.pdf/i.test(r.url())) pedidos.push(r.url()); });
    await page.goto(LIPTON);
    await page.locator('.visor').scrollIntoViewIfNeeded();
    await page.waitForTimeout(1200);
    expect(pedidos, 'el PDF se descarga sin que nadie lo haya pedido').toEqual([]);
    // Lo que sí se ve es la portada de su primera página.
    const portada = page.locator('.visor__portada');
    await expect(portada).toBeVisible();
    expect(await portada.evaluate((e) => e.naturalWidth),
      'la portada del informe no carga').toBeGreaterThan(0);
  });

  test('al pulsarlo se abre aquí mismo, en escritorio', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto(LIPTON);
    await page.locator('.visor').scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);

    await page.locator('.visor__fachada').click();
    const marco = page.locator('.visor__marco');
    await expect(marco).toHaveCount(1);
    await expect(marco).toHaveAttribute('src', /lipton-summer-shake-up\.pdf#view=FitH$/);
    // Con título: un <iframe> sin nombre es un agujero para quien navega con
    // lector de pantalla.
    const titulo = await marco.getAttribute('title');
    expect(titulo, 'el visor no dice qué documento es').toContain('Lipton');
    expect(await marco.evaluate((e) => e.getBoundingClientRect().height),
      'el visor sale sin altura').toBeGreaterThan(300);
  });

  test('en móvil NO se incrusta: abre el PDF en su pestaña', async ({ page }) => {
    await page.setViewportSize(MOVIL);
    await page.goto(LIPTON);
    await page.locator('.visor').scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    // Un visor de PDF embebido en un móvil se desplaza dentro de algo que ya
    // se desplaza. Ahí el enlace hace lo que dice.
    const f = page.locator('.visor__fachada');
    await expect(f).toHaveAttribute('target', '_blank');
    await expect(f).toHaveAttribute('rel', /noopener/);
    await expect(page.locator('.visor__marco')).toHaveCount(0);
  });

  test('el botón de descarga descarga el archivo, no navega a otra web', async ({ page }) => {
    await page.goto(LIPTON);
    const boton = page.locator('.visor__accion[download]');
    await expect(boton).toHaveCount(1);
    await expect(boton).toHaveAttribute('download', 'lipton-summer-shake-up.pdf');
    await expect(boton).toHaveAttribute('href', 'lipton-summer-shake-up.pdf');
    await expect(boton).toContainText(/descargar/i);

    // Y que el servidor lo sirve de verdad, con el tipo correcto.
    const r = await page.request.get('/trabajos/lipton-summer-shake-up.pdf');
    expect(r.status()).toBe(200);
    expect(r.headers()['content-type']).toContain('pdf');
  });

  test('se puede abrir en grande', async ({ page }) => {
    await page.goto(LIPTON);
    const abrir = page.locator('.visor__accion--fin');
    await expect(abrir).toHaveAttribute('href', 'lipton-summer-shake-up.pdf');
    await expect(abrir).toHaveAttribute('target', '_blank');
    await expect(abrir).toContainText(/pantalla completa/i);
  });

  test('funciona con el teclado y se anuncia bien', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto(LIPTON);
    // Las tres acciones son enlaces de verdad, así que entran en el recorrido
    // del tabulador sin que haya que hacer nada.
    const enfocables = await page.$$eval(
      '.visor a', (as) => as.map((a) => a.tagName + ':' + (a.getAttribute('href') || '')));
    expect(enfocables.length, 'el visor no tiene enlaces reales').toBeGreaterThanOrEqual(3);
    enfocables.forEach((x) => expect(x.startsWith('A:')).toBe(true));

    await page.locator('.visor__fachada').focus();
    expect(await page.evaluate(() =>
      document.activeElement.classList.contains('visor__fachada'))).toBe(true);

    // La nota del lector de pantalla dice la verdad, y la verdad depende del
    // ancho: aquí se abre en la propia página.
    const nota = await page.locator('[data-visor-nota]').textContent();
    expect(nota).toMatch(/aquí mismo/);

    // La portada lleva descripción: es la cubierta del informe, no un adorno.
    const alt = await page.locator('.visor__portada').getAttribute('alt');
    expect(alt.length, 'la portada del informe no está descrita').toBeGreaterThan(30);
  });

  test('sin JavaScript el informe sigue siendo accesible', async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto(LIPTON);
    // Los tres son <a> con href real, así que el bloque entero funciona.
    await expect(page.locator('.visor__fachada')).toHaveAttribute(
      'href', 'lipton-summer-shake-up.pdf');
    await expect(page.locator('.visor__accion[download]')).toHaveCount(1);
    await expect(page.locator('.visor__portada')).toBeVisible();
    await ctx.close();
  });

  for (const ancho of [375, 430, 768, 1024, 1440]) {
    test(`a ${ancho}px el informe cabe y se ve entero`, async ({ page }) => {
      await page.setViewportSize({ width: ancho, height: 900 });
      await page.goto(LIPTON);
      await page.locator('.visor').scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
      const m = await page.locator('.visor').evaluate((v) => {
        const f = v.querySelector('.visor__fachada').getBoundingClientRect();
        const c = v.getBoundingClientRect();
        return {
          dentro: f.left >= c.left - 1 && f.right <= c.right + 1,
          ancho: f.width,
          aire: (c.width - f.width) / 2,
        };
      });
      expect(m.dentro, 'el documento se sale de su marco').toBe(true);
      expect(m.ancho, 'el documento sale demasiado pequeño').toBeGreaterThan(240);
      expect(m.aire, 'el documento no tiene aire alrededor').toBeGreaterThan(8);
    });
  }
});

// =============================================================
// LOS CORTES DE VIDEO ENTRE APARTADOS
// =============================================================
//
// Un separador ambiental tiene dos obligaciones que no son de estetica:
// no descargarse hasta que hace falta, y decir de donde sale el metraje.
// Las dos se comprueban aqui sobre la pagina servida, no sobre el JSON.
test.describe('Cortes de vídeo · Opponent Pool Self-Play', () => {
  const RUTA = '/trabajos/rlgym-selfplay-pool.html';

  test('son dos, y ninguno se descarga al cargar la página', async ({ page }) => {
    const mp4 = [];
    page.on('request', (r) => { if (r.url().endsWith('.mp4')) mp4.push(r.url().split('/').pop()); });
    await page.goto(RUTA);
    await page.waitForTimeout(1800);
    await expect(page.locator('.corte')).toHaveCount(2);
    // La portada SI se pide, porque se ve al cargar. Los cortes NO.
    expect(mp4.filter((n) => n.includes('corte')),
      'un corte se ha descargado sin que nadie baje hasta él').toEqual([]);
  });

  test('cada corte dice que es contexto visual y no material del experimento',
    async ({ page }) => {
      await page.goto(RUTA);
      const notas = await page.$$eval('.corte__nota', (ns) => ns.map((n) => n.textContent));
      expect(notas).toHaveLength(2);
      for (const n of notas) {
        expect(n.toLowerCase()).toContain('contexto visual');
        expect(n.toLowerCase()).toContain('no son grabaciones del experimento');
      }
    });

  test('mudos, en bucle, sin controles y sin deformar', async ({ page }) => {
    await page.goto(RUTA);
    const v = await page.$$eval('.corte__video', (ns) => ns.map((x) => ({
      mudo: x.muted, bucle: x.loop, enLinea: x.hasAttribute('playsinline'),
      controles: x.hasAttribute('controls'),
      ajuste: getComputedStyle(x).objectFit,
      poster: !!x.getAttribute('poster'),
      srcDeEntrada: x.getAttribute('src'),
    })));
    expect(v).toHaveLength(2);
    for (const x of v) {
      expect(x.mudo).toBe(true);
      expect(x.bucle).toBe(true);
      expect(x.enLinea).toBe(true);
      expect(x.controles, 'un corte no lleva controles: es ambiente').toBe(false);
      expect(x.ajuste).toBe('cover');
      expect(x.poster, 'sin póster la banda es un rectángulo negro').toBe(true);
      expect(x.srcDeEntrada, 'el src lo pone el script, no el HTML').toBeNull();
    }
  });

  test('con movimiento reducido no se pide ni un vídeo y queda el póster',
    async ({ page }) => {
      await page.emulateMedia({ reducedMotion: 'reduce' });
      const mp4 = [];
      page.on('request', (r) => { if (r.url().endsWith('.mp4')) mp4.push(r.url()); });
      await page.goto(RUTA);
      expect(await page.evaluate(() =>
        matchMedia('(prefers-reduced-motion: reduce)').matches),
      'la emulación no se aplicó: la prueba no probaría nada').toBe(true);
      await page.evaluate(async () => {
        for (let y = 0; y < 12000; y += 700) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 60));
        }
      });
      await page.waitForTimeout(900);
      expect(mp4, 'con movimiento reducido no debe viajar ningún vídeo').toEqual([]);
      const posters = await page.$$eval('.corte__quieta',
        (ns) => ns.map((i) => i.complete && i.naturalWidth > 0));
      expect(posters).toEqual([true, true]);
    });

  test('no desbordan a lo ancho en ningún tamaño', async ({ page }) => {
    for (const w of [390, 768, 1024, 1440]) {
      await page.setViewportSize({ width: w, height: 900 });
      await page.goto(RUTA);
      const desb = await page.evaluate(async () => {
        window.scrollTo(9999, 0);
        await new Promise((r) => requestAnimationFrame(r));
        const x = window.scrollX; window.scrollTo(0, 0); return x;
      });
      expect(desb, `desborde a ${w}px`).toBe(0);
    }
  });
});

// =============================================================
// EL PROYECTO ES UN PORTFOLIO, NO UNA WEB DE CANDIDATURA
// =============================================================
test.describe('Ya no queda nada de la campaña', () => {
  const PAGINAS = ['/', '/trabajos/tfm-lead-scoring.html', '/trabajos/videojuegos.html',
                   '/trabajos/apuestas.html', '/trabajos/lipton.html'];

  for (const ruta of PAGINAS) {
    test(`${ruta} no arrastra la lógica de candidatura`, async ({ page }) => {
      /* El proyecto empezó siendo una web para mandar a cinco empresas: un
         vídeo de Loom de 90 segundos, un enlace de respaldo por si el
         reproductor estaba bloqueado, y una portada que saludaba por el
         nombre de la empresa según el ?e= de la URL. Ese concepto se
         abandonó el 01/09/2026. Esta prueba existe para que no vuelva por
         la puerta de atrás en un copiar y pegar. */
      await page.goto(ruta);
      const html = await page.content();
      for (const resto of ['VIDEO_ID', 'ENLACE_ALTERNATIVO', 'loom.com',
                           'Candidatura espontánea', '?e=merkle']) {
        expect(html, `queda "${resto}", que era de la web de candidatura`)
          .not.toContain(resto);
      }
      // Y ningún enlace a las páginas que se fueron con ella.
      const hrefs = await page.$$eval('a[href]', (as) => as.map((a) => a.getAttribute('href')));
      hrefs.forEach((h) => {
        expect(h, `${h} lleva a una página que ya no existe`)
          .not.toMatch(/version-clara|version-corta|version-larga|tech\.html|prediccion-ventas-videojuegos|ganar-a-la-casa-de-apuestas/);
      });
    });
  }

  test('la portada del sitio es el portfolio', async ({ page }) => {
    // index.html ya no es la web de la campaña: es el portfolio, servido en
    // la raíz. Es lo que hace que el enlace del CV sea el dominio a secas y
    // no dominio.com/plantilla.html.
    await page.goto('/');
    await expect(page.locator('#saludo')).toHaveCount(1);
    await expect(page.locator('#mapa-lienzo, #mapa canvas')).not.toHaveCount(0);
    await expect(page.locator('.obra')).toHaveCount(7);
    await expect(page.locator('#contacto')).toHaveCount(1);
  });

  test('el empaquetado ya no depende de tener un vídeo grabado', async () => {
    /* Durante semanas, no tener grabado el Loom impedía generar el paquete
       entero. Era una herencia de un objetivo que ya no existe, y dejaba el
       portfolio sin poder probarse en Netlify por algo que no le afecta. */
    const pub = fs.readFileSync(
      path.join(__dirname, '..', 'herramientas', 'preparar-publicacion.py'), 'utf8');
    expect(pub, 'el portfolio no es la página que se publica').toContain('"index.html"');
    expect(pub, 'vuelve a exigir el vídeo de Loom').not.toMatch(/MARCADORES[\s\S]{0,400}VIDEO_ID/);
    expect(pub, 'vuelve a exigir el enlace de respaldo')
      .not.toMatch(/MARCADORES[\s\S]{0,400}ENLACE_ALTERNATIVO/);
    // Y la CSP tiene que dejar pasar lo que el portfolio necesita: si falta
    // media-src, los tres vídeos se bloquean en producción sin decir nada.
    expect(pub, 'la CSP no permite los vídeos').toContain("media-src 'self'");
    expect(pub, 'la CSP no permite el visor del PDF').toContain("frame-src 'self'");
    expect(pub, 'la política de permisos bloquearía la reproducción')
      .toContain('autoplay=(self)');
  });
});

test.describe('Visores de documento · cabeceras de producción', () => {
  /* La regresion del visor que se veia bien en local y salia "refused to
     connect" en produccion.

     La causa no estaba en el JavaScript: estaba en que la regla /* del
     _headers mandaba X-Frame-Options: DENY, y esa cabecera la heredaba
     tambien el PDF. DENY prohibe empotrar hasta desde el MISMO origen, asi
     que el navegador se negaba a pintar el <iframe> del visor.

     Estas pruebas solo valen porque servidor.js manda ya las cabeceras
     comunes de verdad, sacadas del generador de publicacion. Mientras no las
     mandaba, la suite aprobaba el iframe sin enterarse de nada. */
  const INFORMES = [
    ['TFM', '/trabajos/tfm-presentacion.pdf'],
    ['Videojuegos', '/trabajos/videojuegos-presentacion.pdf'],
    ['Deep learning', '/trabajos/deep-learning-presentacion.pdf'],
    ['Letterboxd', '/trabajos/letterboxd-presentacion.pdf'],
    ['Lipton', '/trabajos/lipton-summer-shake-up.pdf'],
    ['Apuestas', '/trabajos/apuestas-presentacion.pdf'],
  ];

  for (const [nombre, doc] of INFORMES) {
    test(`el informe de ${nombre} se deja incrustar desde el propio sitio`, async ({ request }) => {
      const r = await request.get(doc);
      expect(r.status(), `${doc} no se sirve`).toBe(200);
      expect(r.headers()['content-type']).toContain('application/pdf');
      // Se exige el valor exacto, no solo "que no sea DENY": si el servidor
      // no mandara ninguna cabecera, la cadena vacía tampoco es DENY y la
      // prueba pasaría sin comprobar nada.
      const xfo = (r.headers()['x-frame-options'] || '(ninguna)').trim().toUpperCase();
      expect(xfo, `${doc} viaja con ${xfo}: con DENY el visor se rompe en producción`)
        .toBe('SAMEORIGIN');
    });
  }

  test('las páginas HTML siguen sin poder empotrarse', async () => {
    // Aflojar X-Frame-Options no puede aflojar las paginas. Su proteccion es
    // frame-ancestors 'none' en su propia CSP, que es la directiva moderna y
    // gana sobre X-Frame-Options: prohibe empotrarlas incluso desde el mismo
    // origen. Si alguien la quita, esto salta.
    const pub = fs.readFileSync(
      path.join(__dirname, '..', 'herramientas', 'preparar-publicacion.py'), 'utf8');
    expect(pub, 'las páginas ya no prohíben ser empotradas')
      .toContain("frame-ancestors 'none'");
    expect(pub, 'X-Frame-Options vuelve a estar en DENY para todo el sitio')
      .not.toMatch(/["']X-Frame-Options:\s*DENY["']/);
  });
});

test.describe('Entra desde el portfolio', () => {
  test('las dos fichas llevan a su página de caso', async ({ page }) => {
    await page.goto('/index.html');
    const destinos = {
      'obra-tfm': 'trabajos/tfm-lead-scoring.html',
      'obra-videojuegos': 'trabajos/videojuegos.html',
    };
    for (const [id, href] of Object.entries(destinos)) {
      const ficha = page.locator('#' + id);
      await expect(ficha).not.toHaveClass(/obra--sin-destino/);
      await expect(ficha.locator('.obra__ir')).toHaveAttribute('href', href);
    }
  });
});

// =============================================================
// QUE SE LEA LO QUE PONE
// =============================================================
//
// Pedro mandó una captura: en los gráficos «se cortan cifras o letras y no se
// entiende lo que pone». Eran dos fallos distintos, y ninguno de los dos lo
// habría visto una prueba que mirase el HTML.
//
// 1. El rótulo se salía del viewBox. Un SVG recorta por su viewBox y no avisa:
//    donde ponía «títulos con ventas» se leía «títu».
// 2. La letra se pintaba minúscula. El texto de un SVG con viewBox se mide en
//    unidades del viewBox, así que su tamaño en pantalla es «lo declarado por
//    la escala del dibujo» — y esa escala era 0,78 en un monitor y 0,45 en un
//    móvil. El rótulo se leía a 5,3px.
//
// Las dos se comprueban igual: preguntándole al navegador dónde ha pintado
// cada texto. getBBox() da la caja real de cada uno, ya con la tipografía
// cargada, que es la única medida que no depende de lo que creamos nosotros.
//
// Y se comprueba en varios anchos a propósito: ui/trabajo.css cambia --g por
// tramos, así que un dibujo que cabe a 1440 puede no caber a 480.

const ANCHOS_GRAFICO = [1440, 1180, 1000, 900, 899, 768, 700, 699, 560,
                        520, 519, 480, 460, 459, 430, 400, 399, 375, 320];

async function medirGraficos(page) {
  await page.evaluate(() => document.fonts.ready);
  return page.evaluate(() => {
    const salida = [];
    document.querySelectorAll('svg.grafico').forEach((svg) => {
      const [, , ancho, alto] = svg.getAttribute('viewBox').split(' ').map(Number);
      const escala = svg.getBoundingClientRect().width / ancho;
      const textos = [...svg.querySelectorAll('text')].map((t) => {
        const c = t.getBBox();
        return {
          txt: t.textContent,
          clase: t.getAttribute('class') || '',
          px: parseFloat(getComputedStyle(t).fontSize) * escala,
          x: c.x, der: c.x + c.width, y: c.y, aba: c.y + c.height,
        };
      });
      salida.push({ seccion: svg.closest('section')?.id || '?', ancho, alto, textos });
    });
    return salida;
  });
}

for (const caso of CASOS) {
  test.describe(`Se lee lo que pone · ${caso.nombre}`, () => {
    test('ningún texto de ningún gráfico se sale de su viewBox', async ({ page }) => {
      for (const ancho of ANCHOS_GRAFICO) {
        await page.setViewportSize({ width: ancho, height: 900 });
        await page.goto(caso.ruta);
        for (const g of await medirGraficos(page)) {
          for (const t of g.textos) {
            const fuera = t.x < -0.5 || t.der > g.ancho + 0.5
                       || t.y < -0.5 || t.aba > g.alto + 0.5;
            expect(fuera,
              `a ${ancho}px, en #${g.seccion}, «${t.txt}» se sale del lienzo `
              + `${g.ancho}x${g.alto}: ocupa de ${t.x.toFixed(0)} a ${t.der.toFixed(0)} `
              + `en horizontal y de ${t.y.toFixed(0)} a ${t.aba.toFixed(0)} en vertical. `
              + 'Un SVG recorta sin avisar: eso en pantalla es una palabra a medias.')
              .toBe(false);
          }
        }
      }
    });

    // No basta con que no se pisen: dos textos PEGADOS se leen como uno solo.
    // Los rótulos de dos barras vecinas llegaron a quedar a cero de distancia
    // y en pantalla ponía «LÍNEAREGRESIÓN». Un criterio de solape los daba por
    // buenos, porque técnicamente no se solapaban. Hace falta hueco de verdad.
    test('no hay dos textos pisados ni pegados', async ({ page }) => {
      const HUECO = 10;   // unidades del viewBox, algo más de media letra
      for (const ancho of ANCHOS_GRAFICO) {
        await page.setViewportSize({ width: ancho, height: 900 });
        await page.goto(caso.ruta);
        for (const g of await medirGraficos(page)) {
          for (let a = 0; a < g.textos.length; a++) {
            for (let b = a + 1; b < g.textos.length; b++) {
              const A = g.textos[a], B = g.textos[b];
              // Solo compiten los que comparten franja horizontal: dos textos
              // en líneas distintas pueden solaparse en x sin estorbarse.
              if (Math.min(A.aba, B.aba) - Math.max(A.y, B.y) <= 1) continue;
              const hueco = Math.max(A.x, B.x) - Math.min(A.der, B.der);
              expect(hueco,
                `a ${ancho}px, en #${g.seccion}, «${A.txt}» y «${B.txt}» quedan a `
                + `${hueco.toFixed(0)} unidades: pegados se leen como una sola palabra.`)
                .toBeGreaterThanOrEqual(HUECO);
            }
          }
        }
      }
    });

    // El número que de verdad importa: a qué tamaño acaba leyéndose. Sin esto,
    // la letra puede encogerse a 5px sin que salte una sola prueba, porque
    // cabe de sobra: el fallo de caber es distinto del fallo de leerse.
    test('en un móvil de 375 los rótulos se leen a un tamaño de verdad', async ({ page }) => {
      await page.setViewportSize(MOVIL);
      await page.goto(caso.ruta);
      for (const g of await medirGraficos(page)) {
        for (const t of g.textos) {
          // 11px de suelo, no 8. Los rótulos se acortaron a propósito para
          // que la letra pudiera crecer hasta aquí: si alguien vuelve a
          // alargar uno, la letra tendrá que encoger y salta esta prueba.
          const suelo = t.clase.includes('g-num') ? 20 : 11;
          expect(t.px,
            `a 375px, en #${g.seccion}, «${t.txt}» se pinta a ${t.px.toFixed(1)}px. `
            + 'Repasa la escalera de --g en ui/trabajo.css.')
            .toBeGreaterThanOrEqual(suelo);
        }
      }
    });
  });
}
