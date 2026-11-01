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

  function snapshot(valor) {
    if (!valor) return null;
    if (typeof valor === 'object') return valor;
    try { return JSON.parse(valor); } catch (e) { return valor; }
  }

  function textoHistorial(valor) {
    var texto = String(valor === null || valor === undefined || valor === '' ? '—' : valor);
    var caracteres = Array.from(texto);
    return esc(caracteres.length > 180 ? caracteres.slice(0, 179).join('') + '…' : texto);
  }

  function valoresHistorial(valor, otro) {
    var datos = snapshot(valor);
    var comparacion = snapshot(otro);
    if (!datos) return '—';
    if (typeof datos !== 'object') return textoHistorial(datos);
    var campos = Object.keys(datos).filter(function(key) {
      return !comparacion || typeof comparacion !== 'object' ||
        JSON.stringify(datos[key]) !== JSON.stringify(comparacion[key]);
    });
    return textoHistorial(campos.map(function(key) {
      var campo = CAMPOS.find(function(c) { return c.key === key; });
      var valorCampo = datos[key];
      return (campo ? campo.label : key.replace(/_/g, ' ')) +
        ': ' + (valorCampo === null || valorCampo === '' ? '—' : valorCampo);
    }).join('; '));
  }

  function alternarHistorial(boton) {
    var detalle = document.getElementById(boton.getAttribute('aria-controls'));
    detalle.hidden = !detalle.hidden;
    boton.setAttribute('aria-expanded', String(!detalle.hidden));
    boton.textContent = detalle.hidden ? 'Ver detalle' : 'Ocultar detalle';
  }

  function detalleCambios(evento) {
    var anterior = snapshot(evento.valores_anteriores);
    var nuevo = snapshot(evento.valores_nuevos);
    if ((!anterior || typeof anterior === 'object') && (!nuevo || typeof nuevo === 'object')) {
      var claves = Array.from(new Set(Object.keys(anterior || {}).concat(Object.keys(nuevo || {}))));
      return claves.filter(function(key) {
        var antes = anterior && anterior[key] !== undefined ? anterior[key] : null;
        var despues = nuevo && nuevo[key] !== undefined ? nuevo[key] : null;
        if (key === 'escala') {
          antes = window.PH.normalizarEscala(antes);
          despues = window.PH.normalizarEscala(despues);
        }
        return JSON.stringify(antes) !== JSON.stringify(despues);
      }).map(function(key) {
        var campo = CAMPOS.find(function(c) { return c.key === key; });
        var etiqueta = campo ? campo.label : key.replace(/_/g, ' ');
        return '<div class="hist-change"><strong>' + esc(etiqueta) + '</strong>' +
          '<div class="hist-values"><div><span>Valor anterior</span><br>' + textoHistorial(anterior && anterior[key]) + '</div>' +
          '<div><span>Valor nuevo</span><br>' + textoHistorial(nuevo && nuevo[key]) + '</div></div></div>';
      }).join('') || '<p>No hay cambios de campos registrados para este evento.</p>';
    }
    return '<p><strong>Valor anterior</strong><br>' + valoresHistorial(evento.valores_anteriores, evento.valores_nuevos) + '</p>' +
      '<p><strong>Valor nuevo</strong><br>' + valoresHistorial(evento.valores_nuevos, evento.valores_anteriores) + '</p>';
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
          ? '<span class="badge sin_ubicacion">Sin parcela asignada</span>'
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

  var paginaHistorial = 1;

  function crearHistorial() {
      var historial = planoActual.eventos || planoActual.historial || [];
      var paginas = Math.max(1, Math.ceil(historial.length / 10));
      paginaHistorial = Math.max(1, Math.min(paginaHistorial, paginas));
      return historial.length
        ? '<div class="hist" id="m-historial"><h3>Historial de cambios</h3><div class="hist-scroll">' +
          '<table class="hist-table"><thead><tr><th scope="col">Fecha</th><th scope="col">Hora</th>' +
          '<th scope="col">Usuario</th><th scope="col">Motivo</th><th scope="col">Detalle</th></tr></thead><tbody>' +
          historial.slice().sort(function(a, b) {
            return (Date.parse(b.fecha) || 0) - (Date.parse(a.fecha) || 0) || (b.id || 0) - (a.id || 0);
          }).slice((paginaHistorial - 1) * 10, paginaHistorial * 10).map(function(h, indice) {
            var fecha = new Date(h.fecha);
            var valida = !isNaN(fecha.getTime());
            return '<tr><td>' + (valida ? esc(fecha.toLocaleDateString('es-AR')) : '—') +
              '</td><td>' + (valida ? esc(fecha.toLocaleTimeString('es-AR', { hour12: false })) : '—') +
              '</td><td>' + textoHistorial(h.usuario_id) + '</td><td>' + textoHistorial(h.motivo) + '</td><td>' +
              '<button type="button" class="ghost hist-toggle" aria-expanded="false" aria-controls="hist-detalle-' + indice + '" onclick="PH.CUModificar.alternarHistorial(this)">Ver detalle</button></td></tr>' +
              '<tr id="hist-detalle-' + indice + '" hidden><td colspan="5" class="hist-detail">' +
              detalleCambios(h) + '</td></tr>';
          }).join('') + '</tbody></table></div>' +
          '<div class="pagination">Página ' + paginaHistorial + ' de ' + paginas + ' · ' + historial.length + ' cambios</div>' +
          '<div class="pagination-actions"><button type="button" class="ghost" onclick="PH.CUModificar.cambiarPaginaHistorial(-1)"' + (paginaHistorial === 1 ? ' disabled' : '') + '>Anterior</button>' +
          '<button type="button" class="ghost" onclick="PH.CUModificar.cambiarPaginaHistorial(1)"' + (paginaHistorial === paginas ? ' disabled' : '') + '>Siguiente</button></div></div>'
        : '';

  }

  function cambiarPaginaHistorial(paso) {
    if (!planoActual) return;
    var cont = document.getElementById('m-historial');
    if (!cont) return;
    paginaHistorial += paso;
    cont.outerHTML = crearHistorial();
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

      paginaHistorial = 1;
      var historialHTML = crearHistorial();

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
          + '<div>Hay una nueva propuesta de la IA disponible para este plano.</div>'
          + '<div style="display:flex; gap:8px;">'
          + '<button type="button" class="primary" onclick="PH.CUModificar.abrirComparacion()">Ver Antes y Después</button>'
          + '<button type="button" class="ghost" onclick="PH.CUModificar.descartarPropuesta()">Descartar propuesta</button>'
          + '</div>'
          + '</div>'
        : '';

      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getPreviewUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
        + enlaceArchivo
        + '<div class="det-actions det-actions-plano">'
        + '<button class="danger" onclick="PH.CUModificar.eliminar(this)">Eliminar plano</button>'
        + btnReintentar
        + '</div>'
        + bannerPropuesta
        + window.PH.Nomenclatura.formulario('m-', d)
        + CAMPOS.map(function(c) {
            var val = d[c.key] !== undefined && d[c.key] !== null ? d[c.key] : '';
            if (c.key === 'escala') val = window.PH.normalizarEscala(val) || '';
            if (c.type === 'textarea') {
              return '<div class="field"><label for="m-' + c.key + '">' + c.label + '</label>' +
                '<textarea id="m-' + c.key + '" rows="4" readonly>' + esc(val) + '</textarea></div>';
            }
            var type = c.type === 'number' ? 'number' : 'text';
            return '<div class="field"><label>' + c.label + '</label>' +
              '<input type="' + type + '"' + (type === 'number' ? ' min="1" step="1"' : '') + ' id="m-' + c.key + '" value="' + attr(val) + '"></div>';
          }).join('')
        + '<div class="field"><label for="m-motivo">Motivo de la modificación (obligatorio)</label>' +
          '<textarea id="m-motivo" rows="3" maxlength="180" required aria-required="true" aria-describedby="m-motivo-contador" oninput="PH.CUModificar.actualizarContadorMotivo()" placeholder="Cuente brevemente por qué se corrige este dato"></textarea>' +
          '<small id="m-motivo-contador" class="motivo-contador">0 / 180 caracteres</small></div>'
        + '<div id="m-msg"></div>'
        + '<div class="det-actions">'
        + '<button class="ghost" onclick="PH.CUModificar.cancelar()">Cancelar</button>'
        + '<button class="primary" onclick="PH.CUModificar.guardar()">Guardar cambios</button>'
        + '</div>'
        + historialHTML;

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
        + '<td class="diff-select">' + (modificado
          ? '<input type="checkbox" id="m-aplicar-' + c.key + '" checked aria-label="Aplicar valor de la IA: ' + attr(c.label) + '">'
          : '—') + '</td>'
        + '</tr>';
    }).join('');

    modal.innerHTML = '<div class="modal-card">'
      + '<div class="modal-header">'
      + '<h2 id="m-modal-title">Comparación: Antes y Después del análisis IA</h2>'
      + '<button type="button" class="modal-close" onclick="PH.CUModificar.cerrarComparacion()">&times;</button>'
      + '</div>'
      + '<div class="modal-body">'
      + '<p>Marcá los campos cuyo valor sugerido por la IA querés aplicar. Los campos desmarcados conservarán sus valores actuales. Los cambios seleccionados se cargarán en el formulario para que puedas revisarlos y confirmarlos al guardar.</p>'
      + '<table class="diff-table">'
      + '<thead><tr><th>Campo</th><th>Valor anterior (guardado)</th><th>Nuevo valor sugerido por la IA</th><th>Estado</th><th>Aplicar</th></tr></thead>'
      + '<tbody>' + filas + '</tbody>'
      + '</table>'
      + '</div>'
      + '<div class="modal-footer">'
      + '<button type="button" class="ghost" onclick="PH.CUModificar.cerrarComparacion()">Cancelar</button>'
      + '<button type="button" class="primary" onclick="PH.CUModificar.aplicarPropuesta()">Aplicar cambios</button>'
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

  function actualizarContadorMotivo() {
    var motivo = document.getElementById('m-motivo');
    var contador = document.getElementById('m-motivo-contador');
    if (motivo && contador) contador.textContent = motivo.value.length + ' / 180 caracteres';
  }

  function aplicarPropuesta() {
    if (!propuestaActual) return;
    var aplicados = 0;
    CAMPOS.forEach(function(c) {
      var seleccion = document.getElementById('m-aplicar-' + c.key);
      if (!seleccion) return;
      var el = document.getElementById('m-' + c.key);
      if (el) {
        var val = seleccion.checked ? propuestaActual[c.key] : planoActual[c.key];
        if (c.key === 'escala') val = window.PH.normalizarEscala(val);
        el.value = (val !== undefined && val !== null) ? val : '';
        if (seleccion.checked) aplicados++;
      }
    });
    var motEl = document.getElementById('m-motivo');
    if (aplicados && motEl && !motEl.value.trim()) {
      motEl.value = 'Actualización por análisis de IA';
    }
    actualizarContadorMotivo();
    cerrarComparacion();
    var msg = document.getElementById('m-msg');
    if (msg) {
      msg.innerHTML = aplicados
        ? '<div class="confirm"><strong>Se cargaron los cambios seleccionados de la IA en el formulario.</strong> Revisalos y hacé clic en "Guardar cambios" para confirmarlos definitivamente.</div>'
        : '<div class="confirm">No se seleccionaron cambios de la IA. Se conservaron los valores actuales del formulario.</div>';
    }
  }

  async function guardar() {
    if (!seleccionadoId) return;

    var motivo = document.getElementById('m-motivo').value.trim();
    if (document.getElementById('m-motivo').value.length > 180) {
      document.getElementById('m-msg').innerHTML = '<div class="error">El motivo no puede superar los 180 caracteres.</div>';
      return;
    }
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
    if (datos.anio !== null && (!Number.isSafeInteger(Number(datos.anio)) || Number(datos.anio) <= 0)) {
      document.getElementById('m-msg').innerHTML = '<div class="error">El año debe ser un número entero mayor que cero o quedar vacío.</div>';
      return;
    }
    datos.escala = window.PH.normalizarEscala(datos.escala);
    if (!window.PH.validarEscala(datos.escala)) {
      document.getElementById('m-msg').innerHTML = '<div class="error">La escala debe tener formato 1:100, o indicar Sin escala o Escalas varias.</div>';
      return;
    }
    try { Object.assign(datos, window.PH.Nomenclatura.leer('m-')); }
    catch (e) { document.getElementById('m-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>'; return; }
    datos.motivo = motivo;

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
    alternarHistorial: alternarHistorial,
    cambiarPaginaHistorial: cambiarPaginaHistorial,
    renderDetalle: renderDetalle,
    seleccionar: seleccionar,
    cancelar: cancelar,
    guardar: guardar,
    actualizarContadorMotivo: actualizarContadorMotivo,
    reintentar: reintentar,
    abrirComparacion: abrirComparacion,
    cerrarComparacion: cerrarComparacion,
    aplicarPropuesta: aplicarPropuesta,
    descartarPropuesta: descartarPropuesta,
    eliminar: eliminar
  };

})(window);
