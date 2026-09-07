// Servidor estático mínimo sobre la carpeta del proyecto, solo para las
// pruebas.
//
// Manda las MISMAS cabeceras comunes que Netlify, y las lee del propio
// generador de publicación para que no haya dos verdades: si mañana cambian
// en herramientas/preparar-publicacion.py, aquí cambian solas.
//
// Antes no mandaba ninguna, y eso dejaba un agujero de cobertura real: la
// suite aprobaba el <iframe> del visor de PDF porque en local nada lo
// impedía, mientras en producción el PDF viajaba con X-Frame-Options: DENY y
// el navegador se negaba a pintarlo.
const http = require('http');
const fs = require('fs');
const path = require('path');

const RAIZ = path.join(__dirname, '..');
const TIPOS = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.pdf': 'application/pdf',
  '.txt': 'text/plain; charset=utf-8',
  // El vídeo tiene que ir con su tipo de verdad: con nosniff puesto, un
  // application/octet-stream deja las portadas sin reproducir.
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.json': 'application/json',
};

// Las cabeceras comunes, sacadas del bloque COMUNES del generador. Las
// cadenas de Python se concatenan solas cuando una cabecera ocupa varias
// líneas, así que aquí se vuelven a pegar igual.
function cabecerasComunes() {
  const py = fs.readFileSync(
    path.join(RAIZ, 'herramientas', 'preparar-publicacion.py'), 'utf8');
  const i = py.indexOf('COMUNES = [');
  const bloque = py.slice(i, py.indexOf('\n]', i));
  const cab = {};
  let actual = null;
  for (const m of bloque.matchAll(/'([^']*)'|"([^"]*)"/g)) {
    const lit = m[1] !== undefined ? m[1] : m[2];
    const cabecera = lit.match(/^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$/);
    if (cabecera) { actual = cabecera[1]; cab[actual] = cabecera[2]; }
    else if (actual) { cab[actual] += lit; }
  }
  return cab;
}

const COMUNES = cabecerasComunes();

http.createServer((req, res) => {
  let ruta = decodeURIComponent(req.url.split('?')[0]);
  if (ruta === '/') ruta = '/index.html';
  const archivo = path.join(RAIZ, ruta);

  if (!archivo.startsWith(RAIZ) || !fs.existsSync(archivo) || fs.statSync(archivo).isDirectory()) {
    res.writeHead(404, { ...COMUNES, 'Content-Type': TIPOS['.html'] });
    const p404 = path.join(RAIZ, '404.html');
    return res.end(fs.existsSync(p404) ? fs.readFileSync(p404) : 'no encontrado');
  }

  res.writeHead(200, {
    ...COMUNES,
    'Content-Type': TIPOS[path.extname(archivo)] || 'application/octet-stream',
    'Cache-Control': 'no-store',
  });
  res.end(fs.readFileSync(archivo));
}).listen(8055, '127.0.0.1');
