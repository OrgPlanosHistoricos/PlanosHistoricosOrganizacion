/**
 * cu-validar.js - CU2: Validar y catalogar plano histórico (HITL).
 * Actor: Validador documental. Revisa los datos leídos automáticamente,
 * los corrige y vincula el plano a su dirección o parcela.
 */
(function(window) {
  'use strict';

  var State = window.PH.State;
  var CAMPOS = [
    { key: 'propietario', label: 'Propietario' },
    { key: 'direccion', label: 'Dirección' },
    { key: 'nomenclatura', label: 'Nomenclatura catastral' },
    { key: 'fecha', label: 'Fecha' },
    { key: 'sellos', label: 'Sellos' },
    { key: 'superficie', label: 'Superficie' }
  ];
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
    var cont = document.getElementById('validar-lista');
    var pendientes = State.getAll().filter(function(d) { return d.estado === 'pendiente'; });

    if (pendientes.length === 0) {
      cont.innerHTML = '<div class="empty">No hay planos pendientes de revisión.</div>';
      return;
    }
    cont.innerHTML = pendientes.map(function(d) {
      var sel = d.id === seleccionadoId ? ' sel' : '';
      return '<button class="row' + sel + '" onclick="PH.CUValidar.seleccionar(\'' + d.id + '\')">' +
        '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
        '<div class="s">' + esc(d.origen.expediente || 'sin expediente') + '</div>' +
        '</button>';
    }).join('');
  }

  function seleccionar(id) {
    seleccionadoId = id;
    renderDetalle();
    renderLista();
  }
  function getSeleccionadoId() { return seleccionadoId; }

  function cancelar() {
    seleccionadoId = null;
    renderDetalle();
    renderLista();
  }

  function toggleSinUbicacion(checked) {
    var input = document.getElementById('v-vinculo');
    input.disabled = checked;
    if (checked) input.value = '';
  }

  function renderDetalle() {
    var cont = document.getElementById('validar-detalle');
    var d = seleccionadoId ? State.getById(seleccionadoId) : null;

    if (!d || d.estado !== 'pendiente') {
      seleccionadoId = null;
      cont.innerHTML = '<div class="empty">Elija un plano pendiente de la lista para revisarlo.</div>';
      return;
    }

    var huboDeterioro = CAMPOS.some(function(c) { return !d.datos[c.key]; });
    var aviso = huboDeterioro
      ? '<div class="hint">La lectura automática no reconoció algunos datos por el estado del documento. Complételos manualmente mirando la imagen.</div>'
      : '<div class="confirm">Datos leídos automáticamente. Revíselos y corríjalos si hace falta.</div>';

    cont.innerHTML = ''
      + '<img class="thumb" src="' + d.archivoUrl + '" alt="Plano ' + esc(d.id) + '">'
      + aviso
      + CAMPOS.map(function(c) {
          return '<div class="field"><label>' + c.label + '</label>' +
            '<input type="text" id="v-' + c.key + '" value="' + attr(d.datos[c.key]) + '"></div>';
        }).join('')
      + '<div class="field"><label>Condición legal</label>' +
        '<select id="v-condicion"><option value="">Sin definir</option>' +
        CONDICIONES.map(function(c) { return '<option' + (d.condicionLegal === c ? ' selected' : '') + '>' + c + '</option>'; }).join('') +
        '</select></div>'
      + '<div class="field"><label>Dirección o parcela vinculada</label>' +
        '<input type="text" id="v-vinculo" value="' + attr(d.direccionVinculada) + '" ' + (d.ubicacionAsignada === false ? 'disabled' : '') + '>' +
        '<label style="display:flex;align-items:center;gap:6px;margin-top:6px;font-weight:400;">' +
        '<input type="checkbox" id="v-sinubic" style="width:auto" ' + (d.ubicacionAsignada === false ? 'checked' : '') + ' onchange="PH.CUValidar.toggleSinUbicacion(this.checked)">' +
        'No se encuentra la parcela o dirección exacta</label>'
      + '</div>'
      + '<div id="v-msg"></div>'
      + '<div class="actions">' +
        '<button class="ghost" onclick="PH.CUValidar.cancelar()">Cancelar</button>' +
        '<button class="primary" onclick="PH.CUValidar.confirmar()">Confirmar e indexar</button>' +
        '</div>';
  }

  function confirmar() {
    var d = seleccionadoId ? State.getById(seleccionadoId) : null;
    if (!d) return;

    var nuevosDatos = {};
    CAMPOS.forEach(function(c) { nuevosDatos[c.key] = document.getElementById('v-' + c.key).value.trim(); });
    var condicion = document.getElementById('v-condicion').value;
    var sinUbic = document.getElementById('v-sinubic').checked;
    var vinculo = document.getElementById('v-vinculo').value.trim();

    if (!sinUbic && !vinculo) {
      document.getElementById('v-msg').innerHTML = '<div class="error">Vincule una dirección o parcela, o marque que no se encuentra.</div>';
      return;
    }

    State.update(d.id, {
      datos: nuevosDatos,
      condicionLegal: condicion,
      ubicacionAsignada: !sinUbic,
      direccionVinculada: sinUbic ? '' : vinculo,
      estado: 'validado',
      historial: d.historial.concat([{ fecha: new Date().toLocaleString('es-AR'), motivo: 'Catalogación inicial' }])
    });

    seleccionadoId = null;
    renderLista();
    renderDetalle();
    if (window.PH.actualizarListas) window.PH.actualizarListas();
  }

  window.PH = window.PH || {};
  window.PH.CUValidar = {
    renderLista: renderLista,
    renderDetalle: renderDetalle,
    seleccionar: seleccionar,
    getSeleccionadoId: getSeleccionadoId,
    toggleSinUbicacion: toggleSinUbicacion,
    cancelar: cancelar,
    confirmar: confirmar
  };

})(window);
