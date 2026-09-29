/**
 * cu-consultar.js - Caso de Uso 04: Búsqueda y consulta de planos históricos
 */
(function(window) {
  'use strict';

  var State = window.PH.State;

  function renderConsultarLista(q) {
    var disponibles = State.getPlanos().filter(function(p) {
      return p.estado !== 'pendiente';
    });

    var query = (q || '').trim().toLowerCase();
    var res = query ? disponibles.filter(function(p) {
      var hay = [
        p.dirOrig,
        p.parcela,
        p.exp,
        p.ubic,
        (p.auto && p.auto.anio) || '',
        (p.auto && p.auto.arquitecto) || '',
        (p.auto && p.auto.titulo) || '',
        (p.auto && p.auto.ubicacion) || ''
      ].join(' ').toLowerCase();
      return hay.indexOf(query) !== -1;
    }) : disponibles;

    var el = document.getElementById('consultar-lista');
    var det = document.getElementById('consultar-detalle');
    if (!el || !det) return;

    if (!res.length) {
      el.innerHTML = '<div class="empty">No se encontraron planos con esos datos.</div>';
      det.innerHTML = '<div class="empty">Cambie los términos de búsqueda e intente de nuevo.</div>';
      return;
    }

    el.innerHTML = res.map(function(p) {
      return '<button class="row" onclick="PH.verConsulta(\'' + p.id + '\')">' +
        '<div class="t">' + State.esc(p.dirOrig || p.parcela || p.archNombre) + ' ' + State.badge(p.estado) + '</div>' +
        '<div class="s">' + (p.exp || 'Sin expediente') + ' · ' + p.id + '</div></button>';
    }).join('');
  }

  function verConsulta(id) {
    var p = State.byId(id);
    if (!p) return;

    var a = p.auto || {};
    var det = document.getElementById('consultar-detalle');
    if (!det) return;

    det.innerHTML = '<div class="card">' +
      (p.archTipo === 'application/pdf' ?
        '<a class="doclink" href="' + p.archData + '" target="_blank">Abrir / descargar PDF: ' + State.esc(p.archNombre) + '</a>' :
        '<img class="thumb" src="' + p.archData + '" alt="Plano ' + State.esc(p.dirOrig) + '">' +
        '<a class="doclink" href="' + p.archData + '" download="' + State.esc(p.archNombre) + '">Descargar imagen</a>') +
      '<p><strong>Dirección / parcela:</strong> ' + State.esc(p.parcela || p.dirOrig || '—') + ' ' + State.badge(p.estado) + '</p>' +
      '<p><strong>Expediente:</strong> ' + State.esc(p.exp || '—') + ' &nbsp; <strong>Ubicación física:</strong> ' + State.esc(p.ubic || '—') + '</p>' +
      '<p><strong>Arquitecto:</strong> ' + State.esc(a.arquitecto || '—') + ' &nbsp; <strong>Año:</strong> ' + State.esc(a.anio || '—') + '</p>' +
      '<p><strong>Título / obra:</strong> ' + State.esc(a.titulo || '—') + ' &nbsp; <strong>Escala:</strong> ' + State.esc(a.escala || '—') + '</p>' +
      '<p><strong>Tipo de plano:</strong> ' + State.esc(a.tipo_de_plano || '—') + ' &nbsp; <strong>Material / soporte:</strong> ' + State.esc(a.material_soporte || '—') + '</p>' +
      (a.notas ? '<p><strong>Notas:</strong> ' + State.esc(a.notas) + '</p>' : '') +
      '</div>';
  }

  function inicializarBusqueda() {
    var btnBuscar = document.getElementById('c-buscar');
    var inputQuery = document.getElementById('c-query');

    if (btnBuscar) {
      btnBuscar.addEventListener('click', function() {
        renderConsultarLista(State.val('c-query'));
      });
    }

    if (inputQuery) {
      inputQuery.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          renderConsultarLista(State.val('c-query'));
        }
      });
      // Búsqueda en vivo reactiva opcional al tipear
      inputQuery.addEventListener('input', function() {
        renderConsultarLista(State.val('c-query'));
      });
    }
  }

  window.PH = window.PH || {};
  window.PH.CUConsultar = {
    inicializar: inicializarBusqueda,
    renderLista: renderConsultarLista,
    verConsulta: verConsulta
  };

  // Acceso directo para handlers en DOM
  window.PH.verConsulta = verConsulta;

})(window);
