/**
 * cu-modificar.js - CU3: Modificar catalogación de plano histórico.
 */
(function(window) {
  'use strict';

  var API = window.PH.API;
  var seleccionadoId = null;

  var CAMPOS = [
    { key: 'texto_extraido', label: 'Texto extraído', type: 'textarea' },
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
    renderDetalle();
    renderLista();
  }

  function cancelar() {
    seleccionadoId = null;
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

      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getPreviewUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
        + enlaceArchivo
        + window.PH.Nomenclatura.formulario('m-', d)
        + CAMPOS.map(function(c) {
            var val = d[c.key] !== undefined && d[c.key] !== null ? d[c.key] : '';
            if (c.type === 'textarea') {
              return '<div class="field"><label>' + c.label + '</label>' +
                '<textarea id="m-' + c.key + '" rows="4">' + esc(val) + '</textarea></div>';
            }
            var type = c.type === 'number' ? 'number' : 'text';
            return '<div class="field"><label>' + c.label + '</label>' +
              '<input type="' + type + '" id="m-' + c.key + '" value="' + attr(val) + '"></div>';
          }).join('')
        + '<div class="field"><label>Motivo del cambio</label>' +
          '<textarea id="m-motivo" rows="3" placeholder="Cuente brevemente por qué se corrige este dato"></textarea></div>'
        + '<div id="m-msg"></div>'
        + historialHTML
        + '<div class="det-actions">' +
          '<button class="ghost" onclick="PH.CUModificar.cancelar()">Cancelar</button>' +
          '<button class="primary" onclick="PH.CUModificar.guardar()">Guardar cambios</button>' +
          '<button class="danger" onclick="PH.CUModificar.eliminar(this)">Eliminar plano</button>' +
          '</div>';

    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
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
      var v = document.getElementById('m-' + c.key).value.trim();
      datos[c.key] = v || null;
    });
    try { Object.assign(datos, window.PH.Nomenclatura.leer('m-')); }
    catch (e) { document.getElementById('m-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>'; return; }
    datos.motivo = motivo;
    datos.usuario_id = "Operador"; // Hardcoded for now

    try {
      await API.modificar(seleccionadoId, datos);
      renderLista();
      await renderDetalle();
      document.getElementById('m-msg').innerHTML = '<div class="confirm">Los cambios se guardaron correctamente.</div>';
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('m-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  async function eliminar(boton) {
    if (!seleccionadoId || !window.confirm('¿Eliminar este plano, su archivo y su historial permanentemente?')) return;
    if (boton) boton.disabled = true;
    try {
      await API.eliminar(seleccionadoId);
      seleccionadoId = null;
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
    eliminar: eliminar
  };

})(window);

