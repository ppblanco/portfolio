/* =============================================================
   PLANTILLA · comportamiento del portfolio
   -------------------------------------------------------------
   Regla de toda la página: el contenido se sirve visible y es el
   JavaScript el que se ofrece a esconderlo para animarlo. Si este
   archivo no llega a ejecutarse, no se pierde nada: el menú se ve,
   el carrusel se desplaza con el dedo o la rueda, los acordeones
   son <details> de verdad y el mapa simplemente no está.

   Bloques:
     1. Aparición al entrar en pantalla, con escalonado
     2. Menú plegable de la barra
     3. Barra que se aparta al bajar y vuelve al subir
     4. Barra de avance de lectura
     5. Carrusel de trabajos
     6. Mapa del trabajo (el grafo de ui/mapa.js)
     7. Foco de luz y ladeo de las fichas
     8. El saludo se escribe y se corrige solo
     9. Formacion: filas que se abren al pasar por encima
    10. Entrada del titular, palabra a palabra
    11. El anillo que acompana al puntero
    12. La llamada flotante de contacto
    13. Interruptor de movimiento
   ============================================================= */

(function () {
  'use strict';

  var raiz = document.documentElement;
  var QUIETO = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var FINO = window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  var HAY_IO = 'IntersectionObserver' in window;

  function pausado() { return raiz.classList.contains('sin-movimiento'); }

  /* La preferencia guardada se aplica AQUI, lo primero de todo, y no abajo
     con el resto del interruptor.

     El motivo es un fallo real: el bloque del video de portada (13 ter) se
     ejecuta antes que el del interruptor (13), asi que preguntaba por
     html.sin-movimiento cuando la clase todavia no estaba puesta. Con el
     movimiento parado y guardado, el video se veia asi: arrancaba, pedia el
     archivo -los 1,8 MB del data-src- y se paraba un instante despues,
     cuando el interruptor por fin leia localStorage. Justo lo que
     preload="none" y el data-src estaban puestos para evitar.

     El interruptor sigue llamando a aplicar() mas abajo: eso pone el texto
     del boton y el aria-pressed. Esto solo adelanta la clase. */
  var CLAVE_MOVIMIENTO = 'plantilla-sin-movimiento';
  try {
    if (window.localStorage.getItem(CLAVE_MOVIMIENTO) === '1') {
      raiz.classList.add('sin-movimiento');
    }
  } catch (err) { /* modo privado: se sigue sin preferencia guardada */ }

  /* ---- 1. Aparición al entrar en pantalla ---------------------
     Dos detalles que separan esto de un revelado corriente:

     · Lo que ya está en pantalla se marca como visible ANTES de
       encender la clase que esconde. Si no, el contenido de la
       portada parpadea: se ve, desaparece y vuelve.
     · El escalonado se calcula aquí, contando la posición entre
       hermanos, en vez de escribir un retraso a mano en cada
       etiqueta del HTML. Añadir un bloque no obliga a renumerar
       los de al lado. */
  var porRevelar = [].slice.call(document.querySelectorAll('[data-revelar]'));
  if (porRevelar.length && HAY_IO && !QUIETO) {
    porRevelar.forEach(function (el) {
      if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add('esta-visible');
    });
    raiz.classList.add('con-revelado');
    try {
      var vigia = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (en) {
          if (!en.isIntersecting) return;
          var el = en.target;
          var hermanos = [].slice.call(el.parentElement.querySelectorAll(':scope > [data-revelar]'));
          var i = Math.max(0, hermanos.indexOf(el));
          el.style.transitionDelay = (i * 0.08).toFixed(2) + 's';
          el.classList.add('esta-visible');
          vigia.unobserve(el);
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
      porRevelar.forEach(function (el) { vigia.observe(el); });
    } catch (err) {
      // Si el observador no llegó a engancharse, mejor enseñarlo todo que
      // dejar la página en negro.
      raiz.classList.remove('con-revelado');
    }
  }

  /* ---- 2. Menú de la barra ------------------------------------
     Nace desplegado y es el script el que lo pliega: si fallara,
     queda abierto —feo pero usable— en vez de cerrado y sin botón
     que lo abra, que sería navegación perdida. */
  var boton = document.getElementById('menu');
  var lista = document.getElementById('menu-lista');
  var estrecha = window.matchMedia('(max-width:860px)');

  if (boton && lista) {
    var plegar = function (si) {
      lista.hidden = si;
      boton.setAttribute('aria-expanded', String(!si));
      boton.querySelector('.oculto').textContent = si ? 'Abrir el menú' : 'Cerrar el menú';
    };
    var ajustar = function () { plegar(estrecha.matches); };

    ajustar();
    if (estrecha.addEventListener) estrecha.addEventListener('change', ajustar);
    else if (estrecha.addListener) estrecha.addListener(ajustar);

    boton.addEventListener('click', function () { plegar(!lista.hidden); });
    lista.addEventListener('click', function (ev) {
      if (ev.target.tagName === 'A' && estrecha.matches) plegar(true);
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && estrecha.matches && !lista.hidden) {
        plegar(true);
        boton.focus();
      }
    });
  }

  /* ---- 3. La barra se aparta al bajar -------------------------
     La barra flota encima del texto. Se lee bajando, así que al
     bajar se va; al subir se busca navegación, así que vuelve.

     HOLGURA existe para que el temblor de un trackpad alrededor de
     cero no la haga aparecer en mitad de una frase: hace falta un
     gesto hacia arriba de 6px de verdad.

     DESDE sale de la altura real de la barra, no de un número
     redondo: por debajo de eso la barra todavía no tapa nada y
     esconderla sería quitarla sin motivo. */
  var barra = document.getElementById('barra');
  if (barra) {
    var ultimaY = window.scrollY, HOLGURA = 6;
    var DESDE = Math.round(barra.getBoundingClientRect().bottom) + 12;
    // La misma medida le sirve al rail de las paginas de trabajo para saber
    // donde posarse. Se publica como propiedad para no medirla dos veces ni
    // escribir el numero a mano en el CSS, que es como se acaba desajustando.
    raiz.style.setProperty('--alto-barra', DESDE + 'px');

    var alDesplazar = function () {
      var y = window.scrollY;
      var dy = y - ultimaY;
      if (Math.abs(dy) > 1) ultimaY = y;

      barra.classList.toggle('esta-posada', y > 20);

      // Nunca se esconde con el menú abierto —se llevaría el menú con
      // ella— ni con el foco dentro, que dejaría a un teclado sin barra.
      var menuAbierto = lista && !lista.hidden && estrecha.matches;
      var conFoco = barra.contains(document.activeElement);
      if (y > DESDE && dy > 0 && !menuAbierto && !conFoco) barra.classList.add('esta-oculta');
      else if (dy < -HOLGURA || y <= DESDE || menuAbierto || conFoco) barra.classList.remove('esta-oculta');

      avanzar();
    };

    /* ---- 4. Avance de lectura ---------------------------------
       Una línea de 2px en el borde de la barra. Es la única pieza
       de la página que dice cuánto queda, y cuesta un scaleX. */
    var avance = document.getElementById('avance');
    var avanzar = function () {
      if (!avance) return;
      var alto = document.documentElement.scrollHeight - window.innerHeight;
      avance.style.transform = 'scaleX(' + (alto > 0 ? Math.min(1, window.scrollY / alto) : 0) + ')';
    };

    var esperando = false;
    window.addEventListener('scroll', function () {
      if (esperando) return;
      esperando = true;
      window.requestAnimationFrame(function () { esperando = false; alDesplazar(); });
    }, { passive: true });
    window.addEventListener('resize', avanzar);
    alDesplazar();
  }

  /* ---- 5. Carrusel de trabajos --------------------------------
     Se mueve de grupo en grupo, no de ficha en ficha: saltar de una
     en una con la flecha se hace eterno. */
  var pista = document.getElementById('pista-trabajos');
  var atras = document.getElementById('carrusel-atras');
  var alante = document.getElementById('carrusel-alante');
  var puntos = document.getElementById('carrusel-puntos');

  if (pista) {
    var paginas = function () {
      return Math.max(1, Math.ceil(pista.scrollWidth / pista.clientWidth));
    };
    var pagina = function () {
      return Math.round(pista.scrollLeft / pista.clientWidth);
    };

    var pintarPuntos = function () {
      if (!puntos) return;
      var total = paginas();
      if (total < 2) { puntos.hidden = true; return; }
      puntos.hidden = false;
      if (puntos.children.length !== total) {
        puntos.innerHTML = '';
        for (var i = 0; i < total; i++) {
          var b = document.createElement('button');
          b.type = 'button';
          b.className = 'carrusel__punto';
          b.setAttribute('data-pagina', i);
          b.setAttribute('aria-label', 'Ir al grupo ' + (i + 1) + ' de ' + total);
          puntos.appendChild(b);
        }
      }
      var actual = pagina();
      for (var j = 0; j < puntos.children.length; j++) {
        if (j === actual) puntos.children[j].setAttribute('aria-current', 'true');
        else puntos.children[j].removeAttribute('aria-current');
      }
    };

    var refrescar = function () {
      // Holgura de 2px: el desplazamiento devuelve decimales y sin ella el
      // botón derecho se queda activo en el último grupo.
      if (atras) atras.disabled = pista.scrollLeft <= 2;
      if (alante) alante.disabled = pista.scrollLeft + pista.clientWidth >= pista.scrollWidth - 2;
      pintarPuntos();
    };

    var mover = function (signo) {
      pista.scrollBy({ left: signo * pista.clientWidth, behavior: QUIETO ? 'auto' : 'smooth' });
    };

    if (atras) atras.addEventListener('click', function () { mover(-1); });
    if (alante) alante.addEventListener('click', function () { mover(1); });
    if (puntos) {
      puntos.addEventListener('click', function (ev) {
        var p = ev.target.getAttribute && ev.target.getAttribute('data-pagina');
        if (p === null || p === undefined) return;
        pista.scrollTo({ left: pista.clientWidth * parseInt(p, 10), behavior: QUIETO ? 'auto' : 'smooth' });
      });
    }

    var esperaCarrusel = false;
    pista.addEventListener('scroll', function () {
      if (esperaCarrusel) return;
      esperaCarrusel = true;
      window.requestAnimationFrame(function () { esperaCarrusel = false; refrescar(); });
    }, { passive: true });
    window.addEventListener('resize', refrescar);
    refrescar();
  }

  /* ---- 6. El mapa del trabajo ---------------------------------
     Es el mismo grafo de index.html, no una copia: ui/mapa.js
     expone la fábrica y aquí solo se le pasa el lienzo y el ámbar.

     No se monta por debajo de 760px. No es pereza: catorce
     etiquetas en un móvil se amontonan hasta ser ilegibles, y el
     grafo se maneja pasando el ratón por encima, gesto que en una
     pantalla táctil no existe. Debajo queda el aviso que dice
     dónde están los proyectos, y no se gasta ni una CPU. */
  var lienzoMapa = document.getElementById('mapa-portfolio');
  var mapa = null;
  if (lienzoMapa && typeof window.crearMapa === 'function') {
    var anchoMapa = window.matchMedia('(min-width:760px)');

    var montarMapa = function () {
      if (anchoMapa.matches && !mapa) {
        mapa = window.crearMapa(lienzoMapa, { rgb: [224, 164, 88] });
      } else if (!anchoMapa.matches && mapa) {
        mapa.ocultar();
      } else if (anchoMapa.matches && mapa) {
        mapa.mostrar();
      }
    };
    montarMapa();
    if (anchoMapa.addEventListener) anchoMapa.addEventListener('change', montarMapa);
    else if (anchoMapa.addListener) anchoMapa.addListener(montarMapa);
  }

  /* ---- 7. Foco de luz y ladeo de las fichas -------------------
     Un solo escuchador para toda la página, no uno por ficha, y lo
     único que escribe son propiedades personalizadas que lee el
     CSS: eso repinta la ficha, no recalcula el diseño.

     Solo con ratón: en una pantalla táctil no hay "encima" que
     iluminar. El ladeo se queda en 3 grados; más y la ficha deja de
     leerse como una ficha. */
  if (FINO && !QUIETO) {
    document.addEventListener('pointermove', function (ev) {
      if (ev.pointerType === 'touch' || pausado()) return;
      var ficha = ev.target.closest && ev.target.closest('.obra');
      if (!ficha) return;
      var c = ficha.getBoundingClientRect();
      var px = (ev.clientX - c.left) / c.width - 0.5;
      var py = (ev.clientY - c.top) / c.height - 0.5;
      ficha.style.setProperty('--luz-x', (ev.clientX - c.left) + 'px');
      ficha.style.setProperty('--luz-y', (ev.clientY - c.top) + 'px');
      ficha.style.setProperty('--giro-y', (px * 3).toFixed(2) + 'deg');
      ficha.style.setProperty('--giro-x', (-py * 3).toFixed(2) + 'deg');
      ficha.classList.add('se-ladea');
    }, { passive: true });

    document.addEventListener('pointerout', function (ev) {
      var ficha = ev.target.closest && ev.target.closest('.obra');
      if (!ficha || (ev.relatedTarget && ficha.contains(ev.relatedTarget))) return;
      ficha.classList.remove('se-ladea');
      ficha.style.removeProperty('--giro-y');
      ficha.style.removeProperty('--giro-x');
    });
  }

  /* ---- 8. El saludo se escribe y se corrige -------------------
     Port a mano de typed.js, no la librería. Son los tres
     comportamientos que hacen que aquello se sienta bien:

       1. HUMANIZADOR. typed.js nunca usa un intervalo fijo: su
          retardo es la mitad de speed al azar más speed, así que
          cada tecla cae entre speed y 1,5 veces speed. Un intervalo
          constante es lo que hace que una máquina de escribir suene
          a máquina y no a persona.
       2. PAUSA AL FINAL. Aguanta la palabra terminada antes de
          borrarla. typed.js usa 700ms; aquí 1500, porque estas son
          palabras para leer y no una cadena de demostración.
       3. BORRADO LISTO. Solo borra hasta el prefijo que comparte
          con la siguiente: de "Hola" a "Hallo" conserva la H. Da la
          sensación de alguien corrigiéndose, no de un campo que se
          vacía y se vuelve a llenar.

     Con movimiento reducido el bloque se va antes de hacer nada: se
     queda el "Hola" que ya venía en el HTML y el cursor ni se
     enciende. */
  // Los dos mandos del saludo, para que el interruptor de movimiento pueda
  // llegar hasta aqui. La auditoria encontro que con el movimiento parado el
  // saludo SEGUIA tecleando: solo miraba la preferencia del sistema al
  // arrancar y nunca el estado del boton.
  var pararSaludo = null, seguirSaludo = null;

  var saludo = document.getElementById('saludo');
  var palabra = document.getElementById('saludo-palabra');
  if (saludo && palabra && !QUIETO) {
    var PALABRAS = [];
    try {
      PALABRAS = JSON.parse(saludo.getAttribute('data-saludos')) || [];
    } catch (err) { PALABRAS = []; }

    if (PALABRAS.length > 1) {
      var TECLA = 78, BORRA = 42, AGUANTA = 1500, ARRANQUE = 1600;
      var humano = function (v) { return Math.round(Math.random() * v / 2) + v; };

      // El HTML ya trae la primera palabra escrita, así que el ciclo empieza
      // por la pausa del final y no por una caja vacía.
      var iP = 0, corte = PALABRAS[0].length, borrando = false, hasta = 0, reloj = null;

      var teclear = function () {
        var actual = PALABRAS[iP];
        if (borrando) {
          corte--;
          palabra.textContent = actual.slice(0, corte);
          if (corte <= hasta) { borrando = false; iP = (iP + 1) % PALABRAS.length; }
          reloj = setTimeout(teclear, humano(BORRA));
          return;
        }
        if (corte < actual.length) {
          corte++;
          palabra.textContent = actual.slice(0, corte);
          reloj = setTimeout(teclear, corte === actual.length ? AGUANTA : humano(TECLA));
          return;
        }
        // Palabra completa y pausa gastada: cuánto hay que retroceder.
        var siguiente = PALABRAS[(iP + 1) % PALABRAS.length];
        hasta = 0;
        while (hasta < actual.length && hasta < siguiente.length
               && actual[hasta] === siguiente[hasta]) hasta++;
        borrando = true;
        teclear();
      };

      // Un cursor parpadeando en una pestaña que nadie mira es trabajo tirado.
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) { clearTimeout(reloj); reloj = null; }
        else if (!reloj) reloj = setTimeout(teclear, humano(BORRA));
      });

      pararSaludo = function () {
        clearTimeout(reloj);
        reloj = null;
        saludo.classList.remove('esta-tecleando');
      };
      seguirSaludo = function () {
        if (reloj) return;                 // ya esta en marcha, no duplicar
        saludo.classList.add('esta-tecleando');
        reloj = setTimeout(teclear, humano(BORRA));
      };

      if (pausado()) {
        // Si la pagina arranca con el movimiento parado, el saludo no empieza.
        saludo.classList.remove('esta-tecleando');
      } else {
        saludo.classList.add('esta-tecleando');
        reloj = setTimeout(teclear, ARRANQUE);
      }
    }
  }

  /* ---- 9. Formación: filas que se abren al pasar por encima ---
     EL MUELLE ESTÁ INTEGRADO, NO IMITADO. Rigidez 280, amortiguación
     32, masa 0,9. La razón de usar un muelle en vez de un acordeón
     con duración fija es que abrir y cerrar se sientan físicos: una
     curva bézier de la misma duración se lee como una curva de
     aceleración, que es justo lo que no es. Quince líneas de
     integración de Euler compran el comportamiento de verdad,
     incluido un cierre que arrastra la velocidad de una apertura
     interrumpida a mitad de camino.

     TRES ENTRADAS, UN SOLO ESTADO. El ratón siempre previsualiza; al
     salir de la lista se vuelve a lo que haya dejado clavado un
     clic, así que apartar el ratón nunca cierra una fila que el
     lector abrió a propósito. Ojo: lo clavado NO puede bloquear el
     hover. Una guarda del tipo "hay algo clavado" congela las cuatro
     filas con un solo clic, y como la cabecera es un botón con
     cursor de mano, hacer clic está invitado. Eso se lee como que el
     componente está roto. */
  var hitos = document.getElementById('hitos');
  if (hitos) {
    var CERRADA = 68, K = 280, D = 32, M = 0.9;
    /* SUELO de la fila abierta. Sin él, la altura la manda solo el texto: una
       entrada de dos puntos abría 191px y su foto salía a 105px de ancho,
       diminuta al lado de la de cuatro puntos. En la referencia todas las
       filas dan a la imagen sitio de sobra, y esa regularidad es la mitad del
       efecto. 220 es el punto donde la foto ya se ve —145px de ancho en vez de
       105— sin que quede un socavón de panel vacío debajo de las etiquetas:
       con 260 sobraban casi setenta píxeles y se notaban. */
    var SUELO_ABIERTA = 220;
    // 900, el mismo corte que el CSS de la placa. Por debajo las filas van
    // abiertas y sin imagen, así que el muelle no tiene nada que hacer.
    var anchoFilas = window.matchMedia('(min-width:900px)');

    var filas = [].slice.call(hitos.querySelectorAll('[data-fila]')).map(function (el) {
      return {
        el: el,
        placa: el.querySelector('.hito__placa'),
        cuerpo: el.querySelector('.hito__cuerpo'),
        boton: el.querySelector('.hito__cabeza'),
        h: CERRADA, v: 0, meta: CERRADA, abierta: CERRADA, clavada: false
      };
    });

    if (filas.length) {
      hitos.classList.add('js');
      var activa = -1, cuadro = null, antes = 0;

      /* ALTURA POR FILA, no una sola para las cuatro. Estas entradas van de dos
         a cuatro puntos, y un número único o recorta la más larga o deja la más
         corta medio vacía. El cuerpo se oculta con opacidad y no se saca del
         flujo, así que offsetHeight es su altura de verdad. Se vuelve a medir
         al cambiar de tamaño porque los puntos se reparten en otras líneas. */
      var medir = function () {
        filas.forEach(function (f) {
          f.abierta = Math.max(SUELO_ABIERTA,
                               CERRADA + (f.cuerpo ? f.cuerpo.offsetHeight : 0));
          if (f.meta !== CERRADA) f.meta = f.abierta;
        });
      };

      var pintar = function (f) {
        var q = (f.h - CERRADA) / Math.max(1, f.abierta - CERRADA);
        f.el.style.height = f.h.toFixed(1) + 'px';
        if (f.placa) {
          f.placa.style.opacity = Math.min(1, q * 1.4).toFixed(3);
          f.placa.style.transform = 'translateX(' + ((1 - q) * 100).toFixed(2) + '%)';
        }
      };

      var paso = function (ahora) {
        var dt = Math.min(0.032, (ahora - antes) / 1000) || 0.016;
        antes = ahora;
        var moviendo = false;
        filas.forEach(function (f) {
          var dx = f.h - f.meta;
          if (Math.abs(dx) < 0.15 && Math.abs(f.v) < 0.15) {
            f.h = f.meta; f.v = 0; pintar(f); return;
          }
          f.v += ((-K * dx) - (D * f.v)) / M * dt;
          f.h += f.v * dt;
          pintar(f);
          moviendo = true;
        });
        cuadro = moviendo ? window.requestAnimationFrame(paso) : null;
      };
      var despertar = function () {
        if (!cuadro) {
          antes = window.performance.now();
          cuadro = window.requestAnimationFrame(paso);
        }
      };

      var activar = function (i) {
        if (activa === i) return;
        activa = i;
        filas.forEach(function (f, k) {
          var on = k === i;
          f.meta = on ? f.abierta : CERRADA;
          f.el.style.opacity = (i === -1 || on) ? '1' : '0.38';
          f.el.style.transition = 'opacity .3s cubic-bezier(.22,.61,.36,1)';
          if (f.boton) f.boton.setAttribute('aria-expanded', on ? 'true' : 'false');
          if (f.cuerpo) {
            // El retraso va solo a la ida: el detalle aparece cuando la fila ya
            // se ha abierto lo bastante para leerse, y desaparece en cuanto
            // empieza a cerrarse.
            var tarda = on ? ' .12s' : '';
            f.cuerpo.style.transition = 'opacity .32s cubic-bezier(.22,.61,.36,1)' + tarda
                                      + ', transform .42s cubic-bezier(.22,.61,.36,1)' + tarda;
            f.cuerpo.style.opacity = on ? '1' : '0';
            f.cuerpo.style.transform = on ? 'translateX(0)' : 'translateX(-8px)';
          }
        });
        if (QUIETO || pausado()) {
          filas.forEach(function (f) { f.h = f.meta; f.v = 0; pintar(f); });
          return;
        }
        despertar();
      };

      var laClavada = function () {
        for (var k = 0; k < filas.length; k++) if (filas[k].clavada) return k;
        return -1;
      };

      filas.forEach(function (f, i) {
        if (f.boton) {
          f.boton.addEventListener('click', function () {
            var clavar = !f.clavada;
            filas.forEach(function (o) { o.clavada = false; });
            f.clavada = clavar;
            activar(clavar ? i : -1);
          });
        }
        f.el.addEventListener('pointerenter', function () { if (FINO) activar(i); });
        f.el.addEventListener('focusin', function () { activar(i); });
      });

      hitos.addEventListener('pointerleave', function () { if (FINO) activar(laClavada()); });
      hitos.addEventListener('focusout', function (ev) {
        if (!hitos.contains(ev.relatedTarget)) activar(laClavada());
      });

      /* Por debajo de 900 el CSS abre todas las filas con !important, así que
         el muelle no tiene nada que hacer y las alturas en línea que escribió
         quedarían obsoletas al volver a subir. Limpiarlas al cruzar sale más
         barato que poner una guarda dentro de pintar(). */
      var ajustarFilas = function () {
        if (anchoFilas.matches) {
          medir(); activar(-1); filas.forEach(pintar);
        } else {
          if (cuadro) { window.cancelAnimationFrame(cuadro); cuadro = null; }
          activa = -1;
          filas.forEach(function (f) {
            f.h = CERRADA; f.v = 0; f.meta = CERRADA;
            f.el.style.height = ''; f.el.style.opacity = '';
            if (f.placa) { f.placa.style.opacity = ''; f.placa.style.transform = ''; }
            if (f.cuerpo) { f.cuerpo.style.opacity = ''; f.cuerpo.style.transform = ''; }
            // En móvil las filas están abiertas de verdad, y eso es lo que
            // tiene que oír quien use un lector de pantalla.
            if (f.boton) f.boton.setAttribute('aria-expanded', 'true');
          });
        }
      };
      if (anchoFilas.addEventListener) anchoFilas.addEventListener('change', ajustarFilas);
      else if (anchoFilas.addListener) anchoFilas.addListener(ajustarFilas);

      var tempo = null;
      window.addEventListener('resize', function () {
        clearTimeout(tempo);
        tempo = setTimeout(function () {
          if (!anchoFilas.matches) return;
          medir();
          if (activa !== -1) { filas[activa].meta = filas[activa].abierta; despertar(); }
        }, 140);
      });

      // Las tipografías web cambian el número de líneas, así que la primera
      // medida tiene que esperarlas o cada fila se mide contra la de respaldo.
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(medir);

      ajustarFilas();
    }
  }

  /* ---- 10. El titular entra palabra a palabra ------------------
     Sin librería: se parte el texto en palabras, cada una en su
     caja con overflow oculto, y suben con un retraso escalonado.
     Se hace sobre el texto que ya está en el HTML, así que si esto
     no corre el titular sigue ahí, entero y legible. */
  var titular = document.querySelector('[data-partir]');
  if (titular && !QUIETO) {
    var palabras = titular.textContent.trim().split(/\s+/);
    titular.textContent = '';
    palabras.forEach(function (p, i) {
      var caja = document.createElement('span');
      caja.className = 'palabra';
      var dentro = document.createElement('span');
      dentro.className = 'palabra__interior';
      dentro.textContent = p;
      dentro.style.transitionDelay = (0.05 + i * 0.07).toFixed(2) + 's';
      caja.appendChild(dentro);
      titular.appendChild(caja);
      if (i < palabras.length - 1) titular.appendChild(document.createTextNode(' '));
    });
    titular.classList.add('esta-partido');
    // Un fotograma después, para que el navegador vea el estado inicial y
    // haya transición en lugar de un salto.
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () { titular.classList.add('esta-entero'); });
    });
  }

  /* ---- 11. El anillo que acompaña al puntero -------------------
     Un nodo de la red, pero pegado al ratón: anillo ámbar que sigue
     con retraso y, sobre algo pulsable, se enciende y le sale un
     núcleo.

     EL CURSOR DEL SISTEMA NO SE TOCA. La referencia hace cursor:none
     y dibuja el suyo; aquí no, y es a propósito. Esconder el cursor
     nativo se lleva por delante el cursor grande, el de alto
     contraste y cualquier ajuste que alguien tenga puesto, a cambio
     de una pieza decorativa. Mal negocio.

     El bucle se aparca solo cuando el anillo alcanza al puntero, y
     cualquier movimiento lo despierta. Un rAF que no para nunca es
     trabajo cada 16ms durante toda la visita, incluso mientras
     alguien está simplemente leyendo. */
  var anillo = document.getElementById('nodo-cursor');
  if (anillo && FINO && !QUIETO) {
    var ax = window.innerWidth / 2, ay = window.innerHeight / 2;
    var rx = ax, ry = ay, corriendo = false;

    var girar = function () {
      // 0,18: por debajo el anillo va pegado y no se lee como algo aparte;
      // por encima se queda tan atrás que parece que va con retardo de red.
      rx += (ax - rx) * 0.18;
      ry += (ay - ry) * 0.18;
      anillo.style.transform = 'translate3d(' + rx.toFixed(1) + 'px,' + ry.toFixed(1) + 'px,0)';
      if (Math.abs(ax - rx) < 0.15 && Math.abs(ay - ry) < 0.15) { corriendo = false; return; }
      window.requestAnimationFrame(girar);
    };
    var despertarAnillo = function () {
      if (corriendo || pausado()) return;
      corriendo = true;
      window.requestAnimationFrame(girar);
    };

    var PULSABLE = 'a,button,summary,[role="button"],input,select,textarea,label';
    window.addEventListener('pointermove', function (ev) {
      if (ev.pointerType === 'touch') return;
      ax = ev.clientX; ay = ev.clientY;
      anillo.classList.add('esta-visible');
      anillo.classList.toggle('esta-activo',
        !!(ev.target.closest && ev.target.closest(PULSABLE)));
      despertarAnillo();
    }, { passive: true });

    // Al salir de la ventana se apaga: un anillo parado en el borde de la
    // pantalla mientras el ratón está en otra aplicación es un adorno huérfano.
    document.addEventListener('pointerleave', function () {
      anillo.classList.remove('esta-visible');
    });
    window.addEventListener('blur', function () {
      anillo.classList.remove('esta-visible');
    });
  }

  /* ---- 12. La llamada flotante --------------------------------
     Aparece cuando ya se ha bajado un poco y se aparta cuando llega
     la llamada final: una píldora que dice "ponte en contacto"
     tapando el botón de ponerse en contacto es a la vez redundante
     y un estorbo. Se esconde con visibility desde el CSS, así que
     mientras no toca tampoco se puede tabular hasta ella. */
  var flotante = document.getElementById('flotante');
  if (flotante) {
    var finalALaVista = false;
    var zonas = [document.getElementById('contacto'),
                 document.querySelector('.pie')].filter(Boolean);

    var revisarFlotante = function () {
      var hondo = window.innerWidth >= 821
        ? window.scrollY > 640
        // Estrecho: no hay margen donde esconderse, así que se retrasa hasta
        // el 70% de la página, que es donde una invitación deja de interrumpir.
        : window.scrollY + window.innerHeight > document.body.scrollHeight * 0.7;
      // Con el foco dentro no se va: dejaría a un teclado a media acción.
      var conFoco = flotante.contains(document.activeElement);
      flotante.classList.toggle('esta-visible', (hondo && !finalALaVista) || conFoco);
    };

    if (zonas.length && HAY_IO) {
      var vistas = new WeakMap();
      var vigiaFinal = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (en) { vistas.set(en.target, en.isIntersecting); });
        finalALaVista = zonas.some(function (z) { return vistas.get(z); });
        revisarFlotante();
      }, { threshold: 0 });
      zonas.forEach(function (z) { vigiaFinal.observe(z); });
    }

    var esperaFlot = false;
    window.addEventListener('scroll', function () {
      if (esperaFlot) return;
      esperaFlot = true;
      window.requestAnimationFrame(function () { esperaFlot = false; revisarFlotante(); });
    }, { passive: true });
    flotante.addEventListener('focus', revisarFlotante);
    flotante.addEventListener('blur', revisarFlotante);
    revisarFlotante();
  }

  /* ---- 13. Parar el movimiento ---------------------------------
     Cuando el sistema ya pide menos movimiento, el botón no se
     ofrece: se queda desactivado y lo dice. Un interruptor que
     promete reanudar algo que el sistema prohíbe es una mentira
     pequeña, pero es una mentira. */
  /* ----------------------------------------------------------------
     13 bis · El raíl de apartados de una página de trabajo

     Marca en cuál estás mientras bajas. Solo eso: los enlaces son anclas de
     verdad y llevan a su sitio con el script bloqueado, así que esto es
     adorno útil y no la navegación.

     Con IntersectionObserver y no con scroll + getBoundingClientRect: el
     segundo obliga a medir todas las secciones en cada fotograma de
     desplazamiento, y medir dispara recálculo de diseño. El margen de
     recorte deja una franja fina cerca de la parte de arriba de la ventana,
     de modo que la sección activa es la que está entrando, no la que ocupa
     más pantalla —que a mitad de una sección larga se queda pegada a la
     anterior—.
     ---------------------------------------------------------------- */
  var rail = document.getElementById('rail');
  if (rail && HAY_IO) {
    var enlaces = [].slice.call(rail.querySelectorAll('[data-rail]'));
    var porAncla = {};
    enlaces.forEach(function (a) { porAncla[a.getAttribute('href').slice(1)] = a; });

    var marcar = function (id) {
      enlaces.forEach(function (a) {
        var suyo = a.getAttribute('href').slice(1) === id;
        if (suyo) a.setAttribute('aria-current', 'true');
        else a.removeAttribute('aria-current');
      });
    };

    var vigia = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (x) {
        if (x.isIntersecting && porAncla[x.target.id]) marcar(x.target.id);
      });
    }, { rootMargin: '-25% 0px -70% 0px', threshold: 0 });

    Object.keys(porAncla).forEach(function (id) {
      var s = document.getElementById(id);
      if (s) vigia.observe(s);
    });

    // Si se llega con un ancla en la URL, el observador aún no ha dicho nada
    // y el raíl saldría sin marcar hasta el primer desplazamiento.
    if (location.hash && porAncla[location.hash.slice(1)]) marcar(location.hash.slice(1));
  }

  /* ----------------------------------------------------------------
     13 ter · El vídeo de la portada de un trabajo

     Un <video autoplay loop> de fondo tiene dos problemas que este bloque
     resuelve, y por eso el HTML NO lleva el atributo autoplay:

     1. Se salta el botón de parar el movimiento. Aquí el vídeo obedece a la
        misma clase html.sin-movimiento que el fondo y el mapa, sin montar un
        segundo interruptor.
     2. Se descarga siempre. Va con preload="none" y el src en data-src, así
        que con el movimiento parado o con prefers-reduced-motion el archivo
        NO se pide nunca: lo que se ve es el póster, que pesa la octava parte.

     Y se para fuera de pantalla: la portada se queda arriba y el resto de la
     página es larga.
     ---------------------------------------------------------------- */
  /* De UNO a VARIOS. Este bloque gobernaba solo la portada, por id. Ahora
     recorre todo lo que lleve data-video-ambiental, que es la portada mas los
     cortes que separan los apartados. Ni una regla cambia: cada video conserva
     su carga en diferido, su parada fuera de pantalla, su obediencia al boton
     de parar y su silencio con movimiento reducido. La portada sigue teniendo
     su id, asi que lo que ya lo buscaba por id lo sigue encontrando.

     La diferencia entre uno y otro es DONDE empiezan: la portada esta arriba
     y ya se ve al cargar; un corte esta a media pagina y no debe pedir su
     archivo hasta que alguien llegue. Eso lo dice data-arranca-visible. */
  [].slice.call(document.querySelectorAll('[data-video-ambiental]')).forEach(function (video) {
    var cargado = false;

    /* Si el video esta a la vista. Empieza en true porque la portada esta
       arriba del todo y ahi esta cuando se carga la pagina; el observador de
       mas abajo corrige el valor en cuanto se engancha.

       Sin esta variable, reanudar el movimiento desde el pie de la pagina
       -que es donde esta el boton- ponia a reproducir un video que quedaba
       tres pantallas mas arriba, y ahi se quedaba corriendo. El observador
       de interseccion no lo salvaba: solo avisa cuando la visibilidad
       CAMBIA, y desde el pie no cambiaba nada. */
    var aLaVista = video.hasAttribute('data-arranca-visible');

    /* No se enseña hasta que de verdad esté pintando. Entre que el archivo
       llega y sale el primer fotograma hay un hueco en el que un <video> sin
       fotogramas es un rectángulo negro, y eso se ve como un parpadeo encima
       del póster. 'playing' es el evento que dice que ya hay imagen. */
    video.addEventListener('playing', function () {
      video.classList.add('esta-encendido');
    });

    var encender = function () {
      if (QUIETO || raiz.classList.contains('sin-movimiento')) return;
      if (!aLaVista) return;
      if (!cargado) {
        video.src = video.getAttribute('data-src');
        cargado = true;
      }
      // play() devuelve una promesa que se rechaza si el navegador decide que
      // no toca. No es un error: sin catch, la consola se llena de rechazos
      // no atendidos cada vez que alguien cambia de pestaña.
      var p = video.play();
      if (p && p.catch) p.catch(function () {});
    };
    var apagar = function () { if (!video.paused) video.pause(); };

    if (!QUIETO) {
      encender();
      new MutationObserver(function () {
        if (raiz.classList.contains('sin-movimiento')) apagar(); else encender();
      }).observe(raiz, { attributes: true, attributeFilter: ['class'] });

      document.addEventListener('visibilitychange', function () {
        if (document.hidden) apagar(); else encender();
      });

      if (HAY_IO) {
        new IntersectionObserver(function (e) {
          aLaVista = e[0].isIntersecting;
          if (aLaVista) encender(); else apagar();
        }, { threshold: 0 }).observe(video);
      }
    }
  });

  /* ----------------------------------------------------------------
     13 quater · El visor de documento de una página de trabajo

     La fachada es un <a> con href de verdad al PDF. Sin JavaScript, o con un
     clic modificado, hace lo que dice: abrir el documento. Lo que añade este
     bloque es que en una pantalla ancha lo cargue AQUÍ, en el mismo sitio y
     con la misma altura, en vez de mandarte a otra pestaña.

     Por qué una fachada y no un <iframe> desde el principio: el PDF son 8,5
     MB. Puesto de entrada, se los descarga todo el que pase por la página,
     lo vaya a leer o no. Así solo viaja cuando alguien lo pide.

     En estrecho NO se sustituye. El visor de PDF embebido en un móvil es
     incómodo de verdad —se desplaza dentro de un contenedor que a su vez se
     desplaza—, y ahí abrir el archivo en su propia pestaña es mejor.
     ---------------------------------------------------------------- */
  var fachadas = [].slice.call(document.querySelectorAll('.visor__fachada'));
  if (fachadas.length) {
    var enSitio = window.matchMedia('(min-width:900px)');

    // La nota que solo oye un lector de pantalla tiene que decir la verdad, y
    // la verdad cambia con el ancho de la ventana.
    var avisar = function () {
      fachadas.forEach(function (f) {
        var nota = f.querySelector('[data-visor-nota]');
        if (nota) {
          nota.textContent = enSitio.matches
            ? ', se abre aquí mismo' : ', se abre en otra pestaña';
        }
      });
    };
    avisar();
    if (enSitio.addEventListener) enSitio.addEventListener('change', avisar);
    else if (enSitio.addListener) enSitio.addListener(avisar);

    fachadas.forEach(function (f) {
      f.addEventListener('click', function (ev) {
        // Ctrl/Cmd/Shift o botón central: la persona ha pedido otra pestaña.
        // Y en estrecho, el href hace su trabajo.
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey || ev.button !== 0) return;
        if (!enSitio.matches) return;
        ev.preventDefault();

        var marco = document.createElement('iframe');
        // #view=FitH abre el PDF ajustado al ancho, que es como se lee un
        // documento y no como lo abre el visor por defecto.
        marco.src = f.getAttribute('href') + '#view=FitH';
        marco.title = f.getAttribute('data-visor') || 'Documento PDF';
        marco.className = 'visor__marco';
        marco.setAttribute('loading', 'lazy');
        f.parentNode.replaceChild(marco, f);
        // El foco se va al documento: quien ha llegado con el teclado estaba
        // en la fachada, y si no se mueve el foco se queda en la nada.
        marco.focus({ preventScroll: true });
      });
    });
  }

  var quieto = document.getElementById('quieto');
  if (quieto) {
    var CLAVE = CLAVE_MOVIMIENTO;
    var texto = quieto.querySelector('[data-texto]');
    var guardado = null;
    try { guardado = window.localStorage.getItem(CLAVE); } catch (err) { /* modo privado */ }

    var aplicar = function (si) {
      raiz.classList.toggle('sin-movimiento', si);
      quieto.setAttribute('aria-pressed', String(si));
      texto.textContent = QUIETO ? 'Movimiento desactivado en el sistema'
                                 : (si ? 'Reanudar movimiento' : 'Parar movimiento');

      /* Parar el movimiento tiene que parar TODO, no casi todo. El fondo y el
         mapa se enteran solos porque vigilan la clase; el saludo y el mapa hay
         que empujarlos. Antes faltaba el saludo y seguia tecleando con la
         pagina "en pausa", que es una promesa a medias. */
      if (si) {
        if (pararSaludo) pararSaludo();
      } else {
        if (seguirSaludo) seguirSaludo();
        if (mapa && mapa.reanudar) mapa.reanudar();
      }
    };

    if (QUIETO) {
      aplicar(true);
      quieto.disabled = true;
    } else {
      aplicar(guardado === '1');
      var alternar = function () {
        var si = !pausado();
        aplicar(si);
        try { window.localStorage.setItem(CLAVE, si ? '1' : '0'); } catch (err) { /* da igual */ }
      };

      quieto.addEventListener('click', alternar);

      /* El mismo mando, arriba. El del pie esta al 99% del recorrido: quien
         pause sin querer ve una web quieta durante seis mil pixeles antes de
         encontrar la forma de deshacerlo. Este solo aparece con el movimiento
         parado y lo devuelve desde donde este. */
      var reanudar = document.getElementById('reanudar');
      if (reanudar) reanudar.addEventListener('click', alternar);
    }
  }
})();
