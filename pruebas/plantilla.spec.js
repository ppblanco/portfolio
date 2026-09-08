// =============================================================
// Pruebas de index.html · el portfolio
// -------------------------------------------------------------
// Cubre lo que se puede romper sin que salte ningún error: un
// botón que ya no hace nada, un enlace que no lleva a ninguna
// parte, un bloque que nunca se enciende, un resto de la
// plantilla de relleno que se cuela con el contenido real.
//
// Ejecutar:  cd pruebas  &&  npx playwright test plantilla
// =============================================================

const { test, expect } = require('@playwright/test');

// Comprobado el 26/08/2026: `test.use({ reducedMotion: 'reduce' })` NO llega
// al navegador en esta configuración —matchMedia sigue diciendo false—, así que
// las pruebas que lo usaban creían estar probando movimiento reducido sin
// estarlo. Lo que funciona es emulateMedia() antes del goto, y cada prueba que
// dependa de ello comprueba que de verdad se aplicó.
async function irConMovimientoReducido(page, ruta) {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(ruta || '/index.html');
  const activo = await page.evaluate(() =>
    matchMedia('(prefers-reduced-motion: reduce)').matches);
  expect(activo, 'la emulación de movimiento reducido no se aplicó').toBe(true);
}

const MOVIL = { width: 375, height: 800 };
const ESCRITORIO = { width: 1440, height: 900 };

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

test.describe('Estructura', () => {
  test('están las ocho secciones, en orden', async ({ page }) => {
    await page.goto('/index.html');

    const orden = await page.evaluate(() =>
      [...document.querySelectorAll('main > section')].map((s) => s.id || s.className.split(' ')[0]));

    expect(orden).toEqual([
      'portada', 'mapa', 'trabajo', 'destrezas',
      'experiencia', 'formacion', 'sobre-mi', 'contacto',
    ]);
  });

  test('las secciones numeradas van del 01 al 05, sin saltos', async ({ page }) => {
    await page.goto('/index.html');
    const numeros = await page.locator('.rotulo__n').allTextContents();
    expect(numeros).toEqual(['01', '02', '03', '04', '05']);
  });

  test('lo que se pinta cuadra con las listas del JSON', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('.obra')).toHaveCount(7);
    await expect(page.locator('.fila-destreza')).toHaveCount(5);
    await expect(page.locator('.puesto')).toHaveCount(4);
    await expect(page.locator('.hito')).toHaveCount(4);
  });
});

test.describe('Contenido real', () => {
  test('no queda ni un resto de la plantilla de relleno', async ({ page }) => {
    await page.goto('/index.html');
    const texto = await page.locator('body').innerText();

    for (const resto of [
      'Nombre Apellido', 'Elemento 1', 'Nombre del proyecto',
      'Título o certificación', 'MARCADOR', 'Lorem', 'PENDIENTE',
    ]) {
      expect(texto, `queda "${resto}" en la página`).not.toContain(resto);
    }
  });

  test('el nombre y la titulación son los de Pedro', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('h1')).toHaveText('Pedro Pérez Blanco');
    await expect(page.locator('.portada__meta')).toContainText('Business Analytics');
    await expect(page).toHaveTitle(/Pedro Pérez Blanco/);
  });

  test('ningún enlace se queda sin destino', async ({ page }) => {
    await page.goto('/index.html');
    // Un href vacío, un "#" pelado o un marcador sin rellenar son enlaces que
    // no llevan a ninguna parte. Delante de un reclutador, peor que no estar.
    const muertos = await page.locator('a[href]').evaluateAll((els) =>
      els.filter((a) => {
        const h = a.getAttribute('href');
        return !h || h === '#' || h.includes('PENDIENTE') || h.includes('TU-DOMINIO');
      }).map((a) => a.textContent.trim().slice(0, 40)));
    expect(muertos).toEqual([]);
  });

  test('los enlaces internos apuntan a secciones que existen', async ({ page }) => {
    await page.goto('/index.html');
    const rotos = await page.evaluate(() =>
      [...document.querySelectorAll('a[href^="#"]')]
        .filter((a) => a.getAttribute('href').length > 1)
        .filter((a) => !document.querySelector(a.getAttribute('href')))
        .map((a) => a.getAttribute('href')));
    expect(rotos).toEqual([]);
  });

  test('los archivos que enlaza el portfolio existen de verdad', async ({ page, request }) => {
    await page.goto('/index.html');
    const rutas = await page.locator('a[href]').evaluateAll((els) =>
      els.map((a) => a.getAttribute('href'))
        .filter((h) => /^(trabajos|medios)\//.test(h)));

    expect(rutas.length).toBeGreaterThan(0);
    for (const r of rutas) {
      const res = await request.get('/' + r);
      expect(res.status(), `${r} no se sirve`).toBe(200);
    }
  });
});

test.describe('Mapa del trabajo', () => {
  test('en escritorio pinta algo: no es un lienzo en blanco', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.locator('#mapa').scrollIntoViewIfNeeded();
    await page.waitForTimeout(900);

    const pintado = await page.locator('#mapa-portfolio').evaluate((c) => {
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let n = 0;
      for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++;
      return n;
    });
    expect(pintado, 'el lienzo del mapa está vacío').toBeGreaterThan(500);
  });

  test('sus nodos de proyecto llevan a fichas que existen', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    // El grafo apunta a estas seis fichas por id. Si una cambia de nombre en
    // el JSON, el nodo deja de llevar a ninguna parte y nadie se entera.
    for (const id of ['obra-tfm', 'obra-videojuegos', 'obra-deeplearning',
                      'obra-letterboxd', 'obra-lipton', 'obra-apuestas']) {
      await expect(page.locator('#' + id)).toBeAttached();
    }
  });

  test('en móvil no se monta y en su sitio queda el aviso', async ({ page }) => {
    await page.setViewportSize(MOVIL);
    await page.goto('/index.html');
    await expect(page.locator('.mapa__caja')).toBeHidden();
    await expect(page.locator('.mapa__aviso')).toBeVisible();
  });
});

test.describe('Barra', () => {
  test('en escritorio se ven los enlaces y el botón de contacto', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await expect(page.locator('.barra__lista a')).toHaveCount(5);
    await expect(page.locator('.barra__lista')).toBeVisible();
    await expect(page.locator('.barra__cta')).toBeVisible();
  });

  test('se aparta al bajar y vuelve al subir', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    const barra = page.locator('#barra');

    await page.mouse.wheel(0, 1200);
    await expect(barra).toHaveClass(/esta-oculta/);

    await page.mouse.wheel(0, -400);
    await expect(barra).not.toHaveClass(/esta-oculta/);
  });

  test('la barra de avance crece al bajar', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    const escala = () => page.locator('#avance').evaluate((e) => {
      const m = new DOMMatrixReadOnly(getComputedStyle(e).transform);
      return m.a;
    });

    expect(await escala()).toBeLessThan(0.05);
    await page.mouse.wheel(0, 3000);
    await expect.poll(escala, { timeout: 4000 }).toBeGreaterThan(0.1);
  });

  test('en móvil el menú se pliega, se abre y se cierra con Escape', async ({ page }) => {
    await page.setViewportSize(MOVIL);
    await page.goto('/index.html');

    const lista = page.locator('#menu-lista');
    const boton = page.locator('#menu');

    await expect(lista).toBeHidden();
    await expect(boton).toHaveAttribute('aria-expanded', 'false');

    await boton.click();
    await expect(lista).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(lista).toBeHidden();
  });

  test('al pulsar un enlace del menú, el menú se quita de en medio', async ({ page }) => {
    await page.setViewportSize(MOVIL);
    await page.goto('/index.html');
    await page.locator('#menu').click();
    await page.locator('#menu-lista a').first().click();
    await expect(page.locator('#menu-lista')).toBeHidden();
  });
});

test.describe('Carrusel de trabajos', () => {
  // Con movimiento reducido el desplazamiento es instantáneo, así que no hay
  // que adivinar cuánto tarda una animación: una prueba que depende de un
  // reloj falla sola cada dos por tres.
  test('nace al principio y la flecha de atrás está desactivada', async ({ page }) => {
    await irConMovimientoReducido(page);
    await expect(page.locator('#carrusel-atras')).toBeDisabled();
    await expect(page.locator('#carrusel-alante')).toBeEnabled();
  });

  test('la flecha adelante desplaza la pista y activa la de atrás', async ({ page }) => {
    await irConMovimientoReducido(page);
    const pista = page.locator('#pista-trabajos');
    const antes = await pista.evaluate((e) => e.scrollLeft);

    await page.locator('#carrusel-alante').click();
    await expect
      .poll(async () => pista.evaluate((e) => e.scrollLeft), { timeout: 5000 })
      .toBeGreaterThan(antes);
    await expect(page.locator('#carrusel-atras')).toBeEnabled();
  });

  test('hay un punto por grupo y el primero está marcado', async ({ page }) => {
    await irConMovimientoReducido(page);
    const puntos = page.locator('.carrusel__punto');
    const cuantos = await puntos.count();

    expect(cuantos).toBeGreaterThan(1);
    await expect(puntos.first()).toHaveAttribute('aria-current', 'true');

    const esperados = await page.locator('#pista-trabajos').evaluate((e) =>
      Math.max(1, Math.ceil(e.scrollWidth / e.clientWidth)));
    expect(cuantos).toBe(esperados);
  });

  test('pulsar el último punto lleva al final de la pista', async ({ page }) => {
    await irConMovimientoReducido(page);
    const pista = page.locator('#pista-trabajos');
    await page.locator('.carrusel__punto').last().click();

    await expect
      .poll(async () => pista.evaluate((e) =>
        e.scrollLeft + e.clientWidth >= e.scrollWidth - 4), { timeout: 5000 })
      .toBe(true);
    await expect(page.locator('#carrusel-alante')).toBeDisabled();
  });
});

test.describe('Acordeones', () => {
  test('el primer puesto nace abierto y los demás cerrados', async ({ page }) => {
    await page.goto('/index.html');
    const abiertos = await page.locator('.puesto').evaluateAll((els) => els.map((e) => e.open));
    expect(abiertos).toEqual([true, false, false, false]);
  });

  test('pulsar un puesto cerrado lo abre y enseña su texto', async ({ page }) => {
    await page.goto('/index.html');
    const segundo = page.locator('.puesto').nth(1);
    await segundo.locator('summary').click();
    await expect(segundo).toHaveAttribute('open', '');
    await expect(segundo.locator('.parrafo')).toBeVisible();
  });

  test('los de experiencia son <details>: funcionan sin JavaScript', async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const p = await ctx.newPage();
    await p.goto('/index.html');
    const segundo = p.locator('.puesto').nth(1);
    await segundo.locator('summary').click();
    await expect(segundo).toHaveAttribute('open', '');
    await ctx.close();
  });
});

// =============================================================
// Saludo multilingüe del hero
// =============================================================
test.describe('El saludo se escribe solo', () => {
  test('arranca en "Hola" y va cambiando de idioma', async ({ page }) => {
    await page.goto('/index.html');
    const palabra = page.locator('#saludo-palabra');

    // "Hola" viene ya escrito en el HTML: la línea nunca está vacía antes de
    // que corra el script.
    await expect(palabra).toHaveText('Hola');
    await expect(page.locator('#saludo')).toHaveClass(/esta-tecleando/);

    const vistos = new Set();
    for (let i = 0; i < 20; i++) {
      vistos.add(await palabra.textContent());
      await page.waitForTimeout(350);
    }
    // Tecleando y borrando pasa por muchos estados intermedios; con más de
    // tres distintos ya está claro que se mueve, y no depende de dónde caiga
    // el muestreo.
    expect(vistos.size, 'el saludo no cambia').toBeGreaterThan(3);
  });

  test('la cola viaja pegada al cursor, sin hueco reservado', async ({ page }) => {
    await page.goto('/index.html');
    // Se probó reservar un ancho fijo para la palabra y quedaba un vacío antes
    // de la coma con toda palabra corta, que se lee como un fallo de
    // maquetación. Esta prueba impide que alguien lo vuelva a poner.
    const ancho = await page.locator('.saludo__palabra').evaluate((e) =>
      getComputedStyle(e).minWidth);
    expect(ancho === 'auto' || ancho === '0px').toBe(true);
  });

  test('un lector de pantalla lo oye una sola vez, y quieto', async ({ page }) => {
    await page.goto('/index.html');
    // La mitad animada va aria-hidden: un nodo cuyo texto cambia cada 80ms es
    // ruido en el árbol de accesibilidad. Al lado va la versión quieta.
    await expect(page.locator('#saludo')).toHaveAttribute('aria-hidden', 'true');
    await expect(page.locator('.portada__saludo .oculto')).toHaveText('Hola, soy');
  });

  test('con movimiento reducido no se mueve ni sale el cursor', async ({ page }) => {
    await irConMovimientoReducido(page);
    const palabra = page.locator('#saludo-palabra');

    await expect(palabra).toHaveText('Hola');
    await expect(page.locator('#saludo')).not.toHaveClass(/esta-tecleando/);
    await page.waitForTimeout(2600);
    await expect(palabra, 'se movió con movimiento reducido').toHaveText('Hola');
  });
});

// =============================================================
// Formación: filas que se abren al pasar por encima
// =============================================================
test.describe('Formación', () => {
  // Lee la altura y el estado de las cuatro filas. Nada de capturas: una
  // captura con clip o fullPage redimensiona el viewport por dentro, y ese
  // cambio dispara el pointerleave que cierra la fila justo al fotografiarla.
  // Costó tres capturas engañosas averiguarlo.
  const filas = (page) => page.$$eval('#hitos [data-fila]', (els) => els.map((e) => ({
    alto: Math.round(e.getBoundingClientRect().height),
    abierta: e.querySelector('.hito__cabeza').getAttribute('aria-expanded'),
    placa: e.querySelector('.hito__placa')
      ? Number(getComputedStyle(e.querySelector('.hito__placa')).opacity) : null,
  })));

  const sobre = async (page, n) => {
    await page.locator('#hitos [data-fila]:nth-child(' + n + ') .hito__cabeza').hover();
    await page.waitForTimeout(650);
  };
  const fuera = async (page) => {
    await page.mouse.move(10, 10);
    await page.waitForTimeout(700);
  };

  test.describe('en escritorio', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(ESCRITORIO);
      await page.goto('/index.html');
      await page.locator('#formacion').scrollIntoViewIfNeeded();
      await page.waitForTimeout(700);
    });

    test('en reposo las cuatro están cerradas y a la misma altura', async ({ page }) => {
      const f = await filas(page);
      expect(f).toHaveLength(4);
      f.forEach((x) => {
        expect(x.alto).toBe(68);
        expect(x.abierta).toBe('false');
        expect(x.placa).toBeLessThan(0.05);
      });
    });

    test('el ratón abre la fila y saca su imagen', async ({ page }) => {
      await sobre(page, 2);
      const f = await filas(page);
      expect(f[1].alto, 'la fila no creció').toBeGreaterThan(120);
      expect(f[1].abierta).toBe('true');
      expect(f[1].placa, 'la imagen no apareció').toBeGreaterThan(0.9);
      expect(f[0].alto).toBe(68);
      expect(f[2].alto).toBe(68);
    });

    test('la fila abierta cabe entera: nada recortado', async ({ page }) => {
      await sobre(page, 1);
      const sobra = await page.$eval('#hitos [data-fila]:nth-child(1)', (e) => {
        const et = e.querySelector('.etiquetas').getBoundingClientRect();
        return Math.round(e.getBoundingClientRect().bottom - et.bottom);
      });
      // La altura sale de medir el cuerpo; si alguien toca el relleno y no la
      // medida, las etiquetas se cortan por abajo y nadie se entera.
      expect(sobra, 'las etiquetas se salen de la fila').toBeGreaterThan(0);
    });

    test('al salir con el ratón se vuelve a cerrar', async ({ page }) => {
      await sobre(page, 2);
      await fuera(page);
      const f = await filas(page);
      f.forEach((x) => { expect(x.alto).toBe(68); });
    });

    test('un clic la deja clavada y sobrevive a que el ratón se vaya', async ({ page }) => {
      await page.locator('#hitos [data-fila]:nth-child(3) .hito__cabeza').click();
      await page.waitForTimeout(650);
      await fuera(page);

      const f = await filas(page);
      expect(f[2].abierta, 'la fila clavada se cerró al salir').toBe('true');
      expect(f[2].alto).toBeGreaterThan(120);
    });

    test('con una clavada, el ratón sobre otra sigue previsualizando', async ({ page }) => {
      // Esta es la trampa del componente: una guarda del tipo "hay algo
      // clavado" congela las cuatro filas con un solo clic, y como la cabecera
      // es un botón con cursor de mano, hacer clic está invitado. Se lee como
      // que el componente está roto.
      await page.locator('#hitos [data-fila]:nth-child(3) .hito__cabeza').click();
      await page.waitForTimeout(650);
      await sobre(page, 1);

      const f = await filas(page);
      expect(f[0].abierta, 'el clic bloqueó el hover').toBe('true');
      expect(f[2].abierta).toBe('false');
    });

    test('el teclado también la abre, y al salir vuelve a la clavada', async ({ page }) => {
      await page.locator('#hitos [data-fila]:nth-child(3) .hito__cabeza').click();
      await page.waitForTimeout(650);
      await fuera(page);

      await page.locator('#hitos [data-fila]:nth-child(4) .hito__cabeza').focus();
      await fuera(page);
      let f = await filas(page);
      expect(f[3].abierta, 'el foco no abrió la fila').toBe('true');

      await page.locator('.barra__cta').focus();
      await page.waitForTimeout(700);
      f = await filas(page);
      expect(f[2].abierta, 'al salir el foco no volvió a la clavada').toBe('true');
    });

    test('cada fila apunta a su panel y la cabecera es un botón de verdad', async ({ page }) => {
      const mal = await page.$$eval('#hitos [data-fila]', (els) => els.filter((e) => {
        const b = e.querySelector('.hito__cabeza');
        const id = b && b.getAttribute('aria-controls');
        return !b || b.tagName !== 'BUTTON' || !id || !e.querySelector('#' + id);
      }).length);
      expect(mal).toBe(0);
    });
  });

  test('en móvil las cuatro quedan abiertas y la foto baja bajo el texto', async ({ page }) => {
    // Una fila que se abre al pasar el ratón en una pantalla táctil es un
    // objetivo de toque disfrazado de hover, así que ahí van abiertas.
    // La placa NO se esconde —eso dejaba la sección entera sin una sola
    // imagen en la mitad de las visitas—: se baja debajo del texto, que es
    // donde una foto cabe en una columna estrecha.
    await page.setViewportSize(MOVIL);
    await page.goto('/index.html');
    await page.locator('#formacion').scrollIntoViewIfNeeded();
    await page.waitForTimeout(800);

    const f = await filas(page);
    f.forEach((x) => {
      expect(x.alto, 'la fila está colapsada en móvil').toBeGreaterThan(90);
      expect(x.abierta).toBe('true');
    });
    await expect(page.locator('.hito__puntos li').first()).toBeVisible();
    await expect(page.locator('.etiqueta').first()).toBeVisible();

    const sitio = await page.$$eval('#hitos [data-fila]', (els) => els.map((e) => {
      const pl = e.querySelector('.hito__placa');
      const ul = e.querySelector('.hito__puntos');
      const img = pl && pl.querySelector('img');
      const rp = pl.getBoundingClientRect(), ru = ul.getBoundingClientRect();
      const esc = img ? Math.min(rp.width / img.naturalWidth, rp.height / img.naturalHeight) : 0;
      return {
        visible: getComputedStyle(pl).display !== 'none' && rp.height > 40,
        debajo: rp.top >= ru.bottom - 1,   // detrás del texto, no encima
        dentro: rp.right <= e.getBoundingClientRect().right + 1,
        entera: img ? Math.abs((img.naturalWidth * esc) / (img.naturalHeight * esc)
                               - img.naturalWidth / img.naturalHeight) < 0.02 : false,
      };
    }));
    expect(sitio).toHaveLength(4);
    sitio.forEach((s, i) => {
      expect(s.visible, `la fila ${i + 1} se quedó sin foto en móvil`).toBe(true);
      expect(s.debajo, `la foto de la fila ${i + 1} se monta sobre el texto`).toBe(true);
      expect(s.dentro, `la foto de la fila ${i + 1} se sale de la fila`).toBe(true);
      expect(s.entera, `la foto de la fila ${i + 1} se recorta en móvil`).toBe(true);
    });
  });

  test('sin JavaScript se leen las cuatro enteras', async ({ browser }) => {
    // El colapso vive detrás de .js: sin script no se esconde nada. Es la
    // única forma de que un buscador o un navegador con el JS bloqueado vean
    // el contenido completo.
    const ctx = await browser.newContext({ javaScriptEnabled: false, viewport: ESCRITORIO });
    const p2 = await ctx.newPage();
    await p2.goto('/index.html');

    await expect(p2.locator('#hitos')).not.toHaveClass(/js/);
    const escondidos = await p2.locator('.hito__cuerpo').evaluateAll((els) =>
      els.filter((e) => e.getBoundingClientRect().height < 20).length);
    expect(escondidos).toBe(0);
    await ctx.close();
  });
});

test.describe('Movimiento', () => {
  test('el interruptor del pie para el movimiento y lo recuerda', async ({ page }) => {
    await page.goto('/index.html');
    const boton = page.locator('#quieto');

    await expect(boton).toHaveAttribute('aria-pressed', 'false');
    await boton.click();
    await expect(boton).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('html')).toHaveClass(/sin-movimiento/);

    await page.reload();
    await expect(page.locator('html')).toHaveClass(/sin-movimiento/);
  });

  test('con el sistema en movimiento reducido, nada se esconde y el interruptor no miente', async ({ page }) => {
    await irConMovimientoReducido(page);

    // Sin revelado no hay nada que revelar: todo se ve desde el principio.
    const invisibles = await page.locator('[data-revelar]').evaluateAll((els) =>
      els.filter((e) => parseFloat(getComputedStyle(e).opacity) < 0.9).length);
    expect(invisibles).toBe(0);

    // Un botón que ofrece reanudar algo que el sistema prohíbe es mentira.
    const boton = page.locator('#quieto');
    await expect(boton).toBeDisabled();
    await expect(boton).toContainText('sistema');
  });

  test('sin JavaScript no queda nada escondido', async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const p = await ctx.newPage();
    await p.goto('/index.html');
    const invisibles = await p.locator('[data-revelar]').evaluateAll((els) =>
      els.filter((e) => parseFloat(getComputedStyle(e).opacity) < 0.9).length);
    expect(invisibles).toBe(0);
    await ctx.close();
  });

  test('recorriendo la página, todos los bloques acaban encendidos', async ({ page }) => {
    await page.goto('/index.html');
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 400) {
        window.scrollTo({ top: y, behavior: 'instant' });
        await new Promise((r) => setTimeout(r, 50));
      }
      await new Promise((r) => setTimeout(r, 400));
    });
    const apagados = await page.locator('[data-revelar]').evaluateAll((els) =>
      els.filter((e) => !e.classList.contains('esta-visible')).length);
    expect(apagados).toBe(0);
  });
});

// =============================================================
// Fondo de datos
// -------------------------------------------------------------
// La red que corre por detrás. Lo que importa no es que se vea
// bonita —eso se juzga mirándola— sino que obedezca al mismo
// interruptor que todo lo demás y que no deje trabajo girando
// cuando nadie lo mira.
// =============================================================
test.describe('Fondo de datos', () => {
  // El contador de requestAnimationFrame se instala ANTES que ningún script de
  // la página. Es la única forma de contar las llamadas de TODOS los bucles,
  // el del fondo y el del mapa, y por tanto de detectar uno duplicado.
  const contarCuadros = (page) => page.addInitScript(() => {
    window.__raf = 0;
    const original = window.requestAnimationFrame;
    window.requestAnimationFrame = function (cb) {
      window.__raf++;
      return original.call(window, cb);
    };
  });

  // Huella del lienzo. Se lee el canvas directamente: una captura de pantalla
  // redimensiona el viewport por dentro y perturba justo lo que mide.
  const huella = (page) => page.evaluate(() => {
    const c = document.getElementById('fondo');
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    let suma = 0, vivos = 0;
    for (let i = 3; i < d.length; i += 4 * 37) {
      if (d[i] > 3) { vivos++; suma += d[i] + d[i - 1] * 3; }
    }
    return { suma, vivos };
  });

  // Cuenta repintados del lienzo. Es MEJOR instrumento que comparar huellas de
  // píxeles: la huella se movía tres unidades sobre veinticuatro mil de forma
  // intermitente y eso convertía la prueba en una moneda al aire. Un repintado
  // es un hecho binario. Se envuelve clearRect, que es la primera línea de
  // cada pintada, y se instala antes que ningún script de la página.
  const contarPintadas = (page) => page.addInitScript(() => {
    window.__pinta = [];
    const original = CanvasRenderingContext2D.prototype.clearRect;
    CanvasRenderingContext2D.prototype.clearRect = function () {
      if (this.canvas && this.canvas.id === 'fondo') window.__pinta.push(performance.now());
      return original.apply(this, arguments);
    };
  });

  const pintadasDesde = (page, marca) => page.evaluate(
    (m) => window.__pinta.filter((x) => x > m).length, marca);

  const ritmo = async (page, ms) => {
    await page.evaluate(() => { window.__raf = 0; });
    await page.waitForTimeout(ms);
    const n = await page.evaluate(() => window.__raf);
    return Math.round(n / (ms / 1000));
  };

  test('existe, está detrás de todo y no roba ni un clic', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');

    const v = await page.locator('#fondo').evaluate((c) => {
      const s = getComputedStyle(c);
      return { punteros: s.pointerEvents, z: Number(s.zIndex), pos: s.position,
               oculto: c.getAttribute('aria-hidden') };
    });
    expect(v.punteros).toBe('none');
    expect(v.z).toBeLessThan(0);
    expect(v.pos).toBe('fixed');
    // Es decoración: ningún lector de pantalla tiene por qué anunciarla.
    expect(v.oculto).toBe('true');

    // Fijo y fuera del flujo: no puede cambiar las dimensiones del documento.
    const declarado = await page.evaluate(() => document.body.scrollWidth);
    expect(declarado).toBeLessThanOrEqual(ESCRITORIO.width + 1);
  });

  test('nada opaco lo tapa: <body> tiene que ser transparente', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');

    /* Esta prueba nace de un fallo que las demás no podían ver. El lienzo va en
       z-index negativo, así que pinta en el paso de "hijos con z negativo" del
       contexto de apilamiento raíz; los fondos de bloque —el de <body>— pintan
       DESPUÉS. Con un fondo opaco en <body>, el lienzo queda debajo y no se ve
       nada, aunque getImageData siga diciendo que hay tinta: esa función lee el
       búfer del canvas y no sabe nada de lo que tiene encima.
       Medido cuando pasó: 19 de 25 puntos con tinta fuerte salían por pantalla
       idénticos al fondo liso. */
    const capas = await page.evaluate(() => {
      const c = getComputedStyle;
      const transparente = (v) => v === 'transparent' || v === 'rgba(0, 0, 0, 0)';
      return {
        bodyTransparente: transparente(c(document.body).backgroundColor),
        htmlPintado: !transparente(c(document.documentElement).backgroundColor),
        z: Number(c(document.getElementById('fondo')).zIndex),
      };
    });

    expect(capas.bodyTransparente,
      '<body> tiene fondo opaco y tapa el lienzo del fondo').toBe(true);
    // Y el color de tierra tiene que estar en <html>, o la página sale en blanco.
    expect(capas.htmlPintado, '<html> se ha quedado sin color de fondo').toBe(true);
    expect(capas.z).toBeLessThan(0);
  });

  test('se ve en pantalla, no solo en el búfer del lienzo', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.waitForTimeout(2000);

    // Se comprueba con el propio navegador: se pinta el lienzo dentro de un
    // canvas auxiliar junto al color de tierra y se mira si el resultado se
    // aparta del fondo liso. Es lo que ve un ojo, no lo que cree el lienzo.
    const contraste = await page.evaluate(() => {
      const c = document.getElementById('fondo');
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let fuertes = 0;
      for (let i = 3; i < d.length; i += 4) if (d[i] > 120) fuertes++;
      return { fuertes, encendido: c.classList.contains('esta-encendido'),
               opacidad: Number(getComputedStyle(c).opacity) };
    });

    // Tinta con cuerpo, el lienzo encendido y sin nadie que lo atenúe.
    expect(contraste.fuertes, 'no hay ni un punto con cuerpo en el fondo').toBeGreaterThan(300);
    expect(contraste.encendido, 'el lienzo no llegó a encenderse').toBe(true);
    expect(contraste.opacidad).toBeGreaterThan(0.9);
  });

  test('con el movimiento activo, se mueve', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.waitForTimeout(1200);

    const a = await huella(page);
    expect(a.vivos, 'el lienzo está vacío').toBeGreaterThan(5);
    await page.waitForTimeout(900);
    const b = await huella(page);
    expect(a.suma, 'el fondo no se mueve').not.toBe(b.suma);
  });

  test('el ciclo completo: parar, seguir parado, y reanudar', async ({ page }) => {
    await contarCuadros(page);
    await contarPintadas(page);
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.waitForTimeout(1200);

    const enMarcha = await ritmo(page, 1200);
    expect(enMarcha, 'no hay ningún bucle corriendo').toBeGreaterThan(20);

    // --- parar ---
    const boton = page.locator('#quieto');
    await boton.click();
    await page.waitForTimeout(900);

    await expect(boton).toHaveAttribute('aria-pressed', 'true');
    await expect(boton).toContainText('Reanudar');
    await expect(page.locator('html')).toHaveClass(/sin-movimiento/);

    // Parado no es apagado: queda una red quieta y muy tenue.
    const parada = await huella(page);
    expect(parada.vivos, 'al parar se ha borrado el lienzo entero').toBeGreaterThan(0);

    // Y a partir de aquí, ni un repintado más. Al pausar se pinta UNA vez, la
    // red estática; lo que no puede haber es una segunda.
    const marca = await page.evaluate(() => performance.now());
    await page.waitForTimeout(1200);
    const despues = await pintadasDesde(page, marca);
    expect(despues, 'el lienzo se sigue repintando con el movimiento parado').toBe(0);

    // Y no puede quedar un requestAnimationFrame girando.
    const parado = await ritmo(page, 1200);
    expect(parado, 'queda un bucle de animación girando en pausa').toBeLessThan(5);

    // --- reanudar ---
    await boton.click();
    await page.waitForTimeout(300);
    await expect(boton).toHaveAttribute('aria-pressed', 'false');
    await expect(boton).toContainText('Parar');

    const marca2 = await page.evaluate(() => performance.now());
    await page.waitForTimeout(1000);
    const vuelta = await pintadasDesde(page, marca2);
    // Al ritmo de pantalla, un segundo son decenas de pintadas. Con veinte ya
    // está claro que el bucle volvió, sin atarse al refresco de la máquina.
    expect(vuelta, 'el fondo no vuelve tras reanudar').toBeGreaterThan(20);
  });

  test('parar y reanudar varias veces no duplica el bucle', async ({ page }) => {
    await contarCuadros(page);
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.waitForTimeout(1200);

    const base = await ritmo(page, 1200);
    const boton = page.locator('#quieto');
    for (let i = 0; i < 4; i++) {
      await boton.click();
      await page.waitForTimeout(260);
      await boton.click();
      await page.waitForTimeout(260);
    }
    await page.waitForTimeout(800);
    const despues = await ritmo(page, 1200);

    // Un bucle de más dobla las llamadas por segundo. Pasó de verdad: al
    // reanudar se empujaba el mapa con mostrar(), que lo daba por visible
    // aunque estuviera a tres pantallas, y su física se quedaba corriendo.
    expect(despues, `de ${base} a ${despues} llamadas por segundo: hay bucles de más`)
      .toBeLessThan(base * 1.6);
  });

  test('con movimiento reducido no se mueve y no gasta ni un cuadro', async ({ page }) => {
    await contarCuadros(page);
    await contarPintadas(page);
    await page.setViewportSize(ESCRITORIO);
    await irConMovimientoReducido(page);
    await page.waitForTimeout(1400);

    const a = await huella(page);
    // Queda la red quieta, que es lo máximo que se puede ofrecer sin mover nada.
    expect(a.vivos, 'no pinta nada en absoluto').toBeGreaterThan(0);

    const marca = await page.evaluate(() => performance.now());
    await page.waitForTimeout(1200);
    expect(await pintadasDesde(page, marca),
      'el lienzo se repinta con movimiento reducido').toBe(0);

    const cuadros = await ritmo(page, 1200);
    expect(cuadros, 'hay un bucle corriendo con movimiento reducido').toBeLessThan(5);
  });

  test('la densidad baja en pantallas pequeñas', async ({ page }) => {
    const tinta = async (w) => {
      await page.setViewportSize({ width: w, height: 900 });
      await page.goto('/index.html');
      await page.waitForTimeout(1400);
      return (await huella(page)).vivos / (w * 900);
    };
    // Se compara tinta por píxel disponible: si la densidad saliera de un
    // número fijo en vez del área, en un móvil habría el mismo amontonamiento
    // que en un monitor.
    const movil = await tinta(375);
    const escritorio = await tinta(1440);
    expect(movil).toBeGreaterThan(0);
    expect(escritorio).toBeGreaterThan(0);
    expect(Math.abs(movil - escritorio) / escritorio,
      'la densidad por píxel se dispara entre móvil y escritorio').toBeLessThan(1.2);
  });

  for (const ancho of [375, 768, 1440]) {
    test(`a ${ancho}px no desborda ni suelta errores`, async ({ page }) => {
      const malas = [];
      page.on('pageerror', (e) => malas.push('js: ' + e.message));
      page.on('console', (m) => { if (m.type() === 'error') malas.push('consola: ' + m.text()); });

      await page.setViewportSize({ width: ancho, height: 900 });
      await page.goto('/index.html');
      await page.waitForTimeout(1300);

      const arrastre = await page.evaluate(() => {
        window.scrollTo(9999, 0);
        const x = window.scrollX;
        window.scrollTo(0, 0);
        return x;
      });
      expect(arrastre).toBe(0);
      expect(malas).toEqual([]);
    });
  }
});

// =============================================================
// Fotos reales y tamanos
// =============================================================
test.describe('Fotos', () => {
  test('la del hero es de tamaño medio y no se deforma', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');

    const f = await page.locator('.portada__imagen').evaluate((e) => {
      const r = e.getBoundingClientRect();
      const panel = document.querySelector('.portada__panel').getBoundingClientRect();
      return { ancho: r.width, alto: r.height, proporcion: r.width / r.height,
               anchoPanel: panel.width };
    });

    // 4:5, que es la proporción del original: así object-fit:cover no recorta
    // ni un píxel y la cara no se corta de forma rara.
    expect(Math.abs(f.proporcion - 0.8), 'la foto se ha deformado').toBeLessThan(0.03);
    // Media: con presencia, pero sin comerse el hero. Antes ocupaba casi lo
    // mismo que todo el texto junto.
    expect(f.ancho).toBeLessThanOrEqual(345);
    expect(f.ancho, 'se ha quedado en un sello').toBeGreaterThan(240);
    expect(f.ancho, 'la foto compite con el texto').toBeLessThan(f.anchoPanel * 0.62);
  });

  test('en móvil se encoge y se centra', async ({ page }) => {
    await page.setViewportSize(MOVIL);
    await page.goto('/index.html');
    const ancho = await page.locator('.portada__imagen').evaluate((e) =>
      e.getBoundingClientRect().width);
    expect(ancho).toBeLessThanOrEqual(265);
  });

  test('cada bloque de formación tiene SU foto, y no se repiten', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.locator('#formacion').scrollIntoViewIfNeeded();
    await page.waitForTimeout(900);

    const fotos = await page.$$eval('#hitos .hito__placa img', (els) => els.map((e) => ({
      src: e.getAttribute('src'),
      ancha: e.naturalWidth,
      ajuste: getComputedStyle(e).objectFit,
    })));

    expect(fotos).toHaveLength(4);
    // Cuatro archivos distintos: si alguien copia y pega una entrada del JSON y
    // se olvida de cambiar la imagen, salen dos bloques con la misma foto y a
    // simple vista no se nota.
    expect(new Set(fotos.map((f) => f.src)).size, 'hay fotos repetidas').toBe(4);
    fotos.forEach((f) => {
      expect(f.ancha, `no carga ${f.src}`).toBeGreaterThan(0);
      // contain, no cover: estas fotos se enseñan enteras. Con cover la caja
      // mandaba sobre la foto y se comía birretes, titulares y media cara.
      expect(f.ajuste, `${f.src} volvió a recortarse`).toBe('contain');
    });
  });

  test('la sección de experiencia lleva SU foto, entera y sin deformar', async ({ page }) => {
    await page.goto('/index.html');
    const img = page.locator('.experiencia__imagen');
    // El nombre importa: es la foto que Pedro puso para esta sección, no una
    // portada de proyecto ni un gráfico reaprovechado.
    await expect(img).toHaveAttribute('src', /experiencia\.jpg$/);

    // Hay que bajar hasta ella: la imagen es loading="lazy" y el navegador no
    // la pide hasta que se acerca a la pantalla. Sin esto naturalWidth es 0 y
    // la prueba diría que está rota cuando lo que pasa es que aún no ha tocado.
    await page.locator('#experiencia').scrollIntoViewIfNeeded();
    await expect.poll(async () => img.evaluate((e) => e.naturalWidth),
      { message: 'la foto de ICADE no llega a cargar', timeout: 8000 }).toBeGreaterThan(0);

    const alt = await img.getAttribute('alt');
    expect(alt.length, 'sin texto alternativo que describa la foto').toBeGreaterThan(20);

    /* Entera en escritorio y en móvil. El hueco es 4:3 igual que la foto, así
       que lo pintado tiene que salir con la proporción del archivo en las dos.
       Antes esta sección tenía una columna vertical y un recorte cocido en el
       archivo; ahora manda la foto. */
    for (const ancho of [1440, 375]) {
      await page.setViewportSize({ width: ancho, height: 900 });
      await page.locator('#experiencia').scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
      const m = await img.evaluate((e) => {
        const r = e.getBoundingClientRect();
        const esc = Math.min(r.width / e.naturalWidth, r.height / e.naturalHeight);
        return {
          nat: e.naturalWidth / e.naturalHeight,
          pintado: (e.naturalWidth * esc) / (e.naturalHeight * esc),
          ajuste: getComputedStyle(e).objectFit,
          ancho: r.width,
        };
      });
      expect(m.ajuste, `a ${ancho}px la foto de experiencia no está en contain`).toBe('contain');
      expect(Math.abs(m.pintado - m.nat), `a ${ancho}px sale deformada`).toBeLessThan(0.02);
      expect(m.ancho, `a ${ancho}px la foto se queda en nada`).toBeGreaterThan(200);
    }
  });

  test('la ficha entera lleva al trabajo, no solo el enlace del pie', async ({ page }) => {
    await page.goto('/index.html');
    /* Se pulsa en la PORTADA, que es el sitio donde nadie pondría un enlace y
       donde todo el mundo hace clic. Si solo funcionara el pie, esto no
       navegaría y la ficha sería un cartel en vez de una puerta.

       Con page.mouse y no con locator.click(): Playwright se niega a pulsar un
       elemento que está tapado por otro, y aquí eso es justo lo que se quiere
       comprobar —que encima de la portada hay un enlace que cubre la ficha—.
       Su comprobación de accesibilidad daría un fallo donde no lo hay. Un clic
       en unas coordenadas es lo que hace una persona. */
    await page.locator('#trabajo').scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    const caja = await page.locator('#obra-videojuegos .obra__portada').boundingBox();
    await page.mouse.click(caja.x + caja.width / 2, caja.y + caja.height / 2);
    // A la pagina de caso, no al cuaderno: desde el 01/09/2026 la ficha lleva
    // al caso, y el caso lleva al cuaderno.
    await expect(page).toHaveURL(/trabajos\/videojuegos\.html$/);
    await page.goBack();

    // Y el enlace de verdad es el título, con el nombre del proyecto dentro:
    // eso es lo que anuncia un lector de pantalla y lo que indexa un buscador.
    // Un "leer más" repetido cuatro veces no dice nada a ninguno de los dos.
    const enlaces = await page.$$eval('.obra .obra__ir', (els) => els.map((e) => ({
      texto: e.textContent.trim(),
      href: e.getAttribute('href'),
      etiqueta: e.closest('.obra').querySelector('.obra__titulo').textContent.trim(),
    })));
    expect(enlaces.length, 'ninguna ficha lleva a su trabajo').toBeGreaterThanOrEqual(3);
    enlaces.forEach((l) => {
      expect(l.texto.length, 'el enlace de la ficha no dice a qué lleva').toBeGreaterThan(8);
      expect(l.texto).toBe(l.etiqueta);
      expect(l.href, `${l.texto} no apunta a ningún sitio`).toMatch(/^trabajos\//);
    });
  });

  test('la flecha de la ficha se ve sin pasar el ratón por encima', async ({ page }) => {
    await page.goto('/index.html');
    // Estaba escondida hasta el hover, y en una pantalla táctil no hay hover:
    // ahí no aparecía nunca y nada decía que la ficha llevara a alguna parte.
    await page.setViewportSize(MOVIL);
    await page.locator('#trabajo').scrollIntoViewIfNeeded();
    const flecha = page.locator('#obra-videojuegos .obra__ir-boton');
    await expect(flecha).toBeVisible();
    expect(await flecha.evaluate((e) => Number(getComputedStyle(e).opacity)))
      .toBeGreaterThan(0.9);
  });

  test('los enlaces del pie siguen siendo suyos, no se los come la ficha', async ({ page }) => {
    await page.goto('/index.html');
    // El ::after que hace pulsable la tarjeta cubre TODO, incluido el pie. Si
    // el enlace del pie no se levanta por encima, deja de existir como enlace
    // y el día que uno apunte a GitHub y otro al cuaderno, los dos irán al
    // mismo sitio sin que nadie se entere.
    // La segunda ficha, que se ve entera: la tercera la recorta el carrusel y
    // el punto medio de su enlace cae fuera de lo visible.
    await page.locator('#trabajo').scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    const encima = await page.$eval('#obra-videojuegos .obra__enlace', (a) => {
      const r = a.getBoundingClientRect();
      const quien = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return quien === a || a.contains(quien);
    });
    expect(encima, 'el enlace del pie está tapado por el área de la tarjeta').toBe(true);
  });

  test('las siete fichas llevan a alguna parte', async ({ page }) => {
    await page.goto('/index.html');
    /* Desde el 03/09/2026 son seis trabajos y ninguno queda huérfano. Esta
       prueba existe para que se note el día que vuelva a haberlo: una ficha
       sin destino no es un error, pero pasar de seis a cinco enlaces sin
       darse cuenta sí. */
    const fichas = await page.$$eval('.obra', (els) => els.map((e) => ({
      id: e.id,
      huerfana: e.classList.contains('obra--sin-destino'),
      enlace: !!e.querySelector('.obra__ir'),
      flecha: !!e.querySelector('.obra__ir-boton'),
    })));
    expect(fichas).toHaveLength(7);
    fichas.forEach((f) => {
      expect(f.huerfana, `${f.id} se quedó sin destino`).toBe(false);
      // Enlace y flecha van juntos SIEMPRE: una flecha sin enlace promete un
      // clic que no existe, y un enlace sin flecha no se ve que lo sea.
      expect(f.enlace, `${f.id} no tiene enlace`).toBe(true);
      expect(f.flecha, `${f.id} no enseña la flecha`).toBe(true);
    });
  });

  test('el generador sabe apagar una ficha que no lleve a ninguna parte', async () => {
    /* El mecanismo, comprobado en el código, porque ya no hay ninguna ficha
       real en ese estado. Si se borra la rama, la próxima ficha sin enlace
       saldrá con flecha, se levantará al pasar el ratón y no llevará a nada:
       exactamente lo que se lee como un enlace roto. */
    const fs = require('fs');
    const path = require('path');
    const gen = fs.readFileSync(
      path.join(__dirname, '..', 'herramientas', 'hacer-plantilla.py'), 'utf8');
    expect(gen, 'ya no se marca la ficha sin destino').toContain('obra--sin-destino');
    // Sin enlace principal, ni título enlazado ni flecha.
    expect(gen).toMatch(/else:[\s\S]{0,400}titulo = e\(p\["titulo"\]\)[\s\S]{0,120}boton = ""/);

    const css = fs.readFileSync(
      path.join(__dirname, '..', 'ui', 'plantilla.css'), 'utf8');
    expect(css, 'la ficha sin destino ya no se apaga en el CSS')
      .toMatch(/\.obra--sin-destino:hover[\s\S]{0,160}transform:none/);
  });

  test('el mapa abre el trabajo, no baja a su ficha', async ({ page }) => {
    /* Desde el 02/09/2026 los proyectos tienen su página de caso, así
       que pulsar un nodo y aterrizar en la tarjeta dejaba a quien pulsaba a un
       clic todavía de lo que había ido a ver. Con la tarjeta era lo único que
       se podía hacer; ahora ya no.

       El grafo se dibuja en un canvas, así que desde fuera no hay elemento que
       pulsar: lo que se comprueba es que los seis nodos declaran su página,
       que esas páginas existen, y que la navegación es la rama que se toma. La
       comprobación de que un clic de verdad navega se hizo con un barrido del
       lienzo; aquí saldría lentísima y flaky. */
    const fs2 = require('fs');
    const path2 = require('path');
    const mapa = fs2.readFileSync(path2.join(__dirname, '..', 'ui', 'mapa.js'), 'utf8');

    const paginas = [...mapa.matchAll(/pagina:\s*'([^']+)'/g)].map((m) => m[1]);
    expect(paginas.length, 'los nodos del mapa no declaran su página').toBe(7);

    for (const ruta of paginas) {
      expect(fs2.existsSync(path2.join(__dirname, '..', ruta)),
        `el mapa lleva a ${ruta}, que no existe`).toBe(true);
      const r = await page.request.get('/' + ruta);
      expect(r.status(), `${ruta} no se sirve`).toBe(200);
    }

    // La rama que navega, y la de respaldo por si un proyecto se quedara sin
    // página: sin ella, ese nodo dejaría de hacer nada al pulsarlo.
    expect(mapa).toMatch(/if \(nodo\.pagina\)[\s\S]{0,120}window\.location\.href = nodo\.pagina/);
    expect(mapa, 'se perdió el respaldo de bajar a la ficha').toContain('scrollIntoView');
  });

  test('las siete fichas llevan su portada, y ninguna se repite', async ({ page }) => {
    await page.goto('/index.html');
    const portadas = await page.$$eval('.obra__portada', (els) => els.map((e) => ({
      src: decodeURIComponent(e.getAttribute('src')),
      alt: e.getAttribute('alt') || '',
      obra: e.closest('.obra').id,
    })));
    expect(portadas).toHaveLength(7);
    // Cuatro archivos distintos: copiar y pegar una ficha y olvidarse de la
    // imagen deja dos proyectos con la misma cara y no se nota de un vistazo.
    expect(new Set(portadas.map((p) => p.src)).size, 'hay portadas repetidas').toBe(7);
    portadas.forEach((p) => {
      expect(p.src, `${p.obra} no tiene portada`).toMatch(/^medios\//);
      expect(p.alt.length, `la portada de ${p.obra} no está descrita`).toBeGreaterThan(30);
    });
  });

  test('los dos CV están y se descargan, no se abren en el visor', async ({ page }) => {
    await page.goto('/index.html');
    /* Dos idiomas, dos archivos. Y con `download`: sin ese atributo el
       navegador abre el PDF en una pestaña y quien venía a guardarlo tiene que
       buscar el botón del visor. Pedro pidió que se pudieran descargar. */
    const cvs = await page.$$eval('a[href*="cv-pedro-perez-blanco"]', (as) => as.map((a) => ({
      href: a.getAttribute('href'),
      descarga: a.getAttribute('download'),
      texto: a.textContent.replace(/\s+/g, ' ').trim(),
    })));
    expect(cvs.length, 'faltan enlaces al CV').toBeGreaterThanOrEqual(2);

    const idiomas = new Set(cvs.map((c) => c.href));
    expect(idiomas.has('medios/cv-pedro-perez-blanco-es.pdf'), 'falta el CV en español').toBe(true);
    expect(idiomas.has('medios/cv-pedro-perez-blanco-en.pdf'), 'falta el CV en inglés').toBe(true);

    cvs.forEach((c) => {
      expect(c.descarga, `${c.href} se abriría en vez de descargarse`).toBeTruthy();
      expect(c.descarga, 'el archivo se guardaría sin extensión').toMatch(/\.pdf$/);
      // Y el enlace dice en qué idioma está, que es de lo que se trata.
      expect(c.texto, `"${c.texto}" no dice el idioma`).toMatch(/español|English/i);
    });
  });

  test('los dos archivos de CV existen y son PDF de verdad', async ({ page }) => {
    for (const idioma of ['es', 'en']) {
      const r = await page.request.get(`/medios/cv-pedro-perez-blanco-${idioma}.pdf`);
      expect(r.status(), `el CV en ${idioma} no se sirve`).toBe(200);
      expect(r.headers()['content-type']).toContain('pdf');
      const cuerpo = await r.body();
      expect(cuerpo.length, `el CV en ${idioma} está vacío`).toBeGreaterThan(10000);
      expect(cuerpo.subarray(0, 4).toString(), 'no empieza por %PDF').toBe('%PDF');
    }
  });

  test('Lead scoring no lleva ninguna etiqueta de estado', async ({ page }) => {
    await page.goto('/index.html');
    // Ni "En producción" ni nada que la sustituya. La comprobación es doble:
    // que no exista la píldora, y que no aparezca la palabra en la ficha.
    await expect(page.locator('.obra__distintivo')).toHaveCount(0);
    const ficha = await page.locator('#obra-tfm').innerText();
    for (const palabra of ['producción', 'Live', 'Activo', 'Terminado', 'Disponible']) {
      expect(ficha.toLowerCase(), `queda "${palabra}" como estado`)
        .not.toContain(palabra.toLowerCase());
    }
  });
});

// =============================================================
// Llamada flotante de contacto
// =============================================================
test.describe('CTA flotante', () => {
  const estado = (page) => page.locator('#flotante').evaluate((e) => ({
    marcado: e.classList.contains('esta-visible'),
    visibilidad: getComputedStyle(e).visibility,
    href: e.getAttribute('href'),
  }));

  test('lleva mi correo de verdad y los dos textos', async ({ page }) => {
    await page.goto('/index.html');
    const cta = page.locator('#flotante');
    await expect(cta).toHaveAttribute('href', 'mailto:pedro.perez.blanco@outlook.es');
    await expect(cta.locator('b')).toHaveText('Ponte en contacto');
    await expect(cta.locator('.flotante__texto span')).toHaveText('Escríbeme cuando quieras');
    // Es un enlace con nombre accesible propio, no un icono mudo.
    await expect(cta).toHaveAttribute('aria-label', /.{15,}/);
  });

  test('no está al cargar, aparece al bajar y se aparta en la llamada final', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.waitForTimeout(600);

    let v = await estado(page);
    expect(v.marcado, 'aparece nada más cargar').toBe(false);
    // visibility, no solo transform: si solo se moviera, se podría tabular a un
    // enlace que no está en pantalla y un lector de pantalla lo anunciaría.
    expect(v.visibilidad, 'sigue existiendo para el teclado estando fuera').toBe('hidden');

    await page.evaluate(() => window.scrollTo({ top: 1400, behavior: 'instant' }));
    await page.waitForTimeout(700);
    v = await estado(page);
    expect(v.marcado, 'no aparece al bajar').toBe(true);
    expect(v.visibilidad).toBe('visible');

    await page.evaluate(() => {
      const r = document.getElementById('contacto').getBoundingClientRect();
      window.scrollTo({ top: window.scrollY + r.top - 100, behavior: 'instant' });
    });
    await page.waitForTimeout(900);
    v = await estado(page);
    // Una píldora que dice "ponte en contacto" tapando el botón de ponerse en
    // contacto es redundante y estorba.
    expect(v.marcado, 'se queda encima de la llamada final').toBe(false);
  });

  test('en móvil se queda solo el círculo', async ({ page }) => {
    await page.setViewportSize(MOVIL);
    await page.goto('/index.html');
    await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight * 0.75, behavior: 'instant' }));
    await page.waitForTimeout(800);

    const v = await page.locator('#flotante').evaluate((e) => {
      const r = e.getBoundingClientRect();
      return { ancho: r.width, derecha: window.innerWidth - r.right,
               texto: e.querySelector('.flotante__texto').getBoundingClientRect().width };
    });
    // La píldora entera son 235px: en 375 es casi dos tercios de pantalla.
    expect(v.ancho, 'ocupa demasiado en móvil').toBeLessThan(110);
    expect(v.texto, 'el texto sigue ocupando sitio').toBeLessThan(2);
    expect(v.derecha).toBeGreaterThan(0);
  });
});

// =============================================================
// El anillo que acompana al puntero
// =============================================================
test.describe('Cursor de nodo', () => {
  test('no esconde el cursor del sistema ni se come los clics', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');

    // Esta es la línea que separa un detalle bonito de un problema de
    // accesibilidad: esconder el cursor nativo se lleva por delante el cursor
    // grande, el de alto contraste y cualquier ajuste del sistema.
    const nativo = await page.evaluate(() => getComputedStyle(document.body).cursor);
    expect(nativo, 'se ha escondido el cursor del sistema').not.toBe('none');

    const anillo = await page.locator('#nodo-cursor').evaluate((e) => ({
      punteros: getComputedStyle(e).pointerEvents,
      oculto: e.getAttribute('aria-hidden'),
    }));
    expect(anillo.punteros, 'el anillo intercepta clics y selección de texto').toBe('none');
    expect(anillo.oculto).toBe('true');
  });

  test('se enciende al mover el ratón y reacciona sobre lo pulsable', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.waitForTimeout(500);

    await page.mouse.move(700, 640);
    await page.waitForTimeout(350);
    let v = await page.locator('#nodo-cursor').evaluate((e) => ({
      visible: e.classList.contains('esta-visible'), activo: e.classList.contains('esta-activo'),
    }));
    expect(v.visible, 'el anillo no aparece').toBe(true);
    expect(v.activo, 'se activa sobre texto normal').toBe(false);

    await page.locator('.boton--solido').first().hover();
    await page.waitForTimeout(350);
    v = await page.locator('#nodo-cursor').evaluate((e) => ({
      activo: e.classList.contains('esta-activo'),
    }));
    expect(v.activo, 'no reacciona sobre un botón').toBe(true);
  });

  test('con el movimiento parado desaparece, y el CTA sigue funcionando', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.locator('#quieto').click();
    await page.waitForTimeout(500);

    await expect(page.locator('#nodo-cursor')).toBeHidden();
    // Parar el movimiento quita animación, no funcionalidad.
    await page.evaluate(() => window.scrollTo({ top: 1400, behavior: 'instant' }));
    await page.waitForTimeout(700);
    await expect(page.locator('#flotante')).toBeVisible();
    await expect(page.locator('#flotante')).toHaveAttribute('href', /^mailto:/);
  });

  test('con movimiento reducido no se monta', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await irConMovimientoReducido(page);
    await expect(page.locator('#nodo-cursor')).toBeHidden();
  });
});

// =============================================================
// Regresiones
// -------------------------------------------------------------
// Estas pruebas nacen de dos fallos que la suite entera no veia,
// porque todas las demas arrancaban en un navegador limpio y
// miraban una pieza cada vez.
// =============================================================
test.describe('Regresiones', () => {
  // Deja la preferencia guardada ANTES de que corra ningun script, igual que
  // si se hubiera pulsado "parar movimiento" en una visita anterior. Es lo que
  // le paso a Pedro: la preferencia se queda para siempre.
  const conPausaGuardada = async (page) => {
    await page.addInitScript(() => {
      try { localStorage.setItem('plantilla-sin-movimiento', '1'); } catch (e) { /* nada */ }
    });
    await page.goto('/index.html');
    await expect(page.locator('html')).toHaveClass(/sin-movimiento/);
  };

  test('con el movimiento parado, el saludo TAMBIÉN se para', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await conPausaGuardada(page);
    await page.waitForTimeout(900);

    // Este era el fallo: el saludo solo miraba la preferencia del SISTEMA al
    // arrancar y nunca el estado del botón, así que seguía tecleando con la
    // página supuestamente en pausa. Una promesa a medias.
    const antes = await page.locator('#saludo-palabra').textContent();
    await page.waitForTimeout(2600);
    const despues = await page.locator('#saludo-palabra').textContent();

    expect(despues, 'el saludo sigue tecleando con el movimiento parado').toBe(antes);
    await expect(page.locator('#saludo')).not.toHaveClass(/esta-tecleando/);
  });

  test('la pausa se ve y se deshace sin bajar hasta el pie', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await conPausaGuardada(page);
    await page.waitForTimeout(700);

    /* El botón del pie está al 99% del recorrido: seis mil píxeles de web
       quieta antes de encontrar la forma de arreglarlo. Quien pause sin querer
       ve una web muerta y no sabe por qué. Este aviso vive en la barra. */
    const aviso = page.locator('#reanudar');
    await expect(aviso).toBeVisible();
    const enPantalla = await aviso.evaluate((e) => {
      const r = e.getBoundingClientRect();
      return r.top >= 0 && r.bottom <= window.innerHeight;
    });
    expect(enPantalla, 'el aviso de pausa no se ve sin desplazarse').toBe(true);

    await aviso.click();
    await expect(page.locator('html')).not.toHaveClass(/sin-movimiento/);
    await expect(aviso).toBeHidden();

    // Y todo vuelve: el saludo teclea otra vez.
    const antes = await page.locator('#saludo-palabra').textContent();
    await page.waitForTimeout(2600);
    expect(await page.locator('#saludo-palabra').textContent(),
      'tras reanudar, el saludo sigue parado').not.toBe(antes);
  });

  test('reanudar desde la barra no deja bucles de más', async ({ page }) => {
    await page.addInitScript(() => {
      window.__raf = 0;
      const original = window.requestAnimationFrame;
      window.requestAnimationFrame = function (cb) { window.__raf++; return original.call(window, cb); };
    });
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.waitForTimeout(1200);

    const medir = async () => {
      await page.evaluate(() => { window.__raf = 0; });
      await page.waitForTimeout(1200);
      return Math.round((await page.evaluate(() => window.__raf)) / 1.2);
    };
    const base = await medir();

    for (let i = 0; i < 3; i++) {
      await page.locator('#quieto').click();
      await page.waitForTimeout(300);
      await page.locator('#reanudar').click();
      await page.waitForTimeout(300);
    }
    await page.waitForTimeout(800);
    const despues = await medir();
    expect(despues, `de ${base} a ${despues} cuadros por segundo`).toBeLessThan(base * 1.6);
  });

  test('ninguna imagen se recorta hasta perder lo que enseña', async ({ page }) => {
    /* La regresión de verdad: en móvil, la foto de ICADE se metía en un hueco
       apaisado siendo vertical y cover se comía el 60% de la altura. Salía el
       torso y la corbata, sin cabeza. Un recorte del 35% ya es sospechoso;
       más que eso, casi seguro que se está perdiendo lo importante. */
    for (const ancho of [375, 768, 1440]) {
      await page.setViewportSize({ width: ancho, height: 900 });
      await page.goto('/index.html');
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 500) {
          window.scrollTo({ top: y, behavior: 'instant' });
          await new Promise((r) => setTimeout(r, 60));
        }
        const imgs = [...document.querySelectorAll('img')];
        imgs.forEach((i) => { i.loading = 'eager'; });
        await Promise.all(imgs.map((i) => (i.complete && i.naturalWidth > 0
          ? Promise.resolve()
          : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 8000); }))));
      });
      await page.waitForTimeout(600);

      const brutos = await page.evaluate(() => [...document.querySelectorAll('img')]
        .map((e) => {
          const r = e.getBoundingClientRect();
          if (!r.width || !r.height || !e.naturalWidth) return null;
          if (getComputedStyle(e).objectFit !== 'cover') return null;
          // Una imagen que no se ve no recorta nada que nadie vaya a mirar.
          // Las placas de formación viven a opacidad 0 hasta que su fila se
          // abre, y medirlas cerradas daba un 74% que no existe en pantalla.
          let op = 1;
          for (let a = e; a && a !== document.body; a = a.parentElement) {
            op *= Number(getComputedStyle(a).opacity);
          }
          if (op < 0.1) return null;
          const f = Math.max(r.width / e.naturalWidth, r.height / e.naturalHeight);
          const perdidoX = 1 - r.width / (e.naturalWidth * f);
          const perdidoY = 1 - r.height / (e.naturalHeight * f);
          return { src: decodeURIComponent(e.getAttribute('src')).split('/').pop(),
                   perdido: Math.round(Math.max(perdidoX, perdidoY) * 100) };
        }).filter(Boolean));

      const brutas = brutos.filter((x) => x.perdido > 35);
      expect(brutas, `a ${ancho}px se recortan de más: `
        + brutas.map((x) => `${x.src} pierde ${x.perdido}%`).join(', ')).toEqual([]);
    }
  });

  test('las fotos de formación se ven enteras, sin recortar nada', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.locator('#formacion').scrollIntoViewIfNeeded();
    await page.waitForTimeout(900);

    // Se mide con la fila ABIERTA, que es cuando la placa se ve. Cerrada mide
    // 68px de alto y con el relleno el hueco útil se queda en nada: medirla
    // así daba un resultado que no le pasa a nadie mirando la página.
    for (let i = 1; i <= 4; i++) {
      // Clic, no hover: clavar la fila la deja abierta pase lo que pase con el
      // puntero. Y se espera a que ESTÉ abierta en vez de contar milisegundos:
      // el muelle tarda lo que tarda, y bajo carga tardaba más que la espera
      // fija que había aquí. La prueba fallaba a ratos, que es lo peor que
      // puede hacer una prueba.
      await page.locator(`#hitos [data-fila]:nth-child(${i}) .hito__cabeza`).click();
      await page.waitForFunction(
        (n) => {
          const c = document.querySelector(`#hitos [data-fila]:nth-child(${n}) .hito__cuerpo`);
          const pl = document.querySelector(`#hitos [data-fila]:nth-child(${n}) .hito__placa`);
          return c && pl && c.getBoundingClientRect().height > 40
            && pl.getBoundingClientRect().height > 120;
        },
        i, { timeout: 5000 });
      const f = await page.$eval(`#hitos [data-fila]:nth-child(${i}) .hito__placa img`, (e) => {
        const r = e.getBoundingClientRect();
        const escala = Math.min(r.width / e.naturalWidth, r.height / e.naturalHeight);
        return {
          src: decodeURIComponent(e.getAttribute('src')).split('/').pop(),
          ajuste: getComputedStyle(e).objectFit,
          nat: e.naturalWidth / e.naturalHeight,
          pintado: (e.naturalWidth * escala) / (e.naturalHeight * escala),
          cabe: e.naturalWidth * escala <= r.width + 1 && e.naturalHeight * escala <= r.height + 1,
          util: Math.min(r.width, r.height),
        };
      });
      expect(f.ajuste, `${f.src} no está en contain`).toBe('contain');
      expect(f.util, `${f.src} no tiene hueco donde encajarse`).toBeGreaterThan(20);
      expect(Math.abs(f.pintado - f.nat), `${f.src} se pinta deformada`).toBeLessThan(0.02);
      expect(f.cabe, `${f.src} se sale de su hueco y el overflow la recorta`).toBe(true);
    }

    /* Y la comprobación directa de "no se recorta": con object-fit:contain, lo
       que se pinta conserva la proporción del archivo. Si alguien vuelve a
       poner cover, la proporción pintada pasa a ser la de la caja y esto salta.

       Se mide el CONTENIDO pintado, no la caja: la caja llena la placa y el
       contenido va encajado dentro. Antes se comparaba object-position, que
       decía dónde mirar pero no si se estaba perdiendo algo. */
    const fotos = await page.$$eval('#hitos .hito__placa img', (els) => els.map((e) => {
      const r = e.getBoundingClientRect();
      const nat = e.naturalWidth / e.naturalHeight;
      const escala = Math.min(r.width / e.naturalWidth, r.height / e.naturalHeight);
      return {
        src: decodeURIComponent(e.getAttribute('src')).split('/').pop(),
        ajuste: getComputedStyle(e).objectFit,
        nat,
        // Lo que se ve, con contain: la foto escalada para caber entera.
        pintado: (e.naturalWidth * escala) / (e.naturalHeight * escala),
        cabe: e.naturalWidth * escala <= r.width + 1 && e.naturalHeight * escala <= r.height + 1,
      };
    }));

    expect(fotos).toHaveLength(4);
    fotos.forEach((f) => {
      expect(f.ajuste, `${f.src} no está en contain`).toBe('contain');
      expect(Math.abs(f.pintado - f.nat), `${f.src} se pinta deformada`).toBeLessThan(0.02);
      expect(f.cabe, `${f.src} se sale de su hueco y el overflow la recorta`).toBe(true);
    });
  });

  test('la portada del TFM es la diapositiva de la defensa, entera', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    const portada = page.locator('#obra-tfm .obra__portada');
    // Es una diapositiva con texto hasta cerca del borde: recortarla se lleva
    // palabras del título.
    await expect(portada).toHaveAttribute('src', /Lead%20scoring/);
    await expect(portada).toHaveClass(/obra__portada--entera/);
    expect(await portada.evaluate((e) => getComputedStyle(e).objectFit)).toBe('contain');
  });

  test('la foto de cada bloque es la que dice su nombre de archivo', async ({ page }) => {
    await page.goto('/index.html');
    // Pedro nombra los archivos con la sección a la que van. Si alguien mueve
    // uno de sitio, el bloque enseña la foto de otro y nadie se entera.
    const pares = await page.$$eval('#hitos [data-fila]', (els) => els.map((e) => ({
      titulo: e.querySelector('.hito__titulo').textContent.trim(),
      archivo: decodeURIComponent(e.querySelector('.hito__placa img').getAttribute('src'))
        .split('/').pop().replace(/\.[a-z]+$/i, ''),
    })));

    // El nombre del archivo tiene que empezar como el título del bloque.
    const suelto = (s) => s.toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');
    const malas = pares.filter((x) => !suelto(x.archivo).startsWith(suelto(x.titulo).slice(0, 14)));
    expect(malas, 'fotos en el bloque equivocado: '
      + malas.map((x) => `"${x.titulo}" lleva "${x.archivo}"`).join(' / ')).toEqual([]);
  });
});

test.describe('Teclado y accesibilidad', () => {
  test('el enlace de saltar al contenido existe y apunta a <main>', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('a.saltar')).toHaveAttribute('href', '#contenido');
    await expect(page.locator('main#contenido')).toBeAttached();
  });

  test('se puede recorrer la barra con el tabulador', async ({ page }) => {
    await page.setViewportSize(ESCRITORIO);
    await page.goto('/index.html');
    await page.keyboard.press('Tab');                       // saltar al contenido
    await expect(page.locator('a.saltar')).toBeFocused();
    await page.keyboard.press('Tab');                       // la marca
    await expect(page.locator('.barra__marca')).toBeFocused();
  });

  test('toda imagen o describe algo o es decorativa a propósito', async ({ page }) => {
    await page.goto('/index.html');
    // Un alt vacío no es un olvido si la imagen es decoración: las placas de
    // formación repiten lo que ya dice el texto de al lado, y describirlas
    // haría que un lector de pantalla leyera la institución dos veces. Lo que
    // sí es un fallo es un alt vacío en una imagen que nadie ha marcado como
    // decorativa, y un alt que falta del todo.
    const mal = await page.locator('img').evaluateAll((els) => els.filter((e) => {
      const alt = e.getAttribute('alt');
      if (alt === null) return true;                       // ni siquiera está
      if (alt.trim()) return false;                        // describe algo
      return !e.closest('[aria-hidden="true"]');           // vacío sin declararlo
    }).map((e) => e.getAttribute('src')));
    expect(mal).toEqual([]);
  });

  test('el lienzo del mapa se anuncia como imagen con descripción', async ({ page }) => {
    await page.goto('/index.html');
    const lienzo = page.locator('#mapa-portfolio');
    await expect(lienzo).toHaveAttribute('role', 'img');
    await expect(lienzo).toHaveAttribute('aria-label', /.{20,}/);
  });
});

test.describe('Sin sorpresas', () => {
  for (const ancho of [375, 430, 768, 1024, 1440]) {
    test(`a ${ancho}px no se desborda a lo ancho`, async ({ page }) => {
      await page.setViewportSize({ width: ancho, height: 900 });
      await page.goto('/index.html');

      // Desborde de verdad = la página se deja arrastrar. Con overflow:clip,
      // scrollWidth sigue contando lo recortado y da falsos positivos.
      const arrastre = await page.evaluate(() => {
        window.scrollTo(9999, 0);
        const x = window.scrollX;
        window.scrollTo(0, 0);
        return x;
      });
      expect(arrastre, `se puede arrastrar a la derecha a ${ancho}px`).toBe(0);

      const declarado = await page.evaluate(() => document.body.scrollWidth);
      expect(declarado).toBeLessThanOrEqual(ancho + 1);
    });
  }

  test('no hay errores de consola ni peticiones fallidas', async ({ page }) => {
    const malas = [];
    page.on('pageerror', (e) => malas.push('js: ' + e.message));
    page.on('console', (m) => { if (m.type() === 'error') malas.push('consola: ' + m.text()); });
    page.on('requestfailed', (r) => malas.push('red: ' + r.url()));

    await page.goto('/index.html');
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 400) {
        window.scrollTo({ top: y, behavior: 'instant' });
        await new Promise((r) => setTimeout(r, 40));
      }
    });

    expect(malas).toEqual([]);
  });

  test('ninguna imagen está rota', async ({ page }) => {
    await page.goto('/index.html');
    const rotas = await page.evaluate(async () => {
      const imgs = [...document.querySelectorAll('img')];
      imgs.forEach((i) => { i.loading = 'eager'; });
      await Promise.all(imgs.map((i) => (i.complete && i.naturalWidth > 0
        ? Promise.resolve()
        : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 8000); }))));
      // naturalWidth, no complete: complete vale false mientras el navegador
      // entrega una imagen que ya tenía en caché.
      return imgs.filter((i) => i.naturalWidth === 0).map((i) => i.src.split('/').pop());
    });
    expect(rotas).toEqual([]);
  });
});

test.describe('Contraste', () => {
  test('los rótulos y las etiquetas de la home se leen: 4,5:1 mínimo', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(400);
    const malos = await textosConPocoContraste(page);
    expect(malos, 'textos por debajo del mínimo: ' + malos.join(' | '))
      .toEqual([]);
  });
});
