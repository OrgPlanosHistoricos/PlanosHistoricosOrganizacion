/**
 * cu-cargar.js - CU1: Cargar plano histórico.
 */
(function(window) {
  'use strict';

  var API = window.PH.API;

  function esc(s) {
    return (s === undefined || s === null || s === '') ? '' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function tituloDoc(d) {
    return d.direccion_referencia || d.expediente || d.nombre_original;
  }
  function respuestaInvalida(d) {
    return d.ia_error && d.ia_error.indexOf('JSON válido') !== -1;
  }

  function mostrarMensaje(tipo, texto) {
    document.getElementById('cargar-msgs').innerHTML = '<div class="' + tipo + '">' + texto + '</div>';
  }
  function limpiarMensaje() {
    document.getElementById('cargar-msgs').innerHTML = '';
  }


  function inicializar() {
    var form = document.getElementById('form-cargar');
    form.addEventListener('submit', function(ev) {
      ev.preventDefault();
      onSubmit();
    });
  }

  async function onSubmit() {
    limpiarMensaje();
    var fileInput = document.getElementById('f-archivo');
    var file = fileInput.files[0];

    if (!file) {
      mostrarMensaje('error', 'El archivo digital del plano es obligatorio para continuar.');
      return;
    }
    var okExt = /\.(jpe?g|png|webp|pdf)$/i.test(file.name);
    if (!okExt) {
      mostrarMensaje('error', 'El formato del archivo no es válido o está dañado. Usá JPG, PNG, WEBP o PDF.');
      return;
    }

    var ubicacion = document.getElementById('f-ubic').value.trim();
    var expediente = document.getElementById('f-exp').value.trim();
    var direccion = document.getElementById('f-dir').value.trim();

    try {
      mostrarMensaje('pulse', 'Subiendo archivo e iniciando procesamiento...');
      var doc = await API.create(file, ubicacion, expediente, direccion);
      document.getElementById('form-cargar').reset();
      mostrarMensaje('confirm', 'El plano se guardó correctamente. Estará disponible en la cola de revisión en breve.');
      renderRecientes();
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      mostrarMensaje('error', 'Error al cargar: ' + e.message);
    }
  }

  async function renderRecientes() {
    var cont = document.getElementById('cargar-recientes');
    try {
      var pendientes = await API.getAll('pendiente');
      
      // En API, estado "pendiente" significa que ya se subió y (si aplica) se procesó.
      // Pero si quisiéramos mostrar los que están "procesando" la IA,
      // la API no filtra por ia_estado con query param "estado". 
      // Por ahora traemos todo y filtramos localmente los pendientes + ia procesando.
      var todos = await API.getAll();
      var recientes = todos.filter(d => d.estado === 'pendiente' || d.ia_estado === 'procesando');

      if (recientes.length === 0) {
        cont.innerHTML = '<div class="empty">Todavía no hay planos en la cola de análisis.</div>';
        return;
      }
      cont.innerHTML = '<div class="list">' + recientes.map(function(d) {
        var estadoHTML = d.ia_estado === 'procesando'
          ? '<span class="pulse"></span><span class="badge pendiente">Analizando…</span>'
          : respuestaInvalida(d)
            ? '<span class="badge ia-error">Respuesta IA inválida (no JSON)</span>'
            : d.ia_estado === 'error'
              ? '<span class="badge ia-error">Error de IA</span>'
          : '<span class="badge pendiente">Pendiente de revisión</span>';
        var hwClass = (d.tipo_gpu || (d.usado_gpu ? 'gpu' : 'cpu')).toLowerCase();
        var hwLabel = d.tipo_gpu || (d.usado_gpu ? 'GPU' : 'CPU');
        var hwHTML = '<span class="badge-hw ' + hwClass + '">' + esc(hwLabel) + '</span>';
        return '<div class="row" style="cursor:default">' +
          '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
          '<div class="s">' + esc(d.nombre_original) + ' · ' + estadoHTML + hwHTML + '</div>' +
          '</div>';
      }).join('') + '</div>';
    } catch (e) {
      cont.innerHTML = '<div class="error">Error al cargar recientes: ' + e.message + '</div>';
    }
  }

  window.PH = window.PH || {};
  window.PH.CUCargar = { inicializar: inicializar, renderRecientes: renderRecientes };

})(window);
