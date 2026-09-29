/**
 * cu-cargar.js - Caso de Uso 01: Cargar plano histórico y procesar con IA
 */
(function(window) {
  'use strict';

  var State = window.PH.State;

  function mostrarMensajeCarga(tipo, html) {
    var el = document.getElementById('cargar-msgs');
    if (el) el.innerHTML = tipo ? '<div class="' + tipo + '">' + html + '</div>' : '';
  }

  function inicializarFormularioCarga() {
    var form = document.getElementById('form-cargar');
    if (!form) return;

    form.addEventListener('submit', function(e) {
      e.preventDefault();
      mostrarMensajeCarga('', '');

      var fileInput = document.getElementById('f-archivo');
      var file = fileInput.files[0];
      if (!file) {
        mostrarMensajeCarga('error', 'El archivo del plano es indispensable para continuar.');
        return;
      }

      var validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/tiff', 'application/pdf'];
      if (validTypes.indexOf(file.type) === -1) {
        mostrarMensajeCarga('error', 'El formato no es válido o el archivo está dañado. Use JPG, PNG, WEBP o PDF.');
        return;
      }

      var reader = new FileReader();
      reader.onload = function() {
        var esAnalizable = State.FORMATOS_API.indexOf(file.type) !== -1;
        var p = {
          id: State.nid(),
          archNombre: file.name,
          archTipo: file.type,
          archData: reader.result,
          ubic: document.getElementById('f-ubic').value.trim(),
          exp: document.getElementById('f-exp').value.trim(),
          dirOrig: document.getElementById('f-dir').value.trim(),
          estado: 'pendiente',
          iaEstado: esAnalizable ? 'procesando' : 'no_aplica',
          iaError: null,
          tareaId: null,
          auto: null,
          parcela: '',
          historial: []
        };

        var planos = State.getPlanos();
        planos.unshift(p);
        State.save();

        var sinDatos = !p.ubic && !p.exp && !p.dirOrig;
        form.reset();
        renderRecientes();

        if (esAnalizable) {
          mostrarMensajeCarga(
            'confirm',
            '<span class="pulse"></span> <strong>Plano guardado (' + p.id + ').</strong> Enviando a la IA en segundo plano… Podés continuar cargando otros planos o cambiar de pestaña libremente.' +
            (sinDatos ? ' <span class="optional">(Sin datos de origen adicionales).</span>' : '')
          );
          analizarPlano(p, file);
        } else {
          mostrarMensajeCarga(
            'confirm',
            '<strong>Plano guardado (' + p.id + ').</strong> El archivo PDF quedó listo para revisión manual en "Validar y catalogar".'
          );
        }

        if (window.PH && typeof window.PH.actualizarListas === 'function') {
          window.PH.actualizarListas();
        }
      };
      reader.readAsDataURL(file);
    });
  }

  function analizarPlano(p, file) {
    var formData = new FormData();
    formData.append('archivo', file);

    // La petición es asíncrona: responde de inmediato con HTTP 202 y el ID de tarea
    fetch(State.API_BASE + '/procesar-plano', { method: 'POST', body: formData })
      .then(function(res) {
        if (res.ok) return res.json();
        return res.json().catch(function() { return {}; }).then(function(err) {
          throw new Error(err.detail || ('La API respondió con error ' + res.status));
        });
      })
      .then(function(datos) {
        var actual = State.byId(p.id) || p;
        actual.tareaId = datos.task_id;
        actual.iaEstado = 'procesando';
        State.save();
        renderRecientes();

        if (window.PH && typeof window.PH.actualizarListas === 'function') {
          window.PH.actualizarListas();
        }

        State.iniciarPollingTarea(actual.id, datos.task_id);
      })
      .catch(function(err) {
        var actual = State.byId(p.id) || p;
        actual.iaEstado = 'error';
        actual.iaError = err.message;
        State.save();
        mostrarMensajeCarga(
          'hint',
          'Plano ' + actual.id + ' guardado, pero no se pudo iniciar el análisis automático (' + State.esc(err.message) + '). Podés completarlo a mano en "Validar y catalogar".'
        );
        renderRecientes();

        if (window.PH && typeof window.PH.actualizarListas === 'function') {
          window.PH.actualizarListas();
        }
      });
  }

  function renderRecientes() {
    var cont = document.getElementById('cargar-recientes');
    if (!cont) return;

    var recientes = State.getPlanos().slice(0, 4);
    if (!recientes.length) {
      cont.innerHTML = '';
      return;
    }

    var html = '<h3 style="font-size:13px;color:var(--ink-soft);font-weight:600;margin:0 0 10px">Cargas recientes</h3><div class="list">';
    recientes.forEach(function(p) {
      html += '<div class="row" style="cursor:default">' +
        '<div class="t">' + State.esc(p.archNombre) + ' ' + State.badge(p.estado) + State.iaBadge(p) + '</div>' +
        '<div class="s">' + (p.exp ? State.esc(p.exp) : 'Sin expediente') + ' · ' + p.id + '</div>' +
        '</div>';
    });
    html += '</div>';
    cont.innerHTML = html;
  }

  window.PH = window.PH || {};
  window.PH.CUCargar = {
    inicializar: inicializarFormularioCarga,
    renderRecientes: renderRecientes,
    analizarPlano: analizarPlano,
    mostrarMensajeCarga: mostrarMensajeCarga
  };

})(window);
