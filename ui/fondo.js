/* =============================================================
   FONDO · una red de datos funcionando por detrás
   -------------------------------------------------------------
   Nodos que van a la deriva muy despacio, conexiones que aparecen
   cuando dos se acercan, y de vez en cuando un dato que viaja por
   una de esas conexiones y se apaga al llegar. Nada más.

   Por qué NO comparte motor con ui/mapa.js. Se estudió: aquel es
   un grafo de fuerzas con catorce nodos FIJOS, aristas FIJAS,
   muelles de Hooke, etiquetas que se esquivan y arrastre con el
   ratón. Esto es un campo de puntos a la deriva con aristas por
   proximidad. Lo único que comparten es "lienzo y un bucle", que
   son treinta líneas; unificarlos obligaría a que cada uno cargara
   con las ramas del otro en cada fotograma. Lo que sí se comparte,
   que es lo que importa, es el ESTADO: los dos se paran con el
   mismo interruptor y con la misma preferencia del sistema.

   Reglas que no se pueden romper:
     · Un solo requestAnimationFrame, y se cancela al pausar.
     · Cero reservas de memoria dentro del bucle. Todo lo que se
       usa por fotograma está reservado de antemano.
     · El lienzo va fijo a la ventana y detrás de todo, sin tocar
       las dimensiones del documento ni robar un solo clic.
     · Menos es más. Ante la duda, menos partículas.
   ============================================================= */

(function () {
  'use strict';

  var lienzo = document.getElementById('fondo');
  if (!lienzo || !lienzo.getContext) return;

  var raiz = document.documentElement;
  var ctx = lienzo.getContext('2d', { alpha: true });
  var QUIETO = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var FINO = window.matchMedia('(hover:hover) and (pointer:fine)').matches;

  /* El mismo estado que el botón del pie. No hay un segundo sistema de pausa:
     se lee la clase que ese botón escribe en <html>. */
  function pausado() { return raiz.classList.contains('sin-movimiento'); }

  // Avisa al CSS de que el lienzo está montado, para que apague los puntos de
  // respaldo. Sin JavaScript se quedan ellos y el fondo no se ve plano.
  raiz.classList.add('con-fondo');

  /* ---- Ajustes -------------------------------------------------
     UNO_CADA es el área en píxeles que le toca a cada nodo. La
     densidad sale del área disponible y no de un punto de corte:
     así un móvil de 375 lleva unos catorce nodos y un monitor de
     1440 unos cincuenta, sin escribir tres números a mano. */
  var UNO_CADA = 13000, MIN_NODOS = 18, MAX_NODOS = 96;
  var CERCA = 205;          // a partir de aquí dos nodos se enlazan
  var MAX_ARISTAS = 160;    // techo duro: la densidad no puede dispararse
  var SOCIABLE = 0.62;      // qué parte de los nodos admite conexiones
  var RATON_CERCA = 150, RATON_EMPUJE = 3;

  var ancho = 0, alto = 0, dpr = 1;
  var nodos = [], particulas = [];
  var arA = null, arB = null, arAlfa = null, nAristas = 0;

  var cuadro = null, antes = 0;
  var ratonX = -9999, ratonY = -9999;

  // Atenuación global. Baja cuando se llega a la sección del mapa: dos redes
  // a la vez es una red encima de otra, y la del mapa es la que manda.
  var velo = 1, veloMeta = 1;

  /* ---- Semilla propia ------------------------------------------
     Un generador propio para que el fondo salga igual en cada
     visita. Math.random daría una red distinta cada vez, y eso
     hace imposible comparar dos capturas. */
  var semilla = 20260826;
  function azar() {
    semilla = (semilla * 1103515245 + 12345) & 0x7fffffff;
    return semilla / 0x7fffffff;
  }

  /* ---- El pasillo del contenido --------------------------------
     El texto vive en una columna centrada de 1180px. Un nodo justo
     detrás de un párrafo es ruido encima de lo único que hay que
     leer, así que el centro se atenúa: los nodos que caen ahí
     nacen menos y los que se meten a la deriva se apagan solos.
     La cuenta es una curva suave, no un recorte, para que no se
     vea el borde del pasillo. */
  function despejado(x) {
    var medio = ancho / 2;
    // 760px, no los 1180 del contenedor. Se probó con el contenedor entero y a
    // 1440 el pasillo se comía toda la pantalla menos 130px por lado: el fondo
    // quedaba literalmente invisible. Lo que hay que proteger es la columna
    // donde cae el texto corrido, no el ancho del marco.
    var mitad = Math.min(ancho, 760) / 2;
    var d = Math.abs(x - medio) / (mitad || 1);   // 0 en el centro, 1 en el borde
    if (d >= 1) return 1;
    return 0.42 + 0.58 * (d * d);                 // hasta el 42% en el eje
  }

  function medir() {
    var caja = lienzo.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    ancho = Math.max(1, Math.round(caja.width));
    alto = Math.max(1, Math.round(caja.height));
    lienzo.width = Math.round(ancho * dpr);
    lienzo.height = Math.round(alto * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function sembrar() {
    var cuantos = Math.round((ancho * alto) / UNO_CADA);
    cuantos = Math.max(MIN_NODOS, Math.min(MAX_NODOS, cuantos));

    nodos.length = 0;
    for (var i = 0; i < cuantos; i++) {
      // Muestreo por rechazo: se tiran hasta seis posiciones y se queda la
      // primera que caiga fuera del pasillo del contenido. Más barato y más
      // natural que repartirlos por zonas a mano.
      var x = 0, y = 0;
      for (var intento = 0; intento < 6; intento++) {
        x = azar() * ancho;
        y = azar() * alto;
        if (azar() < despejado(x)) break;
      }
      var z = azar();                        // 0 lejos, 1 cerca
      nodos.push({
        x: x, y: y,
        // La deriva va con la profundidad: lo cercano se mueve más, y eso es
        // lo que da sensación de capas sin dibujar ninguna.
        vx: (azar() - 0.5) * (0.05 + z * 0.11),
        vy: (azar() - 0.5) * (0.05 + z * 0.11),
        z: z,
        r: 0.9 + z * 1.7,
        // Unos pocos en blanco cálido, el resto en ámbar. Sin mezclar al 50%:
        // el ámbar es el color de la casa y el blanco es el acento del acento.
        blanco: azar() < 0.22,
        social: azar() < SOCIABLE,
        brillo: 0,
        dx: 0, dy: 0
      });
    }

    // Aristas y partículas, reservadas de una vez y para siempre.
    arA = new Int16Array(MAX_ARISTAS);
    arB = new Int16Array(MAX_ARISTAS);
    arAlfa = new Float32Array(MAX_ARISTAS);

    var cuantasP = Math.max(3, Math.min(12, Math.round(cuantos / 8)));
    particulas.length = 0;
    for (var k = 0; k < cuantasP; k++) {
      particulas.push({
        viva: false, a: 0, b: 0, t: 0,
        vel: 0, tam: 0, alfa: 0,
        espera: azar() * 3.5
      });
    }
  }

  /* ---- Un fotograma --------------------------------------------
     Orden: mover, buscar aristas, mover partículas, pintar. Ni una
     sola reserva de memoria aquí dentro. */
  function mover(dt) {
    for (var i = 0; i < nodos.length; i++) {
      var n = nodos[i];
      n.x += n.vx * dt * 60;
      n.y += n.vy * dt * 60;

      // Al salir por un borde reaparece por el contrario. Un rebote crearía
      // acumulaciones en las esquinas y se notaría el marco.
      if (n.x < -20) n.x = ancho + 20; else if (n.x > ancho + 20) n.x = -20;
      if (n.y < -20) n.y = alto + 20; else if (n.y > alto + 20) n.y = -20;

      // El ratón: unos pocos píxeles y un poco de brillo. Nada que se pueda
      // llamar perseguir.
      var ex = 0, ey = 0, cerca = 0;
      if (FINO && ratonX > -9000) {
        var ddx = n.x - ratonX, ddy = n.y - ratonY;
        var d2 = ddx * ddx + ddy * ddy;
        if (d2 < RATON_CERCA * RATON_CERCA) {
          var d = Math.sqrt(d2) || 1;
          cerca = 1 - d / RATON_CERCA;
          ex = (ddx / d) * cerca * RATON_EMPUJE;
          ey = (ddy / d) * cerca * RATON_EMPUJE;
        }
      }
      n.dx += (ex - n.dx) * 0.08;
      n.dy += (ey - n.dy) * 0.08;
      n.brillo += (cerca - n.brillo) * 0.08;
    }
  }

  function buscarAristas() {
    nAristas = 0;
    var lim = CERCA * CERCA;
    for (var i = 0; i < nodos.length && nAristas < MAX_ARISTAS; i++) {
      var a = nodos[i];
      if (!a.social) continue;
      for (var j = i + 1; j < nodos.length && nAristas < MAX_ARISTAS; j++) {
        var b = nodos[j];
        if (!b.social) continue;
        var dx = (a.x + a.dx) - (b.x + b.dx);
        var dy = (a.y + a.dy) - (b.y + b.dy);
        var d2 = dx * dx + dy * dy;
        if (d2 > lim) continue;
        // Se apaga con la distancia y con lo lejos que estén los dos nodos.
        var f = 1 - Math.sqrt(d2) / CERCA;
        arA[nAristas] = i;
        arB[nAristas] = j;
        arAlfa[nAristas] = f * f * (0.35 + (a.z + b.z) * 0.32);
        nAristas++;
      }
    }
  }

  function moverParticulas(dt) {
    for (var i = 0; i < particulas.length; i++) {
      var p = particulas[i];
      if (!p.viva) {
        p.espera -= dt;
        if (p.espera > 0 || nAristas === 0) continue;
        // Sale por una arista al azar de las que existen AHORA. Si se guardara
        // la arista de antes, el dato viajaría por una línea que ya no está.
        var e = (azar() * nAristas) | 0;
        p.a = arA[e]; p.b = arB[e];
        p.t = 0;
        p.vel = 0.22 + azar() * 0.5;
        p.tam = 1.0 + azar() * 1.1;
        p.alfa = 0.5 + azar() * 0.5;
        p.viva = true;
        continue;
      }
      p.t += p.vel * dt;
      if (p.t >= 1) {
        p.viva = false;
        p.espera = 0.8 + azar() * 4.5;   // aparecen irregulares, no en fila
      }
    }
  }

  function pintar() {
    ctx.clearRect(0, 0, ancho, alto);
    if (velo < 0.02) return;

    var i, n;

    // 1. Conexiones. Muy tenues: son el andamio, no el dibujo.
    ctx.lineWidth = 1;
    for (i = 0; i < nAristas; i++) {
      var a = nodos[arA[i]], b = nodos[arB[i]];
      var al = arAlfa[i] * 0.44 * velo * despejado((a.x + b.x) / 2);
      if (al < 0.004) continue;
      ctx.strokeStyle = 'rgba(224,164,88,' + al.toFixed(3) + ')';
      ctx.beginPath();
      ctx.moveTo(a.x + a.dx, a.y + a.dy);
      ctx.lineTo(b.x + b.dx, b.y + b.dy);
      ctx.stroke();
    }

    // 2. Nodos. Los lejanos llevan un halo suave en vez de un desenfoque de
    //    verdad: ctx.filter cuesta un mundo por fotograma y esto se lee igual.
    for (i = 0; i < nodos.length; i++) {
      n = nodos[i];
      var x = n.x + n.dx, y = n.y + n.dy;
      var base = (0.36 + n.z * 0.58 + n.brillo * 0.3) * velo * despejado(x);
      if (base < 0.006) continue;
      var color = n.blanco ? '255,244,232' : '224,164,88';

      if (n.z < 0.45) {
        ctx.fillStyle = 'rgba(' + color + ',' + (base * 0.4).toFixed(3) + ')';
        ctx.beginPath();
        ctx.arc(x, y, n.r * 2.6, 0, 6.283185);
        ctx.fill();
      }
      ctx.fillStyle = 'rgba(' + color + ',' + base.toFixed(3) + ')';
      ctx.beginPath();
      ctx.arc(x, y, n.r, 0, 6.283185);
      ctx.fill();
    }

    // 3. Los datos que viajan. Es lo único que se permite brillar.
    for (i = 0; i < particulas.length; i++) {
      var p = particulas[i];
      if (!p.viva) continue;
      var na = nodos[p.a], nb = nodos[p.b];
      if (!na || !nb) continue;
      // Entra y sale con una curva suave: aparecer y desaparecer de golpe en
      // mitad de una línea se ve como un parpadeo.
      var borde = Math.min(1, Math.min(p.t, 1 - p.t) * 6);
      var px = na.x + na.dx + ((nb.x + nb.dx) - (na.x + na.dx)) * p.t;
      var py = na.y + na.dy + ((nb.y + nb.dy) - (na.y + na.dy)) * p.t;
      var al2 = p.alfa * borde * velo * despejado(px);
      if (al2 < 0.01) continue;

      ctx.fillStyle = 'rgba(240,196,124,' + (al2 * 0.22).toFixed(3) + ')';
      ctx.beginPath();
      ctx.arc(px, py, p.tam * 3.2, 0, 6.283185);
      ctx.fill();
      ctx.fillStyle = 'rgba(255,226,178,' + al2.toFixed(3) + ')';
      ctx.beginPath();
      ctx.arc(px, py, p.tam, 0, 6.283185);
      ctx.fill();
    }
  }

  function paso(ahora) {
    /* La guarda va DENTRO del bucle, no solo en parar(). Un fotograma que ya
       estaba despachándose cuando llegó la pausa termina su trabajo y vuelve a
       pedir el siguiente DESPUÉS de que cancelAnimationFrame haya cancelado el
       anterior: el identificador nuevo se guarda encima y nadie lo cancela.
       Medido: tres repintados a 17ms de haber pulsado "parar". Comprobándolo
       aquí, ese fotograma huérfano no mueve nada y no se reprograma. */
    if (QUIETO || pausado() || document.hidden) { cuadro = null; return; }

    // Un salto de pestaña puede devolver un dt enorme; se recorta o los nodos
    // aparecen al otro lado de la pantalla de golpe.
    var dt = Math.min(0.05, (ahora - antes) / 1000) || 0.016;
    antes = ahora;

    velo += (veloMeta - velo) * 0.06;

    mover(dt);
    buscarAristas();
    moverParticulas(dt);
    pintar();

    cuadro = window.requestAnimationFrame(paso);
  }

  /* ---- Arrancar y parar ----------------------------------------
     Un solo bucle. arrancar() no hace nada si ya hay uno, así que
     no se pueden duplicar por muchas veces que se llame. */
  function arrancar() {
    if (cuadro || QUIETO || pausado() || document.hidden) return;
    antes = window.performance.now();
    cuadro = window.requestAnimationFrame(paso);
  }
  function parar() {
    if (cuadro) { window.cancelAnimationFrame(cuadro); cuadro = null; }
  }

  /* Con movimiento reducido: una sola pasada, sin partículas y sin conexiones
     encendidas por nadie. Queda una red quieta y muy tenue, que es lo máximo
     que se puede ofrecer sin mover nada. */
  function estatico() {
    velo = 0.55; veloMeta = 0.55;
    buscarAristas();
    for (var i = 0; i < particulas.length; i++) particulas[i].viva = false;
    pintar();
  }

  function reiniciar() {
    medir();
    sembrar();
    if (QUIETO || pausado()) { parar(); estatico(); }
    else arrancar();
    // El fundido se enciende DESPUÉS del primer dibujo, nunca antes: si se
    // encendiera al montar, se vería aparecer un lienzo vacío y luego la red
    // encima, que es justo el parpadeo que el fundido viene a evitar.
    if (!lienzo.classList.contains('esta-encendido')) {
      window.requestAnimationFrame(function () {
        lienzo.classList.add('esta-encendido');
      });
    }
  }

  /* ---- Escuchas. Una de cada, y todas pasivas. ------------------ */

  if (FINO && !QUIETO) {
    window.addEventListener('pointermove', function (ev) {
      if (ev.pointerType === 'touch') return;
      ratonX = ev.clientX; ratonY = ev.clientY;
    }, { passive: true });
    window.addEventListener('pointerleave', function () {
      ratonX = -9999; ratonY = -9999;
    }, { passive: true });
  }

  var tempo = null;
  window.addEventListener('resize', function () {
    clearTimeout(tempo);
    tempo = setTimeout(reiniciar, 180);
  });

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) parar(); else arrancar();
  });

  /* El interruptor del pie no lanza ningún evento: solo escribe una clase en
     <html>. Se vigila esa clase, que además es el estado que ya usan el resto
     de animaciones. Así el botón sigue siendo uno y este fondo no inventa su
     propio sistema de pausa. */
  new MutationObserver(function () {
    if (pausado()) { parar(); estatico(); }
    else if (!QUIETO) arrancar();
  }).observe(raiz, { attributes: true, attributeFilter: ['class'] });

  /* Al llegar a la sección del mapa, el fondo se retira. Dos redes a la vez
     se leen como una red encima de otra, y la del mapa es la que cuenta algo.
     Se atenúa, no se apaga: apagarlo de golpe se nota más que dejarlo. */
  var seccionMapa = document.getElementById('mapa');
  if (seccionMapa && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (ent) {
      var nuevo = ent[0].isIntersecting ? 0.22 : 1;
      // Solo si de verdad cambia. Parado, cada aviso del observador volvía a
      // pintar el lienzo entero con el mismo resultado: trabajo tirado, y
      // además hacía que una red "quieta" tuviera fotogramas distintos.
      if (nuevo === veloMeta) return;
      veloMeta = nuevo;
      if (QUIETO || pausado()) { velo = veloMeta; estatico(); }
    }, { threshold: 0.25 }).observe(seccionMapa);
  }

  reiniciar();
})();
