/**
 * cu-consultar.js - CU4: Consultar planos históricos.
 * Actor: Usuario / Consultor. Busca por calle, expediente, propietario o
 * parcela y visualiza la ficha completa del plano encontrado.
 */
(function(window) {
  'use strict';

  var State = window.PH.State;
  var seleccionadoId = null;

  function esc(s) {
    return (s === undefined || s === null || s === '') ? 's/d' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function tituloDoc(d) {
    return d.origen.direccion || d.origen.expediente || d.archivoNombre;
  }

  function inicializar() {
    document.getElementById('c-buscar').addEventListener('click', function() {
      renderLista(document.getElementById('c-query').value.trim());
    });
    document.getElementById('c-query').addEventListener('keydown', function(ev) {
      if (ev.key === 'Enter') renderLista(this.value.trim());
    });
  }

  function renderLista(query) {
    var cont = document.getElementById('consultar-lista');
    var base = State.getAll().filter(function(d) { return d.estado === 'validado'; });
    var q = (query || '').toLowerCase();
    var resultados = !q ? base : base.filter(function(d) {
      var hay = [tituloDoc(d), d.origen.expediente, d.datos.propietario, d.datos.nomenclatura, d.direccionVinculada]
        .join(' ').toLowerCase();
      return hay.indexOf(q) !== -1;
    });

    if (resultados.length === 0) {
      cont.innerHTML = '<div class="empty">No se encontraron planos coincidentes. Redefina los términos de búsqueda.</div>';
      seleccionadoId = null;
      document.getElementById('consultar-detalle').innerHTML = '<div class="empty">Los resultados de su búsqueda aparecerán acá.</div>';
      return;
    }
    cont.innerHTML = resultados.map(function(d) {
      var sel = d.id === seleccionadoId ? ' sel' : '';
      var badge = d.ubicacionAsignada === false
        ? '<span class="badge sin_ubicacion">Sin ubicación</span>'
        : '<span class="badge validado">Validado</span>';
      return '<button class="row' + sel + '" onclick="PH.CUConsultar.seleccionar(\'' + d.id + '\')">' +
        '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
        '<div class="s">' + badge + '</div>' +
        '</button>';
    }).join('');
  }

  function seleccionar(id) {
    seleccionadoId = id;
    var d = State.getById(id);
    var cont = document.getElementById('consultar-detalle');
    if (!d) {
      cont.innerHTML = '<div class="empty">Los resultados de su búsqueda aparecerán acá.</div>';
      return;
    }

    var historialHTML = d.historial.length
      ? '<div class="hist"><h3>Historial</h3><ul>' +
        d.historial.slice().reverse().map(function(h) {
          return '<li><strong>' + esc(h.fecha) + '</strong> — ' + esc(h.motivo) + '</li>';
        }).join('') + '</ul></div>'
      : '';

    cont.innerHTML = ''
      + '<img class="thumb" src="' + d.archivoUrl + '" alt="Plano ' + esc(d.id) + '">'
      + '<a class="doclink" href="' + d.archivoUrl + '" download="' + esc(d.archivoNombre) + '" target="_blank" rel="noopener">Ver / descargar archivo original</a>'
      + '<div class="field"><label>Dirección / Parcela</label><div>' + (d.ubicacionAsignada === false ? 'Sin ubicación asignada' : esc(d.direccionVinculada)) + '</div></div>'
      + '<div class="field"><label>Propietario</label><div>' + esc(d.datos.propietario) + '</div></div>'
      + '<div class="field"><label>Nomenclatura catastral</label><div>' + esc(d.datos.nomenclatura) + '</div></div>'
      + '<div class="field"><label>Fecha</label><div>' + esc(d.datos.fecha) + '</div></div>'
      + '<div class="field"><label>Sellos</label><div>' + esc(d.datos.sellos) + '</div></div>'
      + '<div class="field"><label>Superficie</label><div>' + esc(d.datos.superficie) + '</div></div>'
      + '<div class="field"><label>Condición legal</label><div>' + esc(d.condicionLegal) + '</div></div>'
      + '<div class="field"><label>Expediente de origen</label><div>' + esc(d.origen.expediente) + '</div></div>'
      + historialHTML;

    renderLista(document.getElementById('c-query').value.trim());
  }

  window.PH = window.PH || {};
  window.PH.CUConsultar = { inicializar: inicializar, renderLista: renderLista, seleccionar: seleccionar };

})(window);
