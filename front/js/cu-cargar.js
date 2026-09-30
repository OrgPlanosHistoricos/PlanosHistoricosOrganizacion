/**
 * cu-cargar.js - CU1: Cargar plano histórico.
 * Actor: Operador. Valida el archivo, guarda los datos de origen (opcionales)
 * e inicia el análisis automático en background.
 */
(function(window) {
  'use strict';

  var State = window.PH.State;

  function esc(s) {
    return (s === undefined || s === null || s === '') ? '' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function tituloDoc(d) {
    return d.origen.direccion || d.origen.expediente || d.archivoNombre;
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

  function onSubmit() {
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

    var reader = new FileReader();
    reader.onload = function(e) { crearDoc(file.name, e.target.result); };
    reader.onerror = function() { mostrarMensaje('error', 'No se pudo leer el archivo. Probá nuevamente.'); };
    reader.readAsDataURL(file);
  }

  function crearDoc(nombre, dataUrl) {
    var doc = {
      id: State.nextId(),
      archivoNombre: nombre,
      archivoUrl: dataUrl,
      estado: 'procesando',
      origen: {
        ubicacion: document.getElementById('f-ubic').value.trim(),
        expediente: document.getElementById('f-exp').value.trim(),
        direccion: document.getElementById('f-dir').value.trim()
      },
      datos: { propietario: '', direccion: '', nomenclatura: '', fecha: '', sellos: '', superficie: '' },
      condicionLegal: '',
      ubicacionAsignada: null,
      direccionVinculada: '',
      historial: [],
      fechaCarga: new Date().toLocaleDateString('es-AR'),
      fechaCargaTs: Date.now()
    };
    State.add(doc);
    State.iniciarProcesamiento(doc);

    document.getElementById('form-cargar').reset();
    mostrarMensaje('confirm', 'El plano se guardó correctamente. En unos segundos va a estar disponible en la cola de revisión.');
    renderRecientes();
    if (window.PH.actualizarListas) window.PH.actualizarListas();
  }

  function renderRecientes() {
    var cont = document.getElementById('cargar-recientes');
    var recientes = State.getAll().filter(function(d) { return d.estado === 'procesando' || d.estado === 'pendiente'; });

    if (recientes.length === 0) {
      cont.innerHTML = '<div class="empty">Todavía no hay planos en la cola de análisis.</div>';
      return;
    }
    cont.innerHTML = '<div class="list">' + recientes.map(function(d) {
      var estadoHTML = d.estado === 'procesando'
        ? '<span class="pulse"></span><span class="badge pendiente">Analizando…</span>'
        : '<span class="badge pendiente">Pendiente de revisión</span>';
      return '<div class="row" style="cursor:default">' +
        '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
        '<div class="s">' + esc(d.archivoNombre) + ' · ' + estadoHTML + '</div>' +
        '</div>';
    }).join('') + '</div>';
  }

  window.PH = window.PH || {};
  window.PH.CUCargar = { inicializar: inicializar, renderRecientes: renderRecientes };

})(window);
