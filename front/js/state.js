/**
 * state.js - Gestión del estado global, persistencia en localStorage y polling de IA
 */
(function(window) {
  'use strict';

  var API_BASE = '/api';
  var FORMATOS_API = ['image/jpeg', 'image/png', 'image/webp', 'image/tiff'];

  function placeholderImg(label) {
    var svg = "<svg xmlns='http://www.w3.org/2000/svg' width='420' height='300'><rect width='420' height='300' fill='#EDE7D6'/><rect x='10' y='10' width='400' height='280' fill='none' stroke='#9C8B63' stroke-width='2'/><text x='210' y='150' font-family='Georgia,serif' font-size='15' fill='#5b5240' text-anchor='middle'>" + label + "</text></svg>";
    return 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg)));
  }

  var seq = 1;
  function nid() {
    return 'PL-' + String(seq++).padStart(3, '0');
  }

  var planos = [];

  function seed() {
    planos = [
      {
        id: nid(),
        archNombre: 'plano_calle47.jpg',
        archTipo: 'image/svg+xml',
        archData: placeholderImg('Plano — Calle 47 N.º 620'),
        ubic: 'Caja 4, Estantería A',
        exp: 'Expte. 1122-1954',
        dirOrig: 'Calle 47 N.º 620',
        estado: 'validado',
        iaEstado: 'completado',
        iaError: null,
        tareaId: null,
        auto: {
          arquitecto: 'Bartolomé Uriarte',
          anio: 1954,
          titulo: 'Vivienda unifamiliar',
          ubicacion: 'Calle 47 N.º 620, La Plata',
          escala: '1:100',
          tipo_de_plano: 'planta',
          material_soporte: 'papel tela',
          notas: 'Sello de la Oficina Técnica Municipal'
        },
        parcela: 'Calle 47 N.º 620 — Lote 9, Mz. 40',
        historial: [{ fecha: '12/03/2024', motivo: 'Carga inicial validada' }]
      },
      {
        id: nid(),
        archNombre: 'plano_diag80.png',
        archTipo: 'image/svg+xml',
        archData: placeholderImg('Plano — Diagonal 80'),
        ubic: 'Caja 9, Legajo 3',
        exp: 'Expte. 3390-1971',
        dirOrig: 'Diagonal 80 N.º 1450',
        estado: 'sin_ubicacion',
        iaEstado: 'completado',
        iaError: null,
        tareaId: null,
        auto: {
          arquitecto: 'Elena Fittipaldi',
          anio: 1971,
          titulo: 'Local comercial',
          ubicacion: 'Diagonal 80 N.º 1450',
          escala: '1:50',
          tipo_de_plano: 'fachada',
          material_soporte: 'papel',
          notas: 'Sello de la Escribanía General de Gobierno'
        },
        parcela: '',
        historial: [{ fecha: '02/05/2024', motivo: 'Catalogado sin ubicación exacta' }]
      },
      {
        id: nid(),
        archNombre: 'plano_expte4521.pdf',
        archTipo: 'application/pdf',
        archData: placeholderImg('Plano — Expte. 4521'),
        ubic: '',
        exp: 'Expte. 4521-1968',
        dirOrig: '',
        estado: 'pendiente',
        iaEstado: 'no_aplica',
        iaError: null,
        tareaId: null,
        auto: null,
        parcela: '',
        historial: []
      },
      {
        id: nid(),
        archNombre: 'plano_deteriorado.jpg',
        archTipo: 'image/svg+xml',
        archData: placeholderImg('Plano deteriorado'),
        ubic: 'Caja 15',
        exp: '',
        dirOrig: '',
        estado: 'pendiente',
        iaEstado: 'error',
        iaError: 'Texto ilegible por deterioro físico',
        tareaId: null,
        auto: null,
        parcela: '',
        historial: []
      }
    ];
  }

  function save() {
    try {
      localStorage.setItem('ph_planos', JSON.stringify(planos));
      localStorage.setItem('ph_seq', String(seq));
    } catch (e) {
      console.error('Error al guardar en localStorage', e);
    }
  }

  function load() {
    try {
      var raw = localStorage.getItem('ph_planos');
      if (raw) {
        planos = JSON.parse(raw);
        seq = parseInt(localStorage.getItem('ph_seq') || '1', 10);
        // Migración de retrocompatibilidad
        planos.forEach(function(p) {
          if (!p.iaEstado) {
            if (p.auto) p.iaEstado = 'completado';
            else if (p.archTipo === 'application/pdf') p.iaEstado = 'no_aplica';
            else p.iaEstado = p.estado === 'pendiente' ? 'no_aplica' : 'completado';
          }
        });
        return true;
      }
    } catch (e) {
      console.error('Error al cargar de localStorage', e);
    }
    return false;
  }

  function byId(id) {
    return planos.find(function(p) { return p.id === id; });
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function val(id) {
    var el = document.getElementById(id);
    return el ? el.value : '';
  }

  function today() {
    var d = new Date();
    return String(d.getDate()).padStart(2, '0') + '/' +
      String(d.getMonth() + 1).padStart(2, '0') + '/' +
      d.getFullYear();
  }

  function badge(estado) {
    var map = { pendiente: 'Pendiente', validado: 'Validado', sin_ubicacion: 'Sin ubicación' };
    return '<span class="badge ' + estado + '">' + (map[estado] || estado) + '</span>';
  }

  function iaBadge(p) {
    if (p.iaEstado === 'procesando') {
      return ' <span class="badge" style="background:var(--amber-soft);color:var(--amber)"><span class="pulse"></span> IA analizando…</span>';
    }
    if (p.iaEstado === 'completado') {
      return ' <span class="badge" style="background:var(--ok-soft);color:var(--ok)">✓ IA lista</span>';
    }
    if (p.iaEstado === 'error') {
      return ' <span class="badge" style="background:var(--brick-soft);color:var(--brick)">⚠ IA error</span>';
    }
    return '';
  }

  // ---- Polling Asíncrono de Tareas de IA ----
  var pollingActivos = {};

  function iniciarPollingTarea(planoId, taskId, onCompleted, onError) {
    if (!taskId || pollingActivos[planoId]) return;
    pollingActivos[planoId] = true;

    var intervalo = 2500;
    var intentos = 0;
    var maxIntentos = 180; // ~7 minutos de margen

    function verificar() {
      var p = byId(planoId);
      if (!p) {
        delete pollingActivos[planoId];
        return;
      }
      // Si el usuario ya lo validó manualmente y se completó, cortar polling
      if (p.estado !== 'pendiente' && p.iaEstado === 'completado') {
        delete pollingActivos[planoId];
        return;
      }

      fetch(API_BASE + '/tareas/' + encodeURIComponent(taskId))
        .then(function(res) {
          if (!res.ok) {
            if (res.status === 404) throw new Error('Tarea no encontrada en el servidor');
            throw new Error('Error al consultar tarea: ' + res.status);
          }
          return res.json();
        })
        .then(function(info) {
          p = byId(planoId);
          if (!p) {
            delete pollingActivos[planoId];
            return;
          }

          if (info.status === 'completed') {
            delete pollingActivos[planoId];
            p.auto = info.resultado;
            p.iaEstado = 'completado';
            p.iaError = null;
            save();
            if (typeof onCompleted === 'function') onCompleted(p);
            if (window.PH && typeof window.PH.onPlanoIAActualizado === 'function') {
              window.PH.onPlanoIAActualizado(p);
            }
          } else if (info.status === 'error') {
            delete pollingActivos[planoId];
            p.iaEstado = 'error';
            p.iaError = info.error || 'Error durante la extracción';
            save();
            if (typeof onError === 'function') onError(p);
            if (window.PH && typeof window.PH.onPlanoIAActualizado === 'function') {
              window.PH.onPlanoIAActualizado(p);
            }
          } else {
            // Sigue en 'pending' o 'processing'
            intentos++;
            if (intentos >= maxIntentos) {
              delete pollingActivos[planoId];
              p.iaEstado = 'error';
              p.iaError = 'Tiempo de espera agotado';
              save();
              if (typeof onError === 'function') onError(p);
              if (window.PH && typeof window.PH.onPlanoIAActualizado === 'function') {
                window.PH.onPlanoIAActualizado(p);
              }
            } else {
              setTimeout(verificar, intervalo);
            }
          }
        })
        .catch(function(err) {
          intentos++;
          if (intentos >= maxIntentos) {
            delete pollingActivos[planoId];
            p = byId(planoId);
            if (p) {
              p.iaEstado = 'error';
              p.iaError = err.message;
              save();
              if (typeof onError === 'function') onError(p);
              if (window.PH && typeof window.PH.onPlanoIAActualizado === 'function') {
                window.PH.onPlanoIAActualizado(p);
              }
            }
          } else {
            setTimeout(verificar, 4000);
          }
        });
    }

    setTimeout(verificar, 1500);
  }

  function reanudarTareasPendientes() {
    planos.forEach(function(p) {
      if (p.iaEstado === 'procesando' && p.tareaId) {
        iniciarPollingTarea(p.id, p.tareaId);
      }
    });
  }

  // Reactivar polling si el usuario vuelve a la pestaña del navegador
  document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
      reanudarTareasPendientes();
    }
  });

  // Exportar al objeto global PH
  window.PH = window.PH || {};
  window.PH.State = {
    API_BASE: API_BASE,
    FORMATOS_API: FORMATOS_API,
    getPlanos: function() { return planos; },
    setPlanos: function(p) { planos = p; },
    nid: nid,
    seed: seed,
    save: save,
    load: load,
    byId: byId,
    esc: esc,
    val: val,
    today: today,
    badge: badge,
    iaBadge: iaBadge,
    iniciarPollingTarea: iniciarPollingTarea,
    reanudarTareasPendientes: reanudarTareasPendientes
  };

})(window);
