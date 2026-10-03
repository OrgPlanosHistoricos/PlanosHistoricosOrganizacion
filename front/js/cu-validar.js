/**
 * cu-validar.js - CU2: Validar y catalogar plano histórico (HITL).
 */
(function(window) {
  'use strict';

  var API = window.PH.API;
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
  
  var seleccionadoId = null;

  function esc(s) {
    return (s === undefined || s === null || s === '') ? '' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function attr(s) { return String(s || '').replace(/"/g, '&quot;'); }
  function tituloDoc(d) {
    return d.direccion_referencia || d.expediente || d.nombre_original;
  }

  async function renderLista() {
    var cont = document.getElementById('validar-lista');
    try {
      var pendientes = await API.getAll('pendiente');
      // Asegurar que si está procesando la IA no se pueda validar aún
      pendientes = pendientes.filter(d => d.ia_estado !== 'procesando');

      if (pendientes.length === 0) {
        cont.innerHTML = '<div class="empty">No hay planos pendientes de revisión.</div>';
        return;
      }
      cont.innerHTML = pendientes.map(function(d) {
        var sel = d.id === seleccionadoId ? ' sel' : '';
        return '<button class="row' + sel + '" onclick="PH.CUValidar.seleccionar(' + d.id + ')">' +
          '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
          '<div class="s">' + esc(d.expediente || 'sin expediente') + '</div>' +
          '</button>';
      }).join('');
    } catch (e) {
      cont.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
    }
  }

  function seleccionar(id) {
    seleccionadoId = id;
    renderDetalle();
    renderLista(); // Para actualizar selección visual
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

  async function renderDetalle() {
    var cont = document.getElementById('validar-detalle');
    
    if (!seleccionadoId) {
      cont.innerHTML = '<div class="empty">Elija un plano pendiente de la lista para revisarlo.</div>';
      return;
    }

    try {
      var d = await API.getById(seleccionadoId);
      if (d.estado !== 'pendiente') {
        seleccionadoId = null;
        cont.innerHTML = '<div class="empty">Elija un plano pendiente de la lista para revisarlo.</div>';
        return;
      }

      var aviso = '<div class="confirm">Datos leídos automáticamente. Revíselos y corríjalos si hace falta.</div>';

      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getArchivoUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
        + aviso
        + CAMPOS.map(function(c) {
            var val = d[c.key] !== undefined && d[c.key] !== null ? d[c.key] : '';
            if (c.type === 'textarea') {
              return '<div class="field"><label>' + c.label + '</label>' +
                '<textarea id="v-' + c.key + '" rows="4">' + esc(val) + '</textarea></div>';
            }
            var type = c.type === 'number' ? 'number' : 'text';
            return '<div class="field"><label>' + c.label + '</label>' +
              '<input type="' + type + '" id="v-' + c.key + '" value="' + attr(val) + '"></div>';
          }).join('')
        + '<div class="field"><label>Parcela vinculada</label>' +
          '<input type="text" id="v-vinculo" value="' + attr(d.parcela) + '" ' + (d.estado === 'sin_ubicacion' ? 'disabled' : '') + '>' +
          '<label style="display:flex;align-items:center;gap:6px;margin-top:6px;font-weight:400;">' +
          '<input type="checkbox" id="v-sinubic" style="width:auto" ' + (d.estado === 'sin_ubicacion' ? 'checked' : '') + ' onchange="PH.CUValidar.toggleSinUbicacion(this.checked)">' +
          'No se encuentra la parcela o dirección exacta</label>'
        + '</div>'
        + '<div id="v-msg"></div>'
        + '<div class="actions">' +
          '<button class="ghost" onclick="PH.CUValidar.cancelar()">Cancelar</button>' +
          '<button class="primary" onclick="PH.CUValidar.confirmar()">Confirmar e indexar</button>' +
          '</div>';

    } catch (e) {
      cont.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
    }
  }

  async function confirmar() {
    if (!seleccionadoId) return;

    var nuevosDatos = {};
    CAMPOS.forEach(function(c) {
      var v = document.getElementById('v-' + c.key).value.trim();
      nuevosDatos[c.key] = v || null;
    });

    var sinUbic = document.getElementById('v-sinubic').checked;
    var vinculo = document.getElementById('v-vinculo').value.trim();

    if (!sinUbic && !vinculo) {
      document.getElementById('v-msg').innerHTML = '<div class="error">Vincule una parcela, o marque que no se encuentra.</div>';
      return;
    }

    nuevosDatos.parcela = sinUbic ? '' : vinculo;

    try {
      await API.validar(seleccionadoId, nuevosDatos);
      seleccionadoId = null;
      renderLista();
      renderDetalle();
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('v-msg').innerHTML = '<div class="error">Error: ' + e.message + '</div>';
    }
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

