/**
 * state.js - Capa de acceso a datos conectada a la API FastAPI.
 * Reemplaza la antigua implementación de localStorage.
 */
(function(window) {
  'use strict';

  var API_BASE = '/api'; // El nginx del front proxy /api/ -> api:8000/

  async function fetchJSON(url, options) {
    var res = await fetch(API_BASE + url, options);
    if (!res.ok) {
        var err = await res.text();
        throw new Error(err || res.statusText);
    }
    return await res.json();
  }

  async function getAll(estado, query) {
    var params = new URLSearchParams();
    if (estado) params.append('estado', estado);
    if (query) params.append('q', query);
    var qs = params.toString();
    return await fetchJSON('/planos' + (qs ? '?' + qs : ''));
  }

  async function getById(id) {
    return await fetchJSON('/planos/' + id);
  }

  async function create(file, ubicacion_fisica, expediente, direccion_referencia) {
    var formData = new FormData();
    formData.append('archivo', file);
    formData.append('ubicacion_fisica', ubicacion_fisica || '');
    formData.append('expediente', expediente || '');
    formData.append('direccion_referencia', direccion_referencia || '');
    
    var res = await fetch(API_BASE + '/planos', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
  }

  async function validar(id, datos) {
    var res = await fetch(API_BASE + '/planos/' + id + '/validar', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos)
    });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
  }

  async function modificar(id, datos) {
    var res = await fetch(API_BASE + '/planos/' + id + '/modificar', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos)
    });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
  }

  async function eliminar(id) {
    var res = await fetch(API_BASE + '/planos/' + id, {
      method: 'DELETE'
    });
    if (!res.ok && res.status !== 204) throw new Error(await res.text());
    return true;
  }

  function getArchivoUrl(id) {
    return API_BASE + '/planos/' + id + '/archivo';
  }

  function renderPreviewHTML(d) {
    var url = getArchivoUrl(d.id);
    var isPdf = (d.content_type || '').toLowerCase().indexOf('pdf') !== -1 ||
                (d.nombre_original || '').toLowerCase().endsWith('.pdf');
    if (isPdf) {
      return '<div class="pdf-preview-box" style="margin-bottom:14px;padding:16px;background:#f8f7f2;border:1px solid var(--border);border-radius:4px;text-align:center;">'
        + '<div style="font-size:32px;margin-bottom:6px">📄</div>'
        + '<strong>Documento PDF:</strong> ' + (d.nombre_original || 'Plano') + '<br>'
        + '<a class="doclink" style="margin-top:10px" href="' + url + '" target="_blank" rel="noopener">Abrir / Ver PDF en nueva pestaña ↗</a>'
        + '</div>';
    }
    return '<div class="img-preview-box" style="margin-bottom:14px;">'
      + '<a href="' + url + '" target="_blank" title="Haga clic para ver en tamaño completo" rel="noopener">'
      + '<img class="thumb" style="cursor:zoom-in" src="' + url + '" alt="Plano ' + d.id + '">'
      + '</a>'
      + '<a class="doclink" href="' + url + '" target="_blank" rel="noopener">🔍 Ver imagen en tamaño completo ↗</a>'
      + '</div>';
  }

  window.PH = window.PH || {};
  window.PH.API = {
    getAll: getAll,
    getById: getById,
    create: create,
    validar: validar,
    modificar: modificar,
    eliminar: eliminar,
    getArchivoUrl: getArchivoUrl,
    renderPreviewHTML: renderPreviewHTML
  };

})(window);

