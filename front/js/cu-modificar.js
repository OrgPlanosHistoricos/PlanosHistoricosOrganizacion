/**
 * cu-modificar.js - CU3: Modificar catalogación de plano histórico.
 * Actor: Validador documental. Corrige datos de un plano ya validado;
 * toda modificación exige un motivo y queda registrada en el historial.
 */
(function(window) {
  'use strict';

  var State = window.PH.State;
  var CONDICIONES = ['Aprobado', 'Conforme a obra', 'Derogado', 'Documento técnico no oficializado'];
  var seleccionadoId = null;

  function esc(s) {
    return (s === undefined || s === null || s === '') ? '' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function attr(s) { return String(s || '').replace(/"/g, '&quot;'); }
  function tituloDoc(d) {
    return d.origen.direccion || d.origen.expediente || d.archivoNombre;
  }

  function renderLista() {
    var cont = document.getElementById('modificar-lista');
    var indexados = State.getAll().filter(function(d) { return d.estado === 'validado'; });

    if (indexados.length === 0) {
      cont.innerHTML = '<div class="empty">Todavía no hay planos catalogados.</div>';
      return;
    }
    cont.innerHTML = indexados.map(function(d) {
      var sel = d.id === seleccionadoId ? ' sel' : '';
      var badge = d.ubicacionAsignada === false
        ? '<span class="badge sin_ubicacion">Sin ubicación</span>'
        : '<span class="badge validado">Validado</span>';
      return '<button class="row' + sel + '" onclick="PH.CUModificar.seleccionar(\'' + d.id + '\')">' +
        '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
        '<div class="s">' + badge + '</div>' +
        '</button>';
    }).join('');
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

  function renderDetalle() {
    var cont = document.getElementById('modificar-detalle');
    var d = seleccionadoId ? State.getById(seleccionadoId) : null;

    if (!d) {
      cont.innerHTML = '<div class="empty">Elija un plano catalogado para modificarlo.</div>';
      return;
    }

    var historialHTML = d.historial.length
      ? '<div class="hist"><h3>Historial de cambios</h3><ul>' +
        d.historial.slice().reverse().map(function(h) {
          return '<li><strong>' + esc(h.fecha) + '</strong> — ' + esc(h.motivo) + '</li>';
        }).join('') + '</ul></div>'
      : '';

    cont.innerHTML = ''
      + '<img class="thumb" src="' + d.archivoUrl + '" alt="Plano ' + esc(d.id) + '">'
      + '<div class="field"><label>Dirección o parcela</label><input type="text" id="m-direccion" value="' + attr(d.direccionVinculada) + '"></div>'
      + '<div class="field"><label>Fecha</label><input type="text" id="m-fecha" value="' + attr(d.datos.fecha) + '"></div>'
      + '<div class="field"><label>Condición legal</label>' +
        '<select id="m-condicion"><option value="">Sin definir</option>' +
        CONDICIONES.map(function(c) { return '<option' + (d.condicionLegal === c ? ' selected' : '') + '>' + c + '</option>'; }).join('') +
        '</select></div>'
      + '<div class="field"><label>Motivo del cambio</label>' +
        '<textarea id="m-motivo" rows="3" placeholder="Cuente brevemente por qué se corrige este dato"></textarea></div>'
      + '<div id="m-msg"></div>'
      + historialHTML
      + '<div class="det-actions">' +
        '<button class="ghost" onclick="PH.CUModificar.cancelar()">Cancelar</button>' +
        '<button class="primary" onclick="PH.CUModificar.guardar()">Guardar cambios</button>' +
        '</div>';
  }

  function guardar() {
    var d = seleccionadoId ? State.getById(seleccionadoId) : null;
    if (!d) return;

    var motivo = document.getElementById('m-motivo').value.trim();
    if (!motivo) {
      document.getElementById('m-msg').innerHTML = '<div class="error">El motivo del cambio es obligatorio para guardar.</div>';
      return;
    }

    var direccion = document.getElementById('m-direccion').value.trim();
    var fecha = document.getElementById('m-fecha').value.trim();
    var condicion = document.getElementById('m-condicion').value;
    var datos = Object.assign({}, d.datos, { fecha: fecha });

    State.update(d.id, {
      direccionVinculada: direccion,
      ubicacionAsignada: !!direccion,
      datos: datos,
      condicionLegal: condicion,
      historial: d.historial.concat([{ fecha: new Date().toLocaleString('es-AR'), motivo: motivo }])
    });

    renderLista();
    renderDetalle();
    document.getElementById('m-msg').innerHTML = '<div class="confirm">Los cambios se guardaron correctamente.</div>';
    if (window.PH.actualizarListas) window.PH.actualizarListas();
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
