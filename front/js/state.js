/**
 * state.js - Capa de datos de la aplicación.
 * Mantiene los documentos en memoria, los persiste en localStorage y simula
 * el procesamiento en background (IDP/IA) que completa los metadatos de un
 * plano recién cargado. En una versión con backend real, iniciarProcesamiento()
 * dispararía una llamada a /api/ (ver nginx.conf) en vez de un setTimeout.
 */
(function(window) {
  'use strict';

  var STORAGE_KEY = 'ph_planos_v1';
  var docs = [];
  var seq = 0;

  function nextId() {
    seq++;
    return 'PL-' + String(seq).padStart(3, '0');
  }

  function placeholderSVG() {
    return 'data:image/svg+xml;utf8,' + encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 75">' +
      '<rect width="100" height="75" fill="#E3DFCF"/>' +
      '<path d="M22 55 L40 30 L52 42 L78 18" stroke="#8F3A2C" stroke-width="2.2" fill="none"/>' +
      '<circle cx="22" cy="55" r="2.6" fill="#8F3A2C"/>' +
      '</svg>'
    );
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ seq: seq, docs: docs }));
      return true;
    } catch (e) {
      console.warn('No se pudo guardar en localStorage:', e);
      return false;
    }
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      var parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.docs)) return false;
      docs = parsed.docs;
      seq = parsed.seq || docs.length;
      return true;
    } catch (e) {
      console.warn('No se pudo leer localStorage:', e);
      return false;
    }
  }

  function seed() {
    seq = 5;
    docs = [
      {
        id: 'PL-001', archivoNombre: 'plano_barletta.jpg', archivoUrl: placeholderSVG(),
        estado: 'pendiente',
        origen: { ubicacion: 'Caja 12, Estantería B', expediente: 'Expte. 884-1987', direccion: 'Calle 47 N.º 1023' },
        datos: { propietario: 'A. Barletta', direccion: 'Calle 47 N.º 1023', nomenclatura: 'Circ. II · Secc. C · Mz. 14 · Parc. 8', fecha: '14/03/1987', sellos: 'Municipalidad — visado 1987', superficie: '186,40 m²' },
        condicionLegal: '', ubicacionAsignada: null, direccionVinculada: '', historial: [],
        fechaCarga: '02/09/2026', fechaCargaTs: Date.now() - 6e8
      },
      {
        id: 'PL-002', archivoNombre: 'plano_mitre.jpg', archivoUrl: placeholderSVG(),
        estado: 'validado',
        origen: { ubicacion: 'Caja 4, Estantería A', expediente: 'Expte. 227-2005', direccion: 'Av. Mitre 452' },
        datos: { propietario: 'Comercial Mitre S.R.L.', direccion: 'Av. Mitre 452', nomenclatura: 'Circ. I · Secc. A · Mz. 22 · Parc. 3', fecha: '22/08/2005', sellos: 'Municipalidad — aprobado 2005', superficie: '310,00 m²' },
        condicionLegal: 'Aprobado', ubicacionAsignada: true, direccionVinculada: 'Av. Mitre 452',
        historial: [{ fecha: '18/08/2019 11:02', motivo: 'Catalogación inicial' }],
        fechaCarga: '18/08/2019', fechaCargaTs: Date.now() - 2e9
      },
      {
        id: 'PL-003', archivoNombre: 'plano_deteriorado.jpg', archivoUrl: placeholderSVG(),
        estado: 'pendiente',
        origen: { ubicacion: 'Depósito histórico', expediente: 'Expte. 1145 (parcial)', direccion: '' },
        datos: { propietario: '', direccion: '', nomenclatura: '', fecha: 's/d', sellos: '', superficie: 's/d' },
        condicionLegal: '', ubicacionAsignada: null, direccionVinculada: '', historial: [],
        fechaCarga: '20/07/2026', fechaCargaTs: Date.now() - 4e8
      },
      {
        id: 'PL-004', archivoNombre: 'plano_chacra44.jpg', archivoUrl: placeholderSVG(),
        estado: 'validado',
        origen: { ubicacion: 'Archivo histórico', expediente: 'Expte. 1968-004', direccion: '' },
        datos: { propietario: 'Ilegible', direccion: '', nomenclatura: 'Chacra 44 (nomenclatura histórica)', fecha: 's/d', sellos: 's/d', superficie: 's/d' },
        condicionLegal: 'Documento técnico no oficializado', ubicacionAsignada: false, direccionVinculada: '',
        historial: [{ fecha: '21/07/2026 15:40', motivo: 'Catalogación inicial — nomenclatura histórica sin equivalencia confirmada' }],
        fechaCarga: '21/07/2026', fechaCargaTs: Date.now() - 3e8
      },
      {
        id: 'PL-005', archivoNombre: 'plano_etchegaray.jpg', archivoUrl: placeholderSVG(),
        estado: 'procesando',
        origen: { ubicacion: 'Caja 7, Estantería A', expediente: 'Expte. 340-2011', direccion: 'Etchegaray 233' },
        datos: { propietario: '', direccion: '', nomenclatura: '', fecha: '', sellos: '', superficie: '' },
        condicionLegal: '', ubicacionAsignada: null, direccionVinculada: '', historial: [],
        fechaCarga: new Date().toLocaleDateString('es-AR'), fechaCargaTs: Date.now()
      }
    ];
  }

  function getAll() {
    return docs.slice().sort(function(a, b) { return (b.fechaCargaTs || 0) - (a.fechaCargaTs || 0); });
  }

  function getById(id) {
    for (var i = 0; i < docs.length; i++) if (docs[i].id === id) return docs[i];
    return null;
  }

  function add(doc) {
    docs.unshift(doc);
    persist();
    return doc;
  }

  function update(id, patch) {
    var d = getById(id);
    if (!d) return null;
    Object.keys(patch).forEach(function(k) { d[k] = patch[k]; });
    persist();
    return d;
  }

  function iniciarProcesamiento(doc, delayMs) {
    delayMs = delayMs || 2200;
    setTimeout(function() {
      var d = getById(doc.id);
      if (!d || d.estado !== 'procesando') return;
      // Simula una lectura incompleta cuando el nombre del archivo sugiere deterioro,
      // igual que pasaría con un documento realmente ilegible.
      var deteriorado = /deterior/i.test(d.archivoNombre);
      d.estado = 'pendiente';
      d.datos = deteriorado
        ? { propietario: '', direccion: d.origen.direccion || '', nomenclatura: '', fecha: '', sellos: '', superficie: '' }
        : { propietario: 'A confirmar', direccion: d.origen.direccion || 'A confirmar', nomenclatura: 'A confirmar', fecha: 'A confirmar', sellos: 'A confirmar', superficie: 'A confirmar' };
      persist();
      if (window.PH && window.PH.onPlanoIAActualizado) window.PH.onPlanoIAActualizado(d);
    }, delayMs);
  }

  function reanudarTareasPendientes() {
    // Si la página se recargó con planos que habían quedado "procesando",
    // el setTimeout original se perdió: los reprogramamos con un delay corto.
    docs.forEach(function(d) {
      if (d.estado === 'procesando') iniciarProcesamiento(d, 1500);
    });
  }

  window.PH = window.PH || {};
  window.PH.State = {
    STORAGE_KEY: STORAGE_KEY,
    load: load,
    seed: seed,
    save: persist,
    getAll: getAll,
    getById: getById,
    add: add,
    update: update,
    nextId: nextId,
    placeholderSVG: placeholderSVG,
    iniciarProcesamiento: iniciarProcesamiento,
    reanudarTareasPendientes: reanudarTareasPendientes
  };

})(window);
