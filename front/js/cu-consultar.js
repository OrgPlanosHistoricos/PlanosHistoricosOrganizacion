/**
 * cu-consultar.js - CU4: Consultar planos históricos.
 */
(function(window) {
  'use strict';

  var API = window.PH.API;
  var seleccionadoId = null;

  function esc(s) {
    return (s === undefined || s === null || s === '') ? 's/d' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function tituloDoc(d) {
    return window.PH.Nomenclatura.titulo(d);
  }

  var ultimaBusqueda = null;
  function inicializar() {
    document.getElementById('consultar-nomenclatura').innerHTML = window.PH.Nomenclatura.formulario('c-');
    document.getElementById('form-consultar').addEventListener('submit', function(ev) {
      ev.preventDefault();
      buscar();
    });
  }
  function buscar() {
    try { renderLista(window.PH.Nomenclatura.clave(window.PH.Nomenclatura.leer('c-'))); }
    catch (e) {
      document.getElementById('consultar-lista').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }
  async function renderLista(query) {
    var cont = document.getElementById('consultar-lista');
    if (!query) {
      cont.innerHTML = '<div class="empty">Completá los cuatro datos de nomenclatura para buscar un plano.</div>';
      return;
    }
    ultimaBusqueda = query;
    try {
      // La API busca una coincidencia exacta de los cuatro componentes.
      var resultados = await API.getAll(null, query);
      // We only want to show validados/sin_ubicacion in catalog search
      resultados = resultados.filter(d => d.estado === 'validado' || d.estado === 'sin_ubicacion');

      if (resultados.length === 0) {
        cont.innerHTML = '<div class="empty">No se encontró un plano catalogado con esa nomenclatura. Revisá los cuatro datos; si recién lo cargaste, todavía puede estar pendiente de revisión.</div>';
        seleccionadoId = null;
        document.getElementById('consultar-detalle').innerHTML = '<div class="empty">Los resultados de su búsqueda aparecerán acá.</div>';
        return;
      }
      
      cont.innerHTML = resultados.map(function(d) {
        var sel = d.id === seleccionadoId ? ' sel' : '';
        var badge = d.estado === 'sin_ubicacion'
          ? '<span class="badge sin_ubicacion">Sin ubicación</span>'
          : '<span class="badge validado">Validado</span>';
        return '<button class="row' + sel + '" onclick="PH.CUConsultar.seleccionar(' + d.id + ')">' +
          '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
          '<div class="s">' + badge + '</div>' +
          '</button>';
      }).join('');
    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  async function seleccionar(id) {
    seleccionadoId = id;
    var cont = document.getElementById('consultar-detalle');
    
    try {
      var d = await API.getById(id);

      var historialHTML = d.historial && d.historial.length
        ? '<div class="hist"><h3>Historial</h3><ul>' +
          d.historial.slice().reverse().map(function(h) {
            var date = new Date(h.fecha).toLocaleString('es-AR');
            return '<li><strong>' + esc(date) + '</strong> — ' + esc(h.motivo) + '</li>';
          }).join('') + '</ul></div>'
        : '';

      var esPdf = d.content_type === 'application/pdf' || (d.nombre_original && d.nombre_original.toLowerCase().endsWith('.pdf'));
      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getPreviewUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
        + '<a class="doclink" href="' + API.getArchivoUrl(d.id) + '" download="' + esc(d.nombre_original) + '" target="_blank" rel="noopener">'
        + (esPdf ? '📄 Abrir / Descargar PDF original (' + esc(d.nombre_original) + ')' : '🖼️ Ver / Descargar archivo original') + '</a>'
        + '<div class="field"><label>Nomenclatura catastral</label><div>' + esc(window.PH.Nomenclatura.titulo(d)) + '</div></div>'
        + '<div class="field"><label>Título</label><div>' + esc(d.titulo) + '</div></div>'
        + '<div class="field"><label>Arquitecto</label><div>' + esc(d.arquitecto) + '</div></div>'
        + '<div class="field"><label>Ubicación (leída)</label><div>' + esc(d.ubicacion) + '</div></div>'
        + '<div class="field"><label>Año</label><div>' + esc(d.anio) + '</div></div>'
        + '<div class="field"><label>Escala</label><div>' + esc(d.escala) + '</div></div>'
        + '<div class="field"><label>Tipo de plano</label><div>' + esc(d.tipo_de_plano) + '</div></div>'
        + '<div class="field"><label>Material / Soporte</label><div>' + esc(d.material_soporte) + '</div></div>'
        + '<div class="field"><label>Texto extraído</label><div style="white-space: pre-wrap;">' + esc(d.texto_extraido) + '</div></div>'
        + '<div class="field"><label>Notas</label><div>' + esc(d.notas) + '</div></div>'
        + '<div class="field"><label>Expediente de origen</label><div>' + esc(d.expediente) + '</div></div>'
        + '<div class="field"><label>Ubicación física</label><div>' + esc(d.ubicacion_fisica) + '</div></div>'
        + historialHTML;

      renderLista(ultimaBusqueda); // To re-highlight selection
    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  window.PH = window.PH || {};
  window.PH.CUConsultar = { inicializar: inicializar, buscar: buscar, renderLista: renderLista, seleccionar: seleccionar };

})(window);

