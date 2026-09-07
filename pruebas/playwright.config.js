// Configuración de las pruebas.
//
// Usa el Edge que ya está instalado en el equipo (channel: 'msedge') en vez de
// descargar un navegador aparte: son varios cientos de megas que aquí no hacen
// falta, y además así se prueba en el mismo navegador que usa Pedro.
//
// Levanta un servidor estático sobre la carpeta del proyecto, porque la web
// se sirve así en Netlify.

const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  timeout: 45000,
  expect: { timeout: 8000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],

  use: {
    baseURL: 'http://127.0.0.1:8055',
    channel: 'msedge',
    headless: true,
    viewport: { width: 1600, height: 950 },
    actionTimeout: 8000,
    screenshot: 'only-on-failure',
  },

  webServer: {
    command: 'node servidor.js',
    url: 'http://127.0.0.1:8055/index.html',
    reuseExistingServer: true,
    timeout: 20000,
  },
});
