/**
 * cu-validar.js - CU2: Validar y catalogar plano histórico (HITL).
 */
(function(window) {
  'use strict';

  var API = window.PH.API;
  var CAMPOS = [
    { key: 'texto_extraido', label: 'Texto extraído', type: 'textarea' },
    { key: 'titulo', label: 'Título' },
    { key: 'arquitecto', label: 'Arquitecto' },
    { key: 'ubicacion', label: 'Ubicación' },
    { key: 'anio', label: 'Año', type: 'number' },
    { key: 'escala', label: 'Escala' },
    { key: 'tipo_de_plano', label: 'Tipo de Plano' },
    { key: 'material_soporte', label: 'Material' },
    { key: 'notas', label: 'Notas' }
  ];
  
  var seleccionadoId = null;

  function esc(s) {
    return (s === undefined || s === null || s === '') ? '' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function attr(s) { return String(s || '').replace(/"/g, '&quot;'); }
  function tituloDoc(d) {
    return window.PH.Nomenclatura.titulo(d);
  }
  function respuestaInvalida(d) {
    return d.ia_error && d.ia_error.indexOf('JSON válido') !== -1;
  }

  async function renderLista() {
    var cont = document.getElementById('validar-lista');
    try {
      var pendientes = await API.getAll('pendiente');
      // Asegurar que si está procesando la IA no se pueda validar aún
      pendientes = pendientes.filter(d => d.ia_estado !== 'procesando');

      if (pendientes.length === 0) {
        cont.innerHTML = '<div class="empty">No hay planos pendientes de revisión.</div>';
        return;
      }
      cont.innerHTML = pendientes.map(function(d) {
        var sel = d.id === seleccionadoId ? ' sel' : '';
        var indicador = respuestaInvalida(d)
          ? '<span class="badge ia-error">Análisis automático incompleto</span>'
          : d.ia_estado === 'error'
            ? '<span class="badge ia-error">No se pudo analizar el plano</span>'
            : '';
        return '<button class="row' + sel + '" onclick="PH.CUValidar.seleccionar(' + d.id + ')">' +
          '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
          '<div class="s">' + esc(d.nombre_original) + ' · ' + indicador + '</div>' +
          '</button>';
      }).join('');
    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  function seleccionar(id) {
    seleccionadoId = id;
    renderDetalle();
    renderLista(); // Para actualizar selección visual
  }
  function getSeleccionadoId() { return seleccionadoId; }

  function cancelar() {
    seleccionadoId = null;
    renderDetalle();
    renderLista();
  }


  async function renderDetalle() {
    var cont = document.getElementById('validar-detalle');
    
    if (!seleccionadoId) {
      cont.innerHTML = '<div class="empty">Elija un plano pendiente de la lista para revisarlo.</div>';
      return;
    }

    try {
      var d = await API.getById(seleccionadoId);
      if (d.estado !== 'pendiente') {
        seleccionadoId = null;
        cont.innerHTML = '<div class="empty">Elija un plano pendiente de la lista para revisarlo.</div>';
        return;
      }

      var maxIntentos = 3;
      var intentos = d.procesamientos ? d.procesamientos.length : 0;
      var btnReintentar = '';
      if (intentos < maxIntentos) {
          btnReintentar = '<br><button class="ghost" style="margin-top:8px" onclick="PH.CUValidar.reintentar(' + d.id + ')">Reintentar análisis IA (' + intentos + '/' + maxIntentos + ')</button>';
      } else {
          btnReintentar = '<br><span style="color:red; font-size: 0.9em; margin-top:8px; display:inline-block;">Se alcanzó el límite de reintentos (' + maxIntentos + '). Cargue a mano.</span>';
      }

      var aviso = respuestaInvalida(d)
        ? '<div class="error"><strong>La IA devolvió una respuesta inválida.</strong> No pudimos interpretar los datos del plano. Podés reintentar el análisis o completar los datos manualmente.' +
          btnReintentar + '</div>'
        : d.ia_estado === 'error'
          ? '<div class="error"><strong>La IA no pudo procesar este plano.</strong> Podés reintentar el análisis o completar los datos manualmente.' +
            btnReintentar + '</div>'
          : '<div class="confirm">Datos leídos automáticamente. Revíselos y corríjalos si hace falta.</div>';

      var esPdf = d.content_type === 'application/pdf' || (d.nombre_original && d.nombre_original.toLowerCase().endsWith('.pdf'));
      var enlaceArchivo = '<div style="margin: 6px 0 12px 0;">'
        + '<a class="doclink" href="' + API.getArchivoUrl(d.id) + '" target="_blank" rel="noopener">'
        + (esPdf ? '📄 Abrir / Descargar PDF original (' + esc(d.nombre_original) + ')' : '🖼️ Ver / Descargar imagen original')
        + '</a></div>';

      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getPreviewUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
        + enlaceArchivo
        + aviso
        + window.PH.Nomenclatura.formulario('v-', d)
        + CAMPOS.map(function(c) {
            var val = d[c.key] !== undefined && d[c.key] !== null ? d[c.key] : '';
            if (c.type === 'textarea') {
              return '<div class="field"><label>' + c.label + '</label>' +
                '<textarea id="v-' + c.key + '" rows="4">' + esc(val) + '</textarea></div>';
            }
            var type = c.type === 'number' ? 'number' : 'text';
            return '<div class="field"><label>' + c.label + '</label>' +
              '<input type="' + type + '" id="v-' + c.key + '" value="' + attr(val) + '"></div>';
          }).join('')
        + '<div id="v-msg"></div>'
        + '<div class="actions">' +
          '<button class="ghost" onclick="PH.CUValidar.cancelar()">Cancelar</button>' +
          '<button class="primary" onclick="PH.CUValidar.confirmar()">Confirmar e indexar</button>' +
          '</div>';

    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  async function confirmar() {
    if (!seleccionadoId) return;

    var nuevosDatos = {};
    CAMPOS.forEach(function(c) {
      var v = document.getElementById('v-' + c.key).value.trim();
      nuevosDatos[c.key] = v || null;
    });

    try { Object.assign(nuevosDatos, window.PH.Nomenclatura.leer('v-')); }
    catch (e) { document.getElementById('v-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>'; return; }
    nuevosDatos.usuario_id = "Validador"; // Hardcoded for now as there's no login

    try {
      await API.validar(seleccionadoId, nuevosDatos);
      seleccionadoId = null;
      renderLista();
      renderDetalle();
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('v-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  async function reintentar(id) {
    if (!id) return;
    try {
      await API.reintentarIA(id, "Validador");
      seleccionadoId = null;
      renderLista();
      renderDetalle();
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('v-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  window.PH = window.PH || {};
  window.PH.CUValidar = {
    renderLista: renderLista,
    renderDetalle: renderDetalle,
    seleccionar: seleccionar,
    getSeleccionadoId: getSeleccionadoId,
    cancelar: cancelar,
    confirmar: confirmar,
    reintentar: reintentar
  };

})(window);
