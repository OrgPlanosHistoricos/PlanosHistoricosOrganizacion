/**
 * cu-validar.js - CU2: Validar y catalogar plano histórico (HITL).
 */
(function(window) {
  'use strict';

  var API = window.PH.API;
  var CAMPOS = [
    { key: 'texto_extraido', label: 'Texto extraído (solo lectura)', type: 'textarea', readonly: true },
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
  var modoCargaManual = false;

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
        var indicador = d.ia_estado === 'no_aplica'
          ? '<span class="badge ia-error">No aplica</span>'
          : respuestaInvalida(d)
            ? '<span class="badge ia-error">Respuesta incompleta</span>'
            : d.ia_estado === 'error'
              ? '<span class="badge ia-error">Error de análisis</span>'
              : '';
        return '<button class="row' + sel + '" onclick="PH.CUValidar.seleccionar(' + d.id + ')">' +
          '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
          '<div class="s">' + esc(d.nombre_original) + (indicador ? ' · ' + indicador : '') + '</div>' +
          '</button>';
      }).join('');
    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  function seleccionar(id) {
    seleccionadoId = id;
    modoCargaManual = false;
    renderDetalle();
    renderLista(); // Para actualizar selección visual
  }
  function getSeleccionadoId() { return seleccionadoId; }

  function cancelar() {
    seleccionadoId = null;
    modoCargaManual = false;
    renderDetalle();
    renderLista();
  }

  function cargarAMano() {
    modoCargaManual = true;
    var formCont = document.getElementById('v-form-container');
    if (formCont) formCont.style.display = 'block';
    var opcFalla = document.getElementById('v-opciones-falla');
    if (opcFalla) opcFalla.style.display = 'none';
    CAMPOS.forEach(function(c) {
      var el = document.getElementById('v-' + c.key);
      if (el && !c.readonly) {
        el.value = '';
      }
    });
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

      var tieneFalla = (d.ia_estado === 'error' || d.ia_estado === 'no_aplica');
      var maxIntentos = 3;
      var intentos = (d.procesamientos && d.procesamientos.length) ? d.procesamientos.length : (d.ia_estado === 'error' ? 1 : 0);
      var puedeReintentar = (d.ia_estado === 'error' && intentos < maxIntentos);

      var motivoFallaTexto = d.ia_estado === 'no_aplica'
        ? 'El análisis automático no aplica para este plano.'
        : respuestaInvalida(d)
          ? 'No pudimos interpretar los datos del plano.'
          : 'El análisis automático no pudo completarse.';

      var aviso = tieneFalla
        ? '<div class="error"><strong>' + esc(motivoFallaTexto) + '</strong> '
          + (d.ia_estado === 'no_aplica'
              ? 'Podés cargar los datos manualmente.'
              : puedeReintentar
                ? 'Podés reintentar el análisis o cargar los datos manualmente.'
                : 'Se alcanzó el límite máximo de ' + maxIntentos + ' intentos. Cargá los datos manualmente.')
          + '</div>'
        : '<div class="confirm">Datos leídos automáticamente. Revíselos y corríjalos si hace falta.</div>';

      var esPdf = d.content_type === 'application/pdf' || (d.nombre_original && d.nombre_original.toLowerCase().endsWith('.pdf'));
      var enlaceArchivo = '<div style="margin: 6px 0 12px 0;">'
        + '<a class="doclink" href="' + API.getArchivoUrl(d.id) + '" target="_blank" rel="noopener">'
        + (esPdf ? '📄 Abrir / Descargar PDF original (' + esc(d.nombre_original) + ')' : '🖼️ Ver / Descargar imagen original')
        + '</a></div>';

      var opcionesFallaHTML = '';
      if (tieneFalla) {
        var displayOpc = modoCargaManual ? 'none' : 'flex';
        opcionesFallaHTML = '<div id="v-opciones-falla" style="display:' + displayOpc + '; gap:8px; flex-wrap:wrap; margin:12px 0 16px 0;">'
          + (puedeReintentar ? '<button class="primary" onclick="PH.CUValidar.reintentar(' + d.id + ')">Reintentar análisis (' + intentos + '/' + maxIntentos + ')</button>' : '')
          + '<button class="' + (puedeReintentar ? 'ghost' : 'primary') + '" onclick="PH.CUValidar.cargarAMano()">Cargar datos a mano</button>'
          + '<button class="danger" onclick="PH.CUValidar.eliminar(this)">Eliminar plano</button>'
          + '</div>';
      }

      var displayForm = (!tieneFalla || modoCargaManual) ? 'block' : 'none';
      var formHTML = '<div id="v-form-container" style="display:' + displayForm + ';">'
        + (tieneFalla && modoCargaManual ? '<div class="confirm" style="margin-bottom:12px">Modo de carga manual: completá los datos leyendo la imagen.</div>' : '')
        + window.PH.Nomenclatura.formulario('v-', d)
        + CAMPOS.map(function(c) {
            var val = (tieneFalla && modoCargaManual) ? '' : (d[c.key] !== undefined && d[c.key] !== null ? d[c.key] : '');
            if (c.type === 'textarea') {
              return '<div class="field"><label for="v-' + c.key + '">' + c.label + '</label>' +
                '<textarea id="v-' + c.key + '" rows="4" readonly>' + esc(val) + '</textarea></div>';
            }
            var type = c.type === 'number' ? 'number' : 'text';
            return '<div class="field"><label>' + c.label + '</label>' +
              '<input type="' + type + '" id="v-' + c.key + '" value="' + attr(val) + '"></div>';
          }).join('')
        + '<div class="actions">'
        + '<button class="ghost" onclick="PH.CUValidar.cancelar()">Cancelar</button>'
        + '<button class="primary" onclick="PH.CUValidar.confirmar()">Confirmar e indexar</button>'
        + (!tieneFalla ? '<button class="danger" onclick="PH.CUValidar.eliminar(this)">Eliminar plano</button>' : '')
        + '</div>'
        + '</div>';

      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getPreviewUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
        + enlaceArchivo
        + aviso
        + opcionesFallaHTML
        + '<div id="v-msg"></div>'
        + formHTML;

    } catch (e) {
      cont.innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  async function confirmar() {
    if (!seleccionadoId) return;

    var nuevosDatos = {};
    CAMPOS.forEach(function(c) {
      if (c.readonly) return;
      var v = document.getElementById('v-' + c.key).value.trim();
      nuevosDatos[c.key] = v || null;
    });

    try { Object.assign(nuevosDatos, window.PH.Nomenclatura.leer('v-')); }
    catch (e) { document.getElementById('v-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>'; return; }
    nuevosDatos.usuario_id = "Validador"; // Hardcoded for now as there's no login

    try {
      await API.validar(seleccionadoId, nuevosDatos);
      seleccionadoId = null;
      modoCargaManual = false;
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
      modoCargaManual = false;
      await renderLista();
      var cont = document.getElementById('validar-detalle');
      if (cont) {
        cont.innerHTML = '<div class="confirm">Reanálisis iniciado. El plano volverá a aparecer en la lista cuando finalice el procesamiento.</div>';
      }
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('v-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    }
  }

  async function eliminar(boton) {
    if (!seleccionadoId || !window.confirm('¿Eliminar este plano, su archivo y su historial permanentemente?')) return;
    if (boton) boton.disabled = true;
    try {
      await API.eliminar(seleccionadoId);
      seleccionadoId = null;
      modoCargaManual = false;
      await renderLista();
      await renderDetalle();
      document.getElementById('validar-detalle').innerHTML = '<div class="confirm">El plano se eliminó correctamente.</div>';
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('v-msg').innerHTML = '<div class="error">' + window.PH.Errores.mensaje(e) + '</div>';
    } finally { if (boton) boton.disabled = false; }
  }

  window.PH = window.PH || {};
  window.PH.CUValidar = {
    renderLista: renderLista,
    renderDetalle: renderDetalle,
    seleccionar: seleccionar,
    getSeleccionadoId: getSeleccionadoId,
    cancelar: cancelar,
    confirmar: confirmar,
    reintentar: reintentar,
    cargarAMano: cargarAMano,
    eliminar: eliminar
  };

})(window);
