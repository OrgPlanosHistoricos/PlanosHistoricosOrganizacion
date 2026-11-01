/**
 * cu-consultar.js - CU4: Consultar planos históricos.
 */
(function(window) {
  'use strict';

  var API = window.PH.API;
  var seleccionadoId = null;

  function esc(s) {
    return (s === undefined || s === null || s === '') ? '-' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function tituloDoc(d) {
    return window.PH.Nomenclatura.titulo(d);
  }

  var camposCatastrales = ['circunscripcion', 'seccion', 'manzana', 'parcela_catastral'];
  var filtros = ['', '', '', ''];
  var catalogo = [];
  var resultados = [];
  var pagina = 1;
  var porPagina = 5;
  var solicitud = 0;

  function normalizarFiltro(valor, indice) {
    var texto = String(valor || '').trim().toUpperCase().replace(/\s+/g, '');
    return indice === 1 ? texto : texto.replace(/^0+(?=[0-9])/, '');
  }

  function inicializar() {
    document.getElementById('consultar-nomenclatura').innerHTML = window.PH.Nomenclatura.formulario('c-');
    document.getElementById('form-consultar').addEventListener('input', buscar);
    document.getElementById('form-consultar').addEventListener('submit', function(ev) {
      ev.preventDefault();
      buscar();
    });
  }

  function limpiarDetalle() {
    seleccionadoId = null;
    document.getElementById('consultar-detalle').innerHTML = '<div class="empty">Seleccione un plano de la lista para ver sus datos.</div>';
  }

  function buscar() {
    filtros = camposCatastrales.map(function(c, i) {
      return normalizarFiltro(document.getElementById('c-' + c).value, i);
    });
    pagina = 1;
    limpiarDetalle();
    filtrar();
  }

  function filtrar() {
    resultados = catalogo.filter(function(d) {
      return filtros.every(function(filtro, i) {
        return !filtro || normalizarFiltro(d[camposCatastrales[i]], i).startsWith(filtro);
      });
    });
    pagina = Math.min(pagina, Math.max(1, Math.ceil(resultados.length / porPagina)));
    dibujarLista();
  }

  function dibujarLista() {
    var cont = document.getElementById('consultar-lista');
    var paginador = document.getElementById('consultar-paginacion');
    if (!resultados.length) {
      cont.innerHTML = '<div class="empty">' + (filtros.some(Boolean)
        ? 'No se encontraron planos catalogados con esos datos catastrales.'
        : 'Todavía no hay planos catalogados.') + '</div>';
      paginador.innerHTML = '';
      limpiarDetalle();
      return;
    }
    var inicio = (pagina - 1) * porPagina;
    cont.innerHTML = resultados.slice(inicio, inicio + porPagina).map(function(d) {
      var sel = d.id === seleccionadoId ? ' sel' : '';
      var badge = d.estado === 'sin_ubicacion'
        ? '<span class="badge sin_ubicacion">Sin parcela asignada</span>'
        : '<span class="badge validado">Validado</span>';
      return '<button class="row' + sel + '" onclick="PH.CUConsultar.seleccionar(' + d.id + ')">' +
        '<div class="t">' + esc(tituloDoc(d)) + '</div><div class="s">' + badge + '</div></button>';
    }).join('');
    var paginas = Math.ceil(resultados.length / porPagina);
    paginador.innerHTML = '<p role="status" aria-live="polite">' + (inicio + 1) + '–' + Math.min(inicio + porPagina, resultados.length) +
      ' de ' + resultados.length + ' planos · Página ' + pagina + ' de ' + paginas + '</p>' +
      '<div class="pagination-actions"><button type="button" class="ghost"' + (pagina === 1 ? ' disabled' : '') +
      ' onclick="PH.CUConsultar.cambiarPagina(-1)">Anterior</button>' +
      '<button type="button" class="ghost"' + (pagina === paginas ? ' disabled' : '') +
      ' onclick="PH.CUConsultar.cambiarPagina(1)">Siguiente</button></div>';
  }

  function cambiarPagina(delta) {
    pagina = Math.max(1, Math.min(pagina + delta, Math.ceil(resultados.length / porPagina) || 1));
    limpiarDetalle();
    dibujarLista();
  }

  async function renderLista() {
    var actual = ++solicitud;
    try {
      var datos = await API.getAll();
      if (actual !== solicitud) return;
      catalogo = datos.filter(function(d) { return d.estado === 'validado' || d.estado === 'sin_ubicacion'; });
      if (seleccionadoId !== null && !catalogo.some(function(d) { return d.id === seleccionadoId; })) limpiarDetalle();
      filtrar();
    } catch (e) {
      if (actual !== solicitud) return;
      catalogo = [];
      resultados = [];
      limpiarDetalle();
      document.getElementById('consultar-paginacion').innerHTML = '';
      document.getElementById('consultar-lista').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  async function seleccionar(id) {
    seleccionadoId = id;
    var cont = document.getElementById('consultar-detalle');
    
    try {
      var d = await API.getById(id);
      if (seleccionadoId !== id) return;

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
        + '<div class="field"><label>Ubicación (extraída)</label><div>' + esc(d.ubicacion) + '</div></div>'
        + '<div class="field"><label>Año</label><div>' + esc(d.anio) + '</div></div>'
        + '<div class="field"><label>Escala</label><div>' + esc(d.escala) + '</div></div>'
        + '<div class="field"><label>Tipo de plano</label><div>' + esc(d.tipo_de_plano) + '</div></div>'
        + '<div class="field"><label>Material / Soporte</label><div>' + esc(d.material_soporte) + '</div></div>'
        + '<div class="field"><label>Texto extraído</label><div style="white-space: pre-wrap;">' + esc(d.texto_extraido) + '</div></div>'
        + '<div class="field"><label>Notas</label><div>' + esc(d.notas) + '</div></div>'
        + '<div class="field"><label>Expediente de origen</label><div>' + esc(d.expediente) + '</div></div>'
        + '<div class="field"><label>Ubicación física</label><div>' + esc(d.ubicacion_fisica) + '</div></div>'
        + historialHTML;

      dibujarLista();
    } catch (e) {
      if (seleccionadoId !== id) return;
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  window.PH = window.PH || {};
  window.PH.CUConsultar = { inicializar: inicializar, buscar: buscar, renderLista: renderLista, seleccionar: seleccionar, cambiarPagina: cambiarPagina };

})(window);

