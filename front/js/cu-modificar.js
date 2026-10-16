/**
 * cu-modificar.js - CU3: Modificar catalogación de plano histórico.
 */
(function(window) {
  'use strict';

  var API = window.PH.API;
  var seleccionadoId = null;
  var planoActual = null;
  var propuestaActual = null;

  var CAMPOS = [
    { key: 'texto_extraido', label: 'Texto extraído (solo lectura)', type: 'textarea', readonly: true },
    { key: 'titulo', label: 'Título' },
    { key: 'arquitecto', label: 'Arquitecto' },
    { key: 'ubicacion', label: 'Ubicación' },
    { key: 'anio', label: 'Año', type: 'number' },
    { key: 'escala', label: 'Escala' },
    { key: 'tipo_de_plano', label: 'Tipo de Plano' },
    { key: 'material_soporte', label: 'Material' },
    { key: 'notas', label: 'Notas' }
  ];

  function esc(s) {
    return (s === undefined || s === null || s === '') ? '' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function attr(s) { return String(s || '').replace(/"/g, '&quot;'); }
  function tituloDoc(d) {
    return window.PH.Nomenclatura.titulo(d);
  }

  async function renderLista() {
    var cont = document.getElementById('modificar-lista');
    try {
      // Modificar lista must show 'validado' and 'sin_ubicacion' since both are cataloged.
      var validados = await API.getAll('validado');
      var sinUbic = await API.getAll('sin_ubicacion');
      var indexados = validados.concat(sinUbic);

      if (indexados.length === 0) {
        cont.innerHTML = '<div class="empty">Todavía no hay planos catalogados.</div>';
        return;
      }
      cont.innerHTML = indexados.map(function(d) {
        var sel = d.id === seleccionadoId ? ' sel' : '';
        var badge = d.estado === 'sin_ubicacion'
          ? '<span class="badge sin_ubicacion">Sin ubicación</span>'
          : '<span class="badge validado">Validado</span>';
        return '<button class="row' + sel + '" onclick="PH.CUModificar.seleccionar(' + d.id + ')">' +
          '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
          '<div class="s">' + badge + '</div>' +
          '</button>';
      }).join('');
    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  function seleccionar(id) {
    seleccionadoId = id;
    cerrarComparacion();
    renderDetalle();
    renderLista();
  }

  function cancelar() {
    seleccionadoId = null;
    planoActual = null;
    propuestaActual = null;
    cerrarComparacion();
    renderDetalle();
    renderLista();
  }

  async function renderDetalle() {
    var cont = document.getElementById('modificar-detalle');

    if (!seleccionadoId) {
      cont.innerHTML = '<div class="empty">Elija un plano catalogado para modificarlo.</div>';
      return;
    }

    try {
      var d = await API.getById(seleccionadoId);
      planoActual = d;

      propuestaActual = null;
      if (d.ia_propuesta) {
        try {
          propuestaActual = typeof d.ia_propuesta === 'string' ? JSON.parse(d.ia_propuesta) : d.ia_propuesta;
        } catch (e) {
          propuestaActual = null;
        }
      }

      var historialHTML = d.eventos && d.eventos.length
        ? '<div class="hist"><h3>Historial de cambios</h3><ul>' +
          d.eventos.slice().reverse().map(function(h) {
            var date = new Date(h.fecha).toLocaleString('es-AR');
            var usr = h.usuario_id || 'anonimo';
            return '<li><strong>' + esc(date) + ' (' + esc(usr) + ')</strong> — ' + esc(h.motivo) + '</li>';
          }).join('') + '</ul></div>'
        : '';

      var esPdf = d.content_type === 'application/pdf' || (d.nombre_original && d.nombre_original.toLowerCase().endsWith('.pdf'));
      var enlaceArchivo = '<div style="margin: 6px 0 12px 0;">'
        + '<a class="doclink" href="' + API.getArchivoUrl(d.id) + '" target="_blank" rel="noopener">'
        + (esPdf ? '📄 Abrir / Descargar PDF original (' + esc(d.nombre_original) + ')' : '🖼️ Ver / Descargar imagen original')
        + '</a></div>';

      var maxIntentos = 3;
      var maxIntentoPrevio = (d.procesamientos && d.procesamientos.length)
        ? Math.max.apply(null, d.procesamientos.map(function(p) { return p.intento || 0; }))
        : 0;
      var intentos = Math.max(maxIntentoPrevio, (d.ia_estado === 'error' || d.ia_estado === 'completado') ? 1 : 0);
      var puedeReintentar = (d.ia_estado !== 'no_aplica' && d.ia_estado !== 'procesando' && intentos < maxIntentos);

      var btnReintentar = '';
      if (d.ia_estado === 'procesando') {
        btnReintentar = '<button type="button" class="ghost" id="m-btn-reintentar" disabled style="opacity:0.7;cursor:wait;">Analizando con IA...</button>';
      } else if (puedeReintentar) {
        btnReintentar = '<button type="button" class="ghost" id="m-btn-reintentar" onclick="PH.CUModificar.reintentar(' + d.id + ')">Reintentar análisis IA (' + intentos + '/' + maxIntentos + ')</button>';
      } else if (intentos >= maxIntentos && d.ia_estado !== 'no_aplica') {
        btnReintentar = '<span class="badge limite">Límite de 3 intentos alcanzado</span>';
      }

      var bannerPropuesta = propuestaActual
        ? '<div class="banner-propuesta">'
          + '<div><strong>Hay una nueva propuesta de la IA disponible para este plano.</strong> Podés comparar los cambios antes de aplicarlos.</div>'
          + '<div style="display:flex; gap:8px;">'
          + '<button type="button" class="primary" onclick="PH.CUModificar.abrirComparacion()">Ver Antes y Después</button>'
          + '<button type="button" class="ghost" onclick="PH.CUModificar.descartarPropuesta()">Descartar propuesta</button>'
          + '</div>'
          + '</div>'
        : '';

      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getPreviewUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
        + enlaceArchivo
        + bannerPropuesta
        + window.PH.Nomenclatura.formulario('m-', d)
        + CAMPOS.map(function(c) {
            var val = d[c.key] !== undefined && d[c.key] !== null ? d[c.key] : '';
            if (c.type === 'textarea') {
              return '<div class="field"><label for="m-' + c.key + '">' + c.label + '</label>' +
                '<textarea id="m-' + c.key + '" rows="4" readonly>' + esc(val) + '</textarea></div>';
            }
            var type = c.type === 'number' ? 'number' : 'text';
            return '<div class="field"><label>' + c.label + '</label>' +
              '<input type="' + type + '" id="m-' + c.key + '" value="' + attr(val) + '"></div>';
          }).join('')
        + '<div class="field"><label>Motivo del cambio</label>' +
          '<textarea id="m-motivo" rows="3" placeholder="Cuente brevemente por qué se corrige este dato"></textarea></div>'
        + '<div id="m-msg"></div>'
        + historialHTML
        + '<div class="det-actions">'
        + '<button class="ghost" onclick="PH.CUModificar.cancelar()">Cancelar</button>'
        + btnReintentar
        + '<button class="primary" onclick="PH.CUModificar.guardar()">Guardar cambios</button>'
        + '<button class="danger" onclick="PH.CUModificar.eliminar(this)">Eliminar plano</button>'
        + '</div>';

    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  function abrirComparacion() {
    if (!propuestaActual || !planoActual) return;
    var modal = document.getElementById('m-modal-comparacion');
    if (!modal && typeof document.createElement === 'function') {
      modal = document.createElement('div');
      modal.id = 'm-modal-comparacion';
      modal.className = 'modal-backdrop';
      if (document.body) document.body.appendChild(modal);
    }
    if (!modal) return;

    var filas = CAMPOS.map(function(c) {
      var valAnt = planoActual[c.key] !== undefined && planoActual[c.key] !== null ? String(planoActual[c.key]) : '';
      var valNue = propuestaActual[c.key] !== undefined && propuestaActual[c.key] !== null ? String(propuestaActual[c.key]) : '';
      var modificado = valAnt.trim() !== valNue.trim();
      var claseFila = modificado ? ' class="diff-changed"' : '';
      var tag = modificado
        ? '<span class="diff-tag-changed">Modificado</span>'
        : '<span class="diff-tag-same">Sin cambios</span>';
      return '<tr' + claseFila + '>'
        + '<td><strong>' + esc(c.label) + '</strong></td>'
        + '<td>' + (valAnt ? esc(valAnt) : '<em style="color:var(--ink-soft);">(vacío)</em>') + '</td>'
        + '<td>' + (valNue ? esc(valNue) : '<em style="color:var(--ink-soft);">(vacío)</em>') + '</td>'
        + '<td>' + tag + '</td>'
        + '</tr>';
    }).join('');

    modal.innerHTML = '<div class="modal-card">'
      + '<div class="modal-header">'
      + '<h2 id="m-modal-title">Comparación: Antes y Después del análisis IA</h2>'
      + '<button type="button" class="modal-close" onclick="PH.CUModificar.cerrarComparacion()">&times;</button>'
      + '</div>'
      + '<div class="modal-body">'
      + '<p>Revisá los datos guardados actualmente frente a la propuesta sugerida por la IA. Si aplicás los cambios, se cargarán en el formulario para que puedas revisarlos y confirmarlos al guardar.</p>'
      + '<table class="diff-table">'
      + '<thead><tr><th>Campo</th><th>Valor anterior (guardado)</th><th>Nuevo valor sugerido por la IA</th><th>Estado</th></tr></thead>'
      + '<tbody>' + filas + '</tbody>'
      + '</table>'
      + '</div>'
      + '<div class="modal-footer">'
      + '<button type="button" class="ghost" onclick="PH.CUModificar.cerrarComparacion()">Conservar actuales (Descartar)</button>'
      + '<button type="button" class="primary" onclick="PH.CUModificar.aplicarPropuesta()">Aplicar cambios de la IA</button>'
      + '</div>'
      + '</div>';
    if (modal.style) modal.style.display = 'flex';
  }

  function cerrarComparacion() {
    var modal = document.getElementById('m-modal-comparacion');
    if (modal && modal.style) modal.style.display = 'none';
  }


  async function descartarPropuesta() {
    if (!seleccionadoId) return;
    try {
      await API.descartarPropuesta(seleccionadoId);
      propuestaActual = null;
      cerrarComparacion();
      await renderDetalle();
      var msg = document.getElementById('m-msg');
      if (msg) msg.innerHTML = '<div class="confirm">Se descartó la propuesta de la IA y se conservaron los valores actuales.</div>';
    } catch (e) {
      var m = document.getElementById('m-msg');
      if (m) m.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  function aplicarPropuesta() {
    if (!propuestaActual) return;
    CAMPOS.forEach(function(c) {
      var el = document.getElementById('m-' + c.key);
      if (el) {
        var val = propuestaActual[c.key];
        el.value = (val !== undefined && val !== null) ? val : '';
      }
    });
    var motEl = document.getElementById('m-motivo');
    if (motEl && !motEl.value.trim()) {
      motEl.value = 'Actualización por reanálisis de IA';
    }
    cerrarComparacion();
    var msg = document.getElementById('m-msg');
    if (msg) {
      msg.innerHTML = '<div class="confirm"><strong>Se cargaron los datos sugeridos por la IA en el formulario.</strong> Revisalos y hacé clic en "Guardar cambios" para confirmarlos definitivamente.</div>';
    }
  }

  async function guardar() {
    if (!seleccionadoId) return;

    var motivo = document.getElementById('m-motivo').value.trim();
    if (!motivo) {
      document.getElementById('m-msg').innerHTML = '<div class="error">El motivo del cambio es obligatorio para guardar.</div>';
      return;
    }

    var datos = {};
    CAMPOS.forEach(function(c) {
      if (c.readonly) return;
      var v = document.getElementById('m-' + c.key).value.trim();
      datos[c.key] = v || null;
    });
    try { Object.assign(datos, window.PH.Nomenclatura.leer('m-')); }
    catch (e) { document.getElementById('m-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>'; return; }
    datos.motivo = motivo;
    datos.usuario_id = "Operador"; // Hardcoded for now

    try {
      await API.modificar(seleccionadoId, datos);
      propuestaActual = null;
      cerrarComparacion();
      renderLista();
      await renderDetalle();
      document.getElementById('m-msg').innerHTML = '<div class="confirm">Los cambios se guardaron correctamente.</div>';
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('m-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  async function reintentar(id) {
    if (!id) return;
    var btn = document.getElementById('m-btn-reintentar');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Iniciando reanálisis...';
    }
    var msg = document.getElementById('m-msg');
    if (msg) {
      msg.innerHTML = '<div class="info">Iniciando reanálisis con IA...</div>';
    }

    try {
      await API.reintentarIA(id, "Operador");
      if (msg) {
        msg.innerHTML = '<div class="info">Procesando plano con IA... Esto puede demorar unos segundos.</div>';
      }

      var intentosPoll = 0;
      var maxPoll = 40; // 40 * 1.5s = 60s
      var interval = setInterval(async function() {
        intentosPoll++;
        try {
          var doc = await API.getById(id);
          if (doc.ia_estado !== 'procesando' || intentosPoll >= maxPoll) {
            clearInterval(interval);
            await renderDetalle();
            if (doc.ia_estado === 'completado') {
              if (doc.ia_propuesta) {
                abrirComparacion();
              } else {
                var m = document.getElementById('m-msg');
                if (m) m.innerHTML = '<div class="confirm">Reanálisis de IA completado.</div>';
              }
            } else if (doc.ia_estado === 'error') {
              var m2 = document.getElementById('m-msg');
              if (m2) m2.innerHTML = '<div class="error">El análisis automático no pudo completarse.</div>';
            }
            if (window.PH.actualizarListas) window.PH.actualizarListas();
          }
        } catch (pollErr) {
          clearInterval(interval);
          await renderDetalle();
        }
      }, 1500);

    } catch (e) {
      if (msg) {
        msg.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
      }
      await renderDetalle();
    }
  }

  async function eliminar(boton) {
    if (!seleccionadoId || !window.confirm('¿Eliminar este plano, su archivo y su historial permanentemente?')) return;
    if (boton) boton.disabled = true;
    try {
      await API.eliminar(seleccionadoId);
      seleccionadoId = null;
      planoActual = null;
      propuestaActual = null;
      cerrarComparacion();
      await renderLista();
      await renderDetalle();
      document.getElementById('modificar-detalle').innerHTML = '<div class="confirm">El plano se eliminó correctamente.</div>';
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('m-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    } finally { if (boton) boton.disabled = false; }
  }

  window.PH = window.PH || {};
  window.PH.CUModificar = {
    renderLista: renderLista,
    renderDetalle: renderDetalle,
    seleccionar: seleccionar,
    cancelar: cancelar,
    guardar: guardar,
    reintentar: reintentar,
    abrirComparacion: abrirComparacion,
    cerrarComparacion: cerrarComparacion,
    aplicarPropuesta: aplicarPropuesta,
    descartarPropuesta: descartarPropuesta,
    eliminar: eliminar
  };

})(window);
