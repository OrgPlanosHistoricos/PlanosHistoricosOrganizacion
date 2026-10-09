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

  function getArchivoUrl(id) {
    return API_BASE + '/planos/' + id + '/archivo';
  }

  function getPreviewUrl(id) {
    return API_BASE + '/planos/' + id + '/preview';
  }

  window.PH = window.PH || {};
  window.PH.API = {
    getAll: getAll,
    getById: getById,
    create: create,
    validar: validar,
    modificar: modificar,
    getArchivoUrl: getArchivoUrl,
    getPreviewUrl: getPreviewUrl
  };

})(window);

