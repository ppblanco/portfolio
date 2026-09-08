// =====================================================================
// LO QUE SALIÓ DE LA AUDITORÍA
// =====================================================================
//
// Archivo aparte a propósito. Todo lo que hay aquí son comprobaciones que
// nacieron de una auditoría concreta —canonical, pestañas nuevas, área de
// pulsación, alternativa accesible del mapa, enlaces externos vivos— y
// tenerlas juntas hace que se entienda de dónde vienen y que se puedan
// quitar de golpe si alguna deja de tener sentido.
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const RAIZ = path.join(__dirname, '..');
const CASOS = fs.readdirSync(path.join(RAIZ, 'trabajos'))
  .filter((f) => f.endsWith('.html'))
  .map((f) => '/trabajos/' + f);
const PAGINAS = ['/index.html', ...CASOS];
const DOMINIO = 'https://pedro-perez-data.netlify.app';

// =============================================================
// CANONICAL
// =============================================================
test.describe('Canonical', () => {
  for (const ruta of PAGINAS) {
    test(`${ruta} declara su canonical, y solo uno`, async ({ page }) => {
      await page.goto(ruta);
      const hrefs = await page.$$eval('link[rel="canonical"]',
        (ns) => ns.map((n) => n.getAttribute('href')));
      expect(hrefs, 'falta el canonical o hay más de uno').toHaveLength(1);
      const esperado = ruta === '/index.html' ? DOMINIO + '/' : DOMINIO + ruta;
      expect(hrefs[0]).toBe(esperado);
    });
  }

  test('la home apunta a la raíz, no a /index.html', async ({ page }) => {
    // Netlify sirve index.html en "/". Es la dirección que se comparte y la
    // que indexa un buscador; declarar /index.html partiría la señal en dos.
    await page.goto('/index.html');
    expect(await page.getAttribute('link[rel="canonical"]', 'href')).toBe(DOMINIO + '/');
  });

  test('canonical y og:url dicen lo mismo en cada página', async ({ page }) => {
    for (const ruta of PAGINAS) {
      await page.goto(ruta);
      const can = await page.getAttribute('link[rel="canonical"]', 'href');
      const og = await page.getAttribute('meta[property="og:url"]', 'content');
      expect(og, `${ruta}: og:url y canonical no coinciden`).toBe(can);
    }
  });

  test('el 404 NO lleva canonical, y sí noindex', async ({ page }) => {
    // Una página de error no es un recurso canónico de nada: declararlo
    // invitaría a indexarla justo cuando se le está pidiendo lo contrario.
    await page.goto('/404.html');
    await expect(page.locator('link[rel="canonical"]')).toHaveCount(0);
    expect(await page.getAttribute('meta[name="robots"]', 'content')).toContain('noindex');
  });
});

// =============================================================
// ENLACES EXTERNOS: PESTAÑA NUEVA Y REL
// =============================================================
test.describe('Enlaces externos', () => {
  test('todos los externos abren en pestaña nueva con noopener y noreferrer',
    async ({ page }) => {
      const fallos = [];
      for (const ruta of PAGINAS) {
        await page.goto(ruta);
        const enlaces = await page.$$eval('a[href^="http"]', (ns) => ns.map((n) => ({
          href: n.getAttribute('href'),
          target: n.getAttribute('target'),
          rel: n.getAttribute('rel') || '',
        })));
        for (const l of enlaces) {
          if (l.target !== '_blank') fallos.push(`${ruta}: ${l.href} sin target=_blank`);
          if (!l.rel.includes('noopener')) fallos.push(`${ruta}: ${l.href} sin noopener`);
          if (!l.rel.includes('noreferrer')) fallos.push(`${ruta}: ${l.href} sin noreferrer`);
        }
      }
      expect(fallos, fallos.join('\n')).toEqual([]);
    });

  test('los enlaces internos NO se abren en pestaña nueva', async ({ page }) => {
    // Salvo el PDF y la presentación, que son documentos y sí.
    const fallos = [];
    for (const ruta of PAGINAS) {
      await page.goto(ruta);
      const malos = await page.$$eval('a[target="_blank"]', (ns) => ns
        .map((n) => n.getAttribute('href'))
        .filter((h) => h && !h.startsWith('http') && !h.endsWith('.pdf')));
      for (const m of malos) fallos.push(`${ruta}: ${m}`);
    }
    expect(fallos, fallos.join('\n')).toEqual([]);
  });
});

// =============================================================
// ¿SIGUEN VIVOS LOS ENLACES EXTERNOS?
// =============================================================
//
// Un repositorio renombrado deja siete enlaces muertos en el portfolio y
// nadie se entera hasta que lo pulsa un reclutador. Esta prueba sale a la
// red, y por eso está escrita para NO ser frágil:
//
//   · HEAD primero; si el servidor no lo admite, GET pidiendo un solo byte.
//     Asi no se descarga un PDF entero para saber que existe.
//   · Dos intentos, con una espera entre medias.
//   · Si TODAS las peticiones fallan, es la red de aquí y no los enlaces:
//     la prueba se salta en vez de dar un rojo que no dice nada.
//   · LinkedIn responde 999 a lo que huela a automatismo. Es su política
//     antibots, no un enlace roto: se documenta como excepción y se acepta.
const TOLERADOS = {
  'linkedin.com': [999, 403, 429],   // bloqueo antibots documentado
};

async function vivo(request, url) {
  const tolerado = Object.entries(TOLERADOS)
    .find(([d]) => url.includes(d))?.[1] || [];
  for (const intento of [1, 2]) {
    for (const metodo of ['head', 'get']) {
      try {
        const r = await request[metodo](url, {
          timeout: 20000,
          maxRedirects: 5,
          headers: metodo === 'get' ? { Range: 'bytes=0-0' } : {},
          failOnStatusCode: false,
        });
        const s = r.status();
        if (s < 400 || tolerado.includes(s)) return { ok: true, status: s };
        if (metodo === 'get') {
          if (intento === 2) return { ok: false, status: s };
        }
      } catch (e) {
        if (metodo === 'get' && intento === 2) return { ok: false, error: String(e).slice(0, 90) };
      }
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  return { ok: false, error: 'agotados los intentos' };
}

test.describe('Enlaces externos vivos', () => {
  test.describe.configure({ timeout: 180000 });

  test('ningún enlace externo del portfolio está roto', async ({ page, request }) => {
    const urls = new Set();
    for (const ruta of PAGINAS) {
      await page.goto(ruta);
      for (const h of await page.$$eval('a[href^="http"]', (ns) => ns.map((n) => n.href))) {
        urls.add(h);
      }
    }
    expect(urls.size, 'no se encontró ningún enlace externo: algo va mal').toBeGreaterThan(4);

    const rotos = [];
    let fallosDeRed = 0;
    for (const u of urls) {
      const r = await vivo(request, u);
      if (!r.ok) {
        if (r.error) fallosDeRed++;
        rotos.push(`${u} -> ${r.status || r.error}`);
      }
    }
    // Si TODO falló por error de transporte, esto no habla de los enlaces.
    if (fallosDeRed === urls.size) {
      test.skip(true, 'sin salida a internet: la prueba no puede decir nada');
    }
    expect(rotos, 'enlaces externos rotos:\n' + rotos.join('\n')).toEqual([]);
  });

  test('los documentos que enlaza cada caso existen', async ({ page }) => {
    // El PDF de la presentación y el del informe: uno es local y el otro va a
    // GitHub. Aquí solo se comprueba el local, que es el que depende de esta
    // carpeta y el que se rompe al renombrar un archivo.
    const fallos = [];
    for (const ruta of CASOS) {
      await page.goto(ruta);
      const locales = await page.$$eval('a[href$=".pdf"]',
        (ns) => ns.map((n) => n.getAttribute('href')).filter((h) => !h.startsWith('http')));
      for (const h of new Set(locales)) {
        const r = await page.request.get(new URL(h, new URL(ruta, 'http://127.0.0.1:8055')).href);
        if (r.status() >= 400) fallos.push(`${ruta}: ${h} -> ${r.status()}`);
      }
    }
    expect(fallos, fallos.join('\n')).toEqual([]);
  });
});

// =============================================================
// ÁREA DE PULSACIÓN
// =============================================================
test.describe('Área de pulsación', () => {
  for (const ancho of [390, 1440]) {
    test(`a ${ancho}px ningún objetivo baja de 24x24 reales`, async ({ page }) => {
      await page.setViewportSize({ width: ancho, height: 900 });
      for (const ruta of ['/index.html', '/trabajos/rlgym-selfplay-pool.html']) {
        await page.goto(ruta);
        await page.evaluate(async () => {
          for (let y = 0; y < 20000; y += 700) {
            window.scrollTo(0, y);
            await new Promise((r) => setTimeout(r, 25));
          }
          window.scrollTo(0, 0);
        });
        const chicos = await page.evaluate(() => {
          const malos = [];
          document.querySelectorAll('a,button').forEach((el) => {
            const b = el.getBoundingClientRect();
            if (!b.width || !b.height) return;
            // El área real puede venir de un ::after estirado: es lo que hacen
            // la ficha entera y los puntos del carrusel. Se mide eso también.
            const d = getComputedStyle(el, '::after');
            const extraA = parseFloat(d.width) || 0;
            const extraB = parseFloat(d.height) || 0;
            const ancho = Math.max(b.width, extraA);
            const alto = Math.max(b.height, extraB);
            if (ancho < 24 || alto < 24) {
              malos.push(`${el.className || el.tagName} ${Math.round(ancho)}x${Math.round(alto)}`);
            }
          });
          return malos;
        });
        expect(chicos, `${ruta} a ${ancho}px:\n` + chicos.join('\n')).toEqual([]);
      }
    });
  }
});

// =============================================================
// EL MAPA, PARA QUIEN NO LO VE
// =============================================================
test.describe('Alternativa accesible del mapa', () => {
  test('el lienzo se anuncia y trae su versión en palabras', async ({ page }) => {
    await page.goto('/index.html');
    const lienzo = page.locator('#mapa canvas');
    await expect(lienzo).toHaveAttribute('role', 'img');
    expect(await lienzo.getAttribute('aria-label')).toBeTruthy();

    const lista = page.locator('#mapa ul.oculto li');
    // Una entrada de intro más una por proyecto.
    const n = await lista.count();
    expect(n, 'la alternativa en texto del mapa no se generó').toBeGreaterThan(5);

    const textos = await lista.allTextContents();
    // Tiene que decir qué comparte cada trabajo, no solo nombrarlos.
    const conHerramientas = textos.filter((t) => t.includes(':') && t.includes(','));
    expect(conHerramientas.length,
      'la alternativa nombra proyectos pero no dice qué comparten').toBeGreaterThan(4);
    expect(textos.join(' ')).toContain('Python');
  });

  test('no añade paradas de tabulador invisibles', async ({ page }) => {
    // Enlaces escondidos son paradas que un teclado encuentra y un ojo no.
    // La navegación ya existe, visible, en las fichas de debajo.
    await page.goto('/index.html');
    await expect(page.locator('#mapa ul.oculto a')).toHaveCount(0);
  });
});

// =============================================================
// RESPALDOS QUE NO PUEDO PROBAR EN UN SAFARI DE VERDAD
// =============================================================
test.describe('Respaldos', () => {
  test('toda mask-image lleva su versión -webkit-', async () => {
    // Safari sigue necesitando el prefijo. Sin él, la máscara no se aplica y
    // la rejilla del corte se ve como un cuadriculado duro de borde a borde.
    for (const f of ['plantilla.css', 'trabajo.css']) {
      const css = fs.readFileSync(path.join(RAIZ, 'ui', f), 'utf8');
      const sin = (css.match(/(?<!-webkit-)mask-image:/g) || []).length;
      const con = (css.match(/-webkit-mask-image:/g) || []).length;
      expect(con, `${f}: ${sin} mask-image y solo ${con} con prefijo`).toBe(sin);
    }
  });

  test('la banda de vídeo tiene respaldo si no hay aspect-ratio', async () => {
    const css = fs.readFileSync(path.join(RAIZ, 'ui', 'trabajo.css'), 'utf8');
    expect(css).toContain('@supports not (aspect-ratio');
    expect(css, 'el respaldo debe dar altura por padding').toMatch(/padding-bottom:\s*42\.85%/);
  });

  test('sin autoplay queda el póster y el contenido entero', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    const mp4 = [];
    page.on('request', (r) => { if (r.url().endsWith('.mp4')) mp4.push(r.url()); });
    await page.goto('/trabajos/rlgym-selfplay-pool.html');
    await page.evaluate(async () => {
      for (let y = 0; y < 20000; y += 700) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 25));
      }
    });
    await page.waitForTimeout(800);
    expect(mp4, 'con movimiento reducido no debe viajar ningún vídeo').toEqual([]);
    const posters = await page.$$eval('.corte__quieta, .relieve__quieta',
      (ns) => ns.map((i) => i.complete && i.naturalWidth > 0));
    expect(posters.length).toBeGreaterThan(2);
    expect(posters.every(Boolean), 'algún póster no cargó').toBe(true);
  });
});

// =============================================================
// LA LÍNEA DE RECTIFICACIONES
// =============================================================
test.describe('Rectificaciones', () => {
  test('están las siete, numeradas y en orden', async ({ page }) => {
    await page.goto('/trabajos/rlgym-selfplay-pool.html');
    const sec = page.locator('#s-correcciones');
    await expect(sec).toHaveCount(1);
    const textos = await sec.locator('.grafico text').allTextContents();
    for (const n of ['01', '02', '03', '04', '05', '06', '07']) {
      expect(textos, `falta la parada ${n}`).toContain(n);
    }
    for (const f of ['Supuesto', 'Prueba', 'Corrección']) {
      expect(textos.join(' '), `falta la fase ${f}`).toContain(f);
    }
  });

  test('no alarga la página más de la cuenta', async ({ page }) => {
    // El acuerdo era que esta sección no fuera otro bloque de mil píxeles.
    await page.goto('/trabajos/rlgym-selfplay-pool.html');
    const alto = await page.locator('#s-correcciones').evaluate((n) => n.getBoundingClientRect().height);
    expect(alto, 'la sección de rectificaciones se ha ido de tamaño').toBeLessThan(1000);
  });

  test('se lee sin ver el dibujo', async ({ page }) => {
    await page.goto('/trabajos/rlgym-selfplay-pool.html');
    const sr = await page.locator('#s-correcciones .oculto').first().textContent();
    expect(sr.length).toBeGreaterThan(80);
    expect(sr).toContain('supuesto');
  });
});
