/**
 * state.js - Capa de acceso a datos conectada a la API FastAPI.
 * Reemplaza la antigua implementación de localStorage.
 */
(function(window) {
  'use strict';

  var API_BASE = '/api'; // El nginx del front proxy /api/ -> api:8000/

  var MENSAJES = {
    red: 'No pudimos conectarnos con el servidor. Revisá tu conexión e intentá nuevamente.',
    formato: 'No pudimos leer el archivo. Usá un JPG, PNG, WEBP o PDF válido y volvé a cargarlo.',
    tamano: 'El archivo supera el tamaño permitido para la carga (20 MB). Reducí su tamaño o elegí un archivo más pequeño e intentá nuevamente.',
    faltante: 'El plano solicitado ya no está disponible. Actualizá la lista y elegí otro plano.',
    datos: 'No pudimos guardar los datos. Revisá los campos del formulario e intentá nuevamente.',
    respuesta: 'No pudimos interpretar la respuesta del servidor. Intentá nuevamente en unos momentos.',
    servidor: 'El servicio no está disponible en este momento. Intentá nuevamente más tarde.',
    ia: 'El análisis automático no pudo completarse. Podés reintentarlo o completar los datos manualmente.',
    max_intentos: 'Se alcanzó el límite máximo de 3 intentos de análisis para este plano.',
    nomenclatura: 'Completá la nomenclatura: circunscripción con un número, sección con letras, y manzana y parcela con un número y letras opcionales. Los números deben ser mayores que cero.',
    duplicado: 'Ya existe un plano con esa nomenclatura. Revisá los cuatro datos o consultá el plano existente.',
    inesperado: 'No pudimos completar la operación. Intentá nuevamente; si el problema continúa, contactá al administrador.'
  };

  function errorSeguro(codigo) {
    var error = new Error(MENSAJES[codigo]);
    error.codigo = codigo;
    return error;
  }

  function mensajeError(error) {
    var codigo = error && error.codigo;
    return Object.prototype.hasOwnProperty.call(MENSAJES, codigo)
      ? MENSAJES[codigo] : MENSAJES.inesperado;
  }

  async function fetchJSON(url, options) {
    var res;
    try {
      res = await fetch(API_BASE + url, options);
    } catch (error) {
      throw errorSeguro('red');
    }
    if (!res.ok) {
      // Nunca usar el cuerpo de la respuesta ni statusText como texto de pantalla.
      var codigo = res.status === 413 ? 'tamano'
        : res.status === 404 ? (/^\/planos\/\d+(?:\/|\?|$)/.test(url) ? 'faltante' : 'servidor')
        : res.status === 405 ? 'servidor'
        : res.status >= 500 ? 'servidor'
        : res.status === 415 || (res.status === 400 && url === '/planos') ? 'formato'
        : url.indexOf('/reintentar_ia') !== -1 ? 'ia'
        : res.status === 400 || res.status === 422 ? 'datos' : 'inesperado';
      // Sólo se reconocen códigos acordados. Nunca se muestra texto recibido del servidor.
      if (res.status === 400 || res.status === 409 || res.status === 422) {
        try {
          var cuerpo = await res.json();
          var codigoAPI = cuerpo && cuerpo.detail && cuerpo.detail.codigo;
          if (codigoAPI === 'nomenclatura' || codigoAPI === 'duplicado' || codigoAPI === 'max_intentos') codigo = codigoAPI;
          else if (res.status === 422 && Array.isArray(cuerpo.detail) && cuerpo.detail.some(function(d) {
            return Array.isArray(d.loc) && ['circunscripcion', 'seccion', 'manzana', 'parcela_catastral'].indexOf(d.loc[d.loc.length - 1]) !== -1;
          })) codigo = 'nomenclatura';
        } catch (error) { /* Mantener el mensaje seguro por estado HTTP. */ }
      }
      throw errorSeguro(codigo);
    }
    try {
      return await res.json();
    } catch (error) {
      throw errorSeguro(error instanceof SyntaxError ? 'respuesta' : 'red');
    }
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

  async function eliminar(id) {
    return await fetchJSON('/planos/' + id, { method: 'DELETE' });
  }

  async function create(file, ubicacion_fisica, expediente, direccion_referencia, nomenclatura) {
    var formData = new FormData();
    formData.append('archivo', file);
    formData.append('ubicacion_fisica', ubicacion_fisica || '');
    formData.append('expediente', expediente || '');
    formData.append('direccion_referencia', direccion_referencia || '');
    formData.append('usuario_id', 'Operador'); // Hardcoded for now
    Object.keys(nomenclatura || {}).forEach(function(campo) { formData.append(campo, nomenclatura[campo]); });
    
    return await fetchJSON('/planos', {
      method: 'POST',
      body: formData
    });
  }

  async function validar(id, datos) {
    return await fetchJSON('/planos/' + id + '/validar', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos)
    });
  }

  async function modificar(id, datos) {
    return await fetchJSON('/planos/' + id + '/modificar', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos)
    });
  }

  async function reintentarIA(id, usuario_id) {
    var qs = '?usuario_id=' + encodeURIComponent(usuario_id || 'Validador');
    return await fetchJSON('/planos/' + id + '/reintentar_ia' + qs, {
      method: 'POST'
    });
  }

  async function descartarPropuesta(id) {
    return await fetchJSON('/planos/' + id + '/descartar_propuesta', {
      method: 'POST'
    });
  }

  function getArchivoUrl(id) {
    return API_BASE + '/planos/' + id + '/archivo';
  }

  function getPreviewUrl(id) {
    return API_BASE + '/planos/' + id + '/preview';
  }

  window.PH = window.PH || {};
  window.PH.Errores = { mensaje: mensajeError, mensajes: MENSAJES };
  window.PH.API = {
    getAll: getAll,
    getById: getById,
    eliminar: eliminar,
    create: create,
    validar: validar,
    modificar: modificar,
    reintentarIA: reintentarIA,
    descartarPropuesta: descartarPropuesta,
    getArchivoUrl: getArchivoUrl,
    getPreviewUrl: getPreviewUrl
  };

})(window);

