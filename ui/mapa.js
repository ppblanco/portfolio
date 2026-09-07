/* =============================================================
   MAPA DEL TRABAJO · grafo vivo de lo que comparte cada proyecto
   -------------------------------------------------------------
   Seis proyectos y las técnicas que los unen. Tres cosas que lo
   hacen sentir como el grafo de Obsidian y no como un dibujo:

     · La física corre siempre, no se calcula una vez y se congela.
       Los nodos se empujan, los enlaces tiran, y el conjunto
       respira. Eso es lo que da la sensación de estar vivo.
     · Se puede agarrar un nodo y arrastrarlo: toda la red
       reacciona. Es la interacción que más convence de que hay
       algo detrás y no una imagen.
     · Al pulsar un proyecto se ABRE su página de caso. Si alguno no
       tuviera página, baja a su ficha, que es lo que se hacía antes.
       Cada nodo lleva a un sitio distinto.

   Por qué no es el grafo de Obsidian entero: aquel se sostiene
   sobre unas doscientas notas y sirve para orientarse. Aquí hay
   catorce nodos elegidos; con cuatro puntos sueltos, un grafo de
   fuerzas se ve vacío. La densidad no se puede fingir.

   Todo en canvas y a mano: son 21 nodos, no hacen falta 90 KB de
   librería de grafos.
   ============================================================= */

(function () {
  'use strict';

  var quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var DATOS_NODOS = [
    { id: 'tfm', texto: 'Lead scoring',     tipo: 'obra', ficha: 'obra-tfm',
      pagina: 'trabajos/tfm-lead-scoring.html', grande: true },
    { id: 'vj',  texto: 'Ventas de juegos', tipo: 'obra', ficha: 'obra-videojuegos',
      pagina: 'trabajos/videojuegos.html' },
    { id: 'atp', texto: 'Casa de apuestas', tipo: 'obra', ficha: 'obra-apuestas',
      pagina: 'trabajos/apuestas.html' },
    { id: 'lip', texto: 'Lipton',           tipo: 'obra', ficha: 'obra-lipton',
      pagina: 'trabajos/lipton.html' },
    { id: 'dl',  texto: 'Demanda · RNN',    tipo: 'obra', ficha: 'obra-deeplearning',
      pagina: 'trabajos/deep-learning.html' },
    { id: 'ltb', texto: 'Letterboxd',       tipo: 'obra', ficha: 'obra-letterboxd',
      pagina: 'trabajos/letterboxd.html' },

    { id: 'py',   texto: 'Python',            tipo: 'tec' },
    { id: 'skl',  texto: 'scikit-learn',      tipo: 'tec' },
    { id: 'shap', texto: 'SHAP',              tipo: 'tec' },
    { id: 'pd',   texto: 'pandas',            tipo: 'tec' },
    { id: 'plot', texto: 'Plotly',            tipo: 'tec' },
    { id: 'rf',   texto: 'Random Forest',     tipo: 'tec' },
    { id: 'gb',   texto: 'Gradient Boosting', tipo: 'tec' },
    { id: 'eda',  texto: 'EDA',               tipo: 'tec' },
    { id: 'mkt',  texto: 'Captación',         tipo: 'tec' },
    { id: 'inv',  texto: 'Investigación',     tipo: 'tec' },
    { id: 'tf',   texto: 'TensorFlow',        tipo: 'tec' },
    { id: 'lstm', texto: 'LSTM',              tipo: 'tec' },
    { id: 'nlp',  texto: 'NLP',               tipo: 'tec' },
    { id: 'spa',  texto: 'spaCy',             tipo: 'tec' },
    { id: 'lda',  texto: 'LDA',               tipo: 'tec' }
  ];

  var ARISTAS = [
    ['tfm', 'py'], ['tfm', 'skl'], ['tfm', 'shap'], ['tfm', 'rf'], ['tfm', 'mkt'],
    ['vj', 'py'], ['vj', 'skl'], ['vj', 'shap'], ['vj', 'pd'], ['vj', 'plot'], ['vj', 'gb'],
    ['atp', 'py'], ['atp', 'pd'], ['atp', 'plot'], ['atp', 'eda'],
    ['lip', 'mkt'], ['lip', 'inv'],
    // Deep learning y Letterboxd. Solo lo que usan de verdad: las herramientas
    // salen de los README de cada proyecto, no de lo que quede bien.
    ['dl', 'py'], ['dl', 'pd'], ['dl', 'tf'], ['dl', 'lstm'],
    ['ltb', 'py'], ['ltb', 'pd'], ['ltb', 'nlp'], ['ltb', 'spa'], ['ltb', 'lda']
  ];

  var vecinos = {};
  DATOS_NODOS.forEach(function (n) { vecinos[n.id] = {}; });
  ARISTAS.forEach(function (a) {
    vecinos[a[0]][a[1]] = true;
    vecinos[a[1]][a[0]] = true;
  });

  /* ===========================================================
     Una instancia del mapa por lienzo. Hay dos: el de la sección
     de trabajos y el del panel que se abre desde la navegación.
     Cada uno lleva sus propias posiciones y su propia física.
     =========================================================== */
  function crearMapa(lienzo, opciones) {
    if (!lienzo || !lienzo.getContext) return null;
    var ctx = lienzo.getContext('2d');
    opciones = opciones || {};

    /* El color de senal se puede pasar por opciones. Por defecto es el cian de
       index.html, asi que esa pagina no cambia nada; index.html pasa su
       ambar. Se guarda como tres numeros para poder componer rgba() con la
       opacidad que toque en cada trazo. */
    var RGB = opciones.rgb || [111, 217, 232];
    function senal(a) { return 'rgba(' + RGB[0] + ',' + RGB[1] + ',' + RGB[2] + ',' + a + ')'; }
    var SENAL = 'rgb(' + RGB[0] + ',' + RGB[1] + ',' + RGB[2] + ')';

  // Copia propia de los nodos: dos mapas no comparten posiciones.
  var NODOS = DATOS_NODOS.map(function (n, i) {
    return { id: n.id, texto: n.texto, tipo: n.tipo, ficha: n.ficha, pagina: n.pagina,
             grande: n.grande, i: i, x: 0, y: 0, vx: 0, vy: 0 };
  });
  var porId = {};
  NODOS.forEach(function (n) { porId[n.id] = n; });

  // Semilla fija: la red arranca siempre igual, aunque luego se mueva.
  var semilla = 1077;
  function azar() {
    semilla = (semilla * 1103515245 + 12345) & 0x7fffffff;
    return semilla / 0x7fffffff;
  }

  var ancho = 0, alto = 0, dpr = 1;
  var encima = null, arrastrando = null, huboArrastre = false;

  function medir() {
    var caja = lienzo.getBoundingClientRect();
    var antesA = ancho, antesB = alto;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    ancho = Math.max(1, Math.round(caja.width));
    alto = Math.max(1, Math.round(caja.height));
    lienzo.width = Math.round(ancho * dpr);
    lienzo.height = Math.round(alto * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    if (antesA && antesB) {  // reescalar lo que ya había
      NODOS.forEach(function (n) {
        n.x = n.x / antesA * ancho;
        n.y = n.y / antesB * alto;
      });
    }
  }

  function sembrar() {
    NODOS.forEach(function (n, i) {
      var ang = (i / NODOS.length) * Math.PI * 2;
      var r = Math.min(ancho, alto) * (0.20 + azar() * 0.14);
      n.x = ancho / 2 + Math.cos(ang) * r * 1.6;
      n.y = alto / 2 + Math.sin(ang) * r;
      n.vx = 0; n.vy = 0;
    });
  }

  function radio(n) {
    var base = n.tipo === 'obra' ? (n.grande ? 9 : 7.5) : 4.2;
    return opciones.compacto ? base * 0.82 : base;
  }

  // En el cuadro pequeño solo se rotulan los proyectos: catorce nombres en
  // 250 píxeles no se leen, se amontonan. Las técnicas salen al señalarlas.
  function conEtiqueta(n) {
    if (!opciones.compacto) return true;
    return n.tipo === 'obra' || n.id === encima || (encima && vecinos[encima][n.id]);
  }

  // ---- Física, un paso ------------------------------------------
  var LARGO = 0;   // distancia de reposo de los enlaces
  function paso() {
    LARGO = Math.min(ancho, alto) * 0.24;

    for (var i = 0; i < NODOS.length; i++) {
      for (var j = i + 1; j < NODOS.length; j++) {
        var a = NODOS[i], b = NODOS[j];
        var dx = b.x - a.x, dy = b.y - a.y;
        var d2 = dx * dx + dy * dy + 40;
        var d = Math.sqrt(d2);
        var f = 5200 / d2;            // repulsión
        a.vx -= dx / d * f; a.vy -= dy / d * f;
        b.vx += dx / d * f; b.vy += dy / d * f;
      }
    }

    ARISTAS.forEach(function (e) {
      var a = porId[e[0]], b = porId[e[1]];
      var dx = b.x - a.x, dy = b.y - a.y;
      var d = Math.hypot(dx, dy) + 1e-6;
      // Hooke a secas: la fuerza es proporcional a lo estirado que está el
      // muelle, y va en la dirección del enlace. Aquí había un factor d de
      // más que la hacía crecer con el cuadrado de la distancia y aplastaba
      // el grafo contra las paredes.
      var f = (d - LARGO) * 0.012;
      a.vx += dx / d * f; a.vy += dy / d * f;
      b.vx -= dx / d * f; b.vy -= dy / d * f;
    });

    NODOS.forEach(function (n) {
      // hacia el centro, flojito, para que no se vaya a las esquinas
      n.vx += (ancho / 2 - n.x) * 0.0016;
      n.vy += (alto / 2 - n.y) * 0.0016;

      // Aquí hubo dos cosas que quedaban vistosas y eran un estorbo: una
      // fuerza que apartaba los nodos del puntero, y un temblor constante
      // para que la red no se congelara nunca. Con las dos, el nodo se movía
      // justo cuando ibas a pulsarlo. Un grafo que esquiva el ratón no se
      // puede usar. Ahora la red se asienta y se queda quieta, y vuelve a
      // moverse cuando la arrastras, que es como se comporta la de Obsidian.

      n.vx *= 0.90; n.vy *= 0.90;      // rozamiento

      if (n === arrastrando) return;    // el que se arrastra manda
      n.x += n.vx; n.y += n.vy;

      // paredes blandas, con sitio para la etiqueta que se vaya a dibujar
      var margenX = conEtiqueta(n) ? (n.tipo === 'obra' ? 100 : 84) : 16;
      var margenY = radio(n) + 12;
      if (n.x < margenX) { n.x = margenX; n.vx *= -0.4; }
      if (n.x > ancho - margenX) { n.x = ancho - margenX; n.vx *= -0.4; }
      if (n.y < margenY) { n.y = margenY; n.vy *= -0.4; }
      if (n.y > alto - margenY) { n.y = alto - margenY; n.vy *= -0.4; }
    });
  }

  // ---- Pintado ---------------------------------------------------
  function vivoNodo(n) {
    if (!encima) return true;
    return n.id === encima || vecinos[encima][n.id];
  }

  // Cajas de las etiquetas ya dibujadas. Si dos nodos quedan cerca, sus
  // nombres se pisan y no se lee ninguno; esto empuja el segundo arriba o
  // abajo hasta que hay hueco. Los proyectos se dibujan primero, así que
  // son los que se quedan en su sitio.
  var ocupado = [];
  function hueco(x, y, w, h) {
    for (var i = 0; i < ocupado.length; i++) {
      var o = ocupado[i];
      if (x < o.x + o.w && x + w > o.x && y < o.y + o.h && y + h > o.y) return false;
    }
    return true;
  }

  function pintar() {
    ctx.clearRect(0, 0, ancho, alto);
    ocupado.length = 0;

    ARISTAS.forEach(function (e) {
      var a = porId[e[0]], b = porId[e[1]];
      var vivo = !encima || e[0] === encima || e[1] === encima;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = vivo ? senal(.42) : 'rgba(255,255,255,.06)';
      ctx.lineWidth = vivo ? 1.2 : 1;
      ctx.stroke();
    });

    NODOS.forEach(function (n) {
      var vivo = vivoNodo(n);
      var esObra = n.tipo === 'obra';
      var r = radio(n) + (n.id === encima ? 2.5 : 0);

      if (esObra) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r * 3.2, 0, Math.PI * 2);
        ctx.fillStyle = senal(vivo ? .11 : .03);
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = esObra
        ? (vivo ? SENAL : senal(.22))
        : (vivo ? 'rgba(255,255,255,.78)' : 'rgba(255,255,255,.16)');
      ctx.fill();

      if (!conEtiqueta(n)) return;

      var cuerpo = opciones.compacto ? (esObra ? 11 : 10.5) : (esObra ? 13 : 11.5);
      ctx.font = (esObra ? '600 ' : '') + cuerpo + 'px "Barlow Condensed", sans-serif';
      var derecha = n.x > ancho / 2;
      ctx.textAlign = derecha ? 'left' : 'right';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = esObra
        ? (vivo ? '#FFFFFF' : 'rgba(255,255,255,.24)')
        : (vivo ? 'rgba(255,255,255,.62)' : 'rgba(255,255,255,.16)');

      var texto = esObra ? n.texto.toUpperCase() : n.texto;
      var w = ctx.measureText(texto).width;
      var h = cuerpo + 2;
      var tx = n.x + (derecha ? 1 : -1) * (r + (opciones.compacto ? 6 : 9));
      var izq = derecha ? tx : tx - w;

      // Se prueban desplazamientos hasta encontrar sitio libre.
      var ty = n.y;
      for (var d = 0; d < 5; d++) {
        var prueba = n.y + [0, -13, 13, -25, 25][d];
        if (hueco(izq, prueba - h / 2, w, h)) { ty = prueba; break; }
        ty = prueba;
      }
      ocupado.push({ x: izq, y: ty - h / 2, w: w, h: h });
      ctx.fillText(texto, tx, ty);
    });
  }

  // ---- Interacción ------------------------------------------------
  function nodoEn(mx, my) {
    var mejor = null, mejorD = 26;   // radio de acierto generoso: son puntos pequeños
    NODOS.forEach(function (n) {
      var d = Math.hypot(n.x - mx, n.y - my);
      if (d < mejorD) { mejorD = d; mejor = n; }
    });
    return mejor;
  }

  function coords(e) {
    var caja = lienzo.getBoundingClientRect();
    return { x: e.clientX - caja.left, y: e.clientY - caja.top };
  }

  lienzo.addEventListener('pointerdown', function (e) {
    var p = coords(e);
    var n = nodoEn(p.x, p.y);
    if (!n) return;
    arrastrando = n;
    huboArrastre = false;
    lienzo.setPointerCapture(e.pointerId);
    lienzo.style.cursor = 'grabbing';
    despertar();          // la física se había dormido al asentarse
  });

  lienzo.addEventListener('pointermove', function (e) {
    var p = coords(e);

    if (arrastrando) {
      if (Math.hypot(arrastrando.x - p.x, arrastrando.y - p.y) > 3) huboArrastre = true;
      arrastrando.x = p.x; arrastrando.y = p.y;
      arrastrando.vx = 0; arrastrando.vy = 0;
      return;
    }

    var n = nodoEn(p.x, p.y);
    var nuevo = n ? n.id : null;
    if (nuevo !== encima) {
      encima = nuevo;
      lienzo.style.cursor = n ? (n.tipo === 'obra' ? 'pointer' : 'grab') : 'default';
      pintar();   // el resaltado tiene que verse aunque la física esté dormida
    }
  });

  function soltar(e) {
    if (arrastrando) {
      // Si no se arrastró, era un clic: abre SU trabajo.
      if (!huboArrastre) irA(arrastrando);
      arrastrando = null;
      lienzo.style.cursor = encima ? 'pointer' : 'default';
    }
    if (e && e.pointerId != null && lienzo.hasPointerCapture(e.pointerId)) {
      lienzo.releasePointerCapture(e.pointerId);
    }
  }
  lienzo.addEventListener('pointerup', soltar);
  lienzo.addEventListener('pointercancel', soltar);

  lienzo.addEventListener('pointerleave', function () {
    if (encima) { encima = null; lienzo.style.cursor = 'default'; pintar(); }
  });

  function irA(nodo) {
    if (!nodo) return;

    /* ABRE EL TRABAJO, no baja a su ficha. Desde el 02/09/2026 los cuatro
       proyectos tienen su página de caso, así que bajar a la tarjeta dejaba
       a quien pulsaba a un clic todavía de lo que había ido a ver. Con la
       tarjeta era lo único que se podía hacer; ahora ya no.

       Si algún proyecto se quedara sin página, sigue funcionando el
       comportamiento de antes: bajar a su ficha. */
    if (nodo.pagina) {
      window.location.href = nodo.pagina;
      return;
    }

    var ficha = document.getElementById(nodo.ficha);
    if (!ficha) return;
    if (opciones.alNavegar) opciones.alNavegar();   // el panel se cierra solo
    ficha.scrollIntoView({ behavior: quieto ? 'auto' : 'smooth', block: 'center' });
    // Un destello corto para que se vea dónde has aterrizado.
    ficha.classList.remove('esta-senalada');
    void ficha.offsetWidth;              // reinicia la animación
    ficha.classList.add('esta-senalada');
    setTimeout(function () { ficha.classList.remove('esta-senalada'); }, 1600);
  }

  // ---- Ciclo -------------------------------------------------------
  // La red corre mientras tenga energía y se para al asentarse. Así se ve
  // colocarse al llegar, reacciona al arrastrarla, y el resto del tiempo
  // está quieta para que se pueda pulsar. Y de paso no gasta batería.
  var corriendo = false, aLaVista = false;

  function energia() {
    var e = 0;
    for (var i = 0; i < NODOS.length; i++) {
      e += NODOS[i].vx * NODOS[i].vx + NODOS[i].vy * NODOS[i].vy;
    }
    return e;
  }

  function bucle() {
    if (!corriendo) return;
    paso();
    pintar();
    if (!arrastrando && energia() < 0.06) { corriendo = false; return; }
    requestAnimationFrame(bucle);
  }

  function despertar() {
    // La clase la escribe el boton de "parar movimiento" del portfolio. En
    // index.html no existe nunca, asi que alli esto siempre es false y el
    // comportamiento no cambia. Sin esta linea el grafo seguia moviendose
    // despues de pulsar el boton, que era el unico animado que se lo saltaba.
    if (document.documentElement.classList.contains('sin-movimiento')) return;
    if (corriendo || quieto || !aLaVista) return;
    corriendo = true;
    requestAnimationFrame(bucle);
  }

  medir();
  sembrar();
  for (var k = 0; k < 60; k++) paso();   // un empujón, no del todo colocado:
  pintar();                              // se termina de asentar a la vista

  if (opciones.enPanel) {
    // El panel no está en el flujo: se despierta cuando se abre.
    aLaVista = false;
  } else if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (ent) {
      aLaVista = ent[0].isIntersecting;
      if (aLaVista) despertar(); else corriendo = false;
    }, { threshold: 0.12 }).observe(lienzo);
  } else {
    aLaVista = true; despertar();
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) corriendo = false; else despertar();
  });

  var temp;
  window.addEventListener('resize', function () {
    clearTimeout(temp);
    temp = setTimeout(function () { medir(); pintar(); }, 150);
  });

    return {
      // Al abrir el panel hay que medir de nuevo: hasta entonces el lienzo
      // estaba oculto y su tamaño era cero.
      mostrar: function () {
        aLaVista = true;
        medir();
        if (NODOS[0].x === 0 && NODOS[0].y === 0) sembrar();
        despertar();
        pintar();
      },
      ocultar: function () { aLaVista = false; corriendo = false; },

      /* Volver del "parar movimiento" NO es lo mismo que abrir el panel.
         mostrar() fuerza aLaVista=true porque el panel acaba de aparecer;
         llamarlo al reanudar deja esa bandera clavada aunque el mapa este a
         tres pantallas de distancia, y su fisica se queda corriendo para
         siempre. Medido: 121 llamadas a requestAnimationFrame por segundo en
         vez de 60. Esto solo empuja el bucle y deja que despertar() decida,
         que ya comprueba si el lienzo esta a la vista. */
      reanudar: function () { despertar(); }
    };
  }

  /* Se expone la fabrica para que otras paginas puedan montar su propio
     mapa sin duplicar 400 lineas de fisica. index.html sigue usando las
     instancias de abajo; index.html llama a esto con su lienzo. */
  window.crearMapa = crearMapa;

  /* ---- Instancias ---------------------------------------------- */

  // 1. El cuadro flotante de la derecha
  var mini = document.getElementById('mini-mapa');
  var mapaMini = crearMapa(document.getElementById('mapa-mini'), { compacto: true });

  if (mini && mapaMini) {
    // No sale en la portada: ahí taparía el titular y no hay nada que
    // navegar todavía. Aparece cuando el visitante ya está dentro.
    var portada = document.getElementById('portada');
    if (portada && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (ent) {
        mini.classList.toggle('esta-visible', !ent[0].isIntersecting);
      }, { threshold: 0.25 }).observe(portada);
    } else {
      mini.classList.add('esta-visible');
    }

    // Plegar y desplegar. Antes había una ✕ que lo escondía para siempre:
    // se cerraba sin querer y no había forma de recuperarlo. Ahora se pliega
    // a su barra, que sigue ahí, y se vuelve a abrir pulsándola.
    var pliegue = document.getElementById('plegar-mapa');
    if (pliegue) {
      pliegue.addEventListener('click', function () {
        var plegado = mini.classList.toggle('esta-plegado');
        pliegue.setAttribute('aria-expanded', plegado ? 'false' : 'true');
        if (plegado) mapaMini.ocultar(); else mapaMini.mostrar();
      });
    }
  }

  // 2. El panel grande
  var panel = document.getElementById('panel-mapa');
  var boton = document.getElementById('abrir-mapa');
  var ampliar = document.getElementById('ampliar-mapa');
  if (panel && boton) {
    var cerrar = function () {
      panel.hidden = true;
      boton.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
      if (mapaPanel) mapaPanel.ocultar();
      boton.focus();
    };

    var mapaPanel = crearMapa(document.getElementById('mapa-panel'),
                              { enPanel: true, alNavegar: cerrar });

    var abrir = function () {
      panel.hidden = false;
      boton.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
      if (mapaPanel) mapaPanel.mostrar();
      var salir = panel.querySelector('.panel-mapa__cerrar');
      if (salir) salir.focus();
    };

    boton.addEventListener('click', abrir);
    if (ampliar) ampliar.addEventListener('click', abrir);   // el ⤢ del cuadro

    panel.addEventListener('click', function (e) {
      if (e.target === panel || e.target.closest('.panel-mapa__cerrar')) cerrar();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !panel.hidden) cerrar();
    });
  }
})();
