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
    return d.direccion_referencia || d.expediente || d.nombre_original;
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
      cont.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
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

      var historialHTML = d.historial && d.historial.length
        ? '<div class="hist"><h3>Historial de cambios</h3><ul>' +
          d.historial.slice().reverse().map(function(h) {
            var date = new Date(h.fecha).toLocaleString('es-AR');
            return '<li><strong>' + esc(date) + '</strong> — ' + esc(h.motivo) + '</li>';
          }).join('') + '</ul></div>'
        : '';

      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getArchivoUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
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
        + '<div class="field"><label>Parcela</label><input type="text" id="m-parcela" value="' + attr(d.parcela) + '"></div>'
        + '<div class="field"><label>Motivo del cambio</label>' +
          '<textarea id="m-motivo" rows="3" placeholder="Cuente brevemente por qué se corrige este dato"></textarea></div>'
        + '<div id="m-msg"></div>'
        + historialHTML
        + '<div class="det-actions">' +
          '<button class="ghost" onclick="PH.CUModificar.cancelar()">Cancelar</button>' +
          '<button class="primary" onclick="PH.CUModificar.guardar()">Guardar cambios</button>' +
          '</div>';

    } catch (e) {
      cont.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
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
    datos.parcela = document.getElementById('m-parcela').value.trim();
    datos.motivo = motivo;

    try {
      await API.modificar(seleccionadoId, datos);
      renderLista();
      renderDetalle();
      document.getElementById('m-msg').innerHTML = '<div class="confirm">Los cambios se guardaron correctamente.</div>';
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('m-msg').innerHTML = '<div class="error">Error: ' + e.message + '</div>';
    }
  }

  window.PH = window.PH || {};
  window.PH.CUModificar = {
    renderLista: renderLista,
    renderDetalle: renderDetalle,
    seleccionar: seleccionar,
    cancelar: cancelar,
    guardar: guardar
  };

})(window);

