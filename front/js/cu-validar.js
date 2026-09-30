/**
 * cu-validar.js - Caso de Uso 02: Validar y catalogar planos pendientes
 */
(function(window) {
  'use strict';

  var State = window.PH.State;
  var selValidar = null;

  function field(id, label, val) {
    return '<div class="field"><label>' + label + '</label><input type="text" id="' + id + '" value="' + State.esc(val) + '"></div>';
  }

  function renderValidarLista() {
    var pend = State.getPlanos().filter(function(p) { return p.estado === 'pendiente'; });
    var el = document.getElementById('validar-lista');
    if (!el) return;

    if (!pend.length) {
      el.innerHTML = '<div class="empty">No hay planos pendientes de revisión.</div>';
      return;
    }

    el.innerHTML = pend.map(function(p) {
      return '<button class="row' + (p.id === selValidar ? ' sel' : '') + '" onclick="PH.selValidar(\'' + p.id + '\')">' +
        '<div class="t">' + State.esc(p.archNombre) + State.iaBadge(p) + '</div>' +
        '<div class="s">' + (p.exp || 'Sin expediente') + ' · ' + p.id + '</div></button>';
    }).join('');
  }

  function renderValidarDetalle() {
    var box = document.getElementById('validar-detalle');
    if (!box) return;

    var p = State.byId(selValidar);
    if (!p) {
      box.innerHTML = '<div class="empty">Elija un plano pendiente de la lista para revisarlo.</div>';
      return;
    }

    var a = p.auto || {
      arquitecto: '', anio: '', titulo: '', ubicacion: '',
      escala: '', tipo_de_plano: '', material_soporte: '', notas: ''
    };

    var bannerHtml = '';
    if (p.iaEstado === 'procesando') {
      bannerHtml = '<div class="hint" style="display:flex;align-items:flex-start;gap:10px;margin-bottom:16px;">' +
        '<span class="pulse" style="margin-top:5px;flex:none;"></span>' +
        '<div><strong>La IA está analizando este plano en segundo plano…</strong>' +
        '<div style="font-size:12.5px;color:var(--ink-soft);margin-top:3px;">' +
        'El modelo de visión está procesando la imagen. Podés esperar acá, cambiar de pestaña o ir completando los datos manualmente. Los campos se completarán automáticamente en cuanto termine la lectura.' +
        '</div></div></div>';
    } else if (p.iaEstado === 'error') {
      bannerHtml = '<div class="error" style="margin-bottom:16px;">' +
        '<strong>La lectura automática no pudo completarse:</strong> ' + State.esc(p.iaError || 'Error al procesar la imagen.') +
        '<div style="font-size:12.5px;margin-top:3px;">Podés completar los campos manualmente a partir de la imagen.</div></div>';
    } else if (p.iaEstado === 'completado') {
      bannerHtml = '<div class="confirm" style="margin-bottom:16px;font-size:13.5px;">' +
        '✓ <strong>Lectura de IA completada:</strong> Revisá los datos detectados antes de confirmar la catalogación.</div>';
    } else if (p.archTipo === 'application/pdf' && p.iaEstado === 'no_aplica') {
      bannerHtml = '<div class="hint" style="margin-bottom:16px;font-size:13.5px;">' +
        'Los archivos PDF sin análisis automático se catalogan manualmente. Abrí el archivo y completá los campos visibles.</div>';
    }

    box.innerHTML = '<div class="card">' +
      (p.archTipo === 'application/pdf' ?
        '<a class="doclink" href="' + p.archData + '" target="_blank">Abrir PDF: ' + State.esc(p.archNombre) + '</a>' :
        '<img class="thumb" src="' + p.archData + '" alt="Vista previa de ' + State.esc(p.archNombre) + '">') +
      bannerHtml +
      '<div class="grid2">' +
        field('v-arquitecto', 'Arquitecto', a.arquitecto) + field('v-anio', 'Año', a.anio) +
        field('v-titulo', 'Título / obra', a.titulo) + field('v-escala', 'Escala', a.escala) +
        field('v-tipo', 'Tipo de plano', a.tipo_de_plano) + field('v-material', 'Material / soporte', a.material_soporte) +
      '</div>' + field('v-ubicacion', 'Ubicación mencionada en el plano', a.ubicacion) + field('v-notas', 'Notas', a.notas) +
      '<div class="field"><label>Dirección o parcela vinculada <span class="optional">(si no se encuentra, se guarda como "sin ubicación asignada")</span></label><input type="text" id="v-parcela" value="' + State.esc(p.parcela) + '" placeholder="Calle y número — Lote, Manzana"></div>' +
      '<div id="validar-msgs"></div>' +
      '<div class="actions"><button class="primary" onclick="PH.confirmarValidacion()">Confirmar catalogación</button></div>' +
    '</div>';
  }

  function confirmarValidacion() {
    var p = State.byId(selValidar);
    if (!p) return;

    p.auto = {
      arquitecto: State.val('v-arquitecto'),
      anio: State.val('v-anio'),
      titulo: State.val('v-titulo'),
      ubicacion: State.val('v-ubicacion'),
      escala: State.val('v-escala'),
      tipo_de_plano: State.val('v-tipo'),
      material_soporte: State.val('v-material'),
      notas: State.val('v-notas')
    };

    var parcela = State.val('v-parcela').trim();
    p.parcela = parcela;
    p.estado = parcela ? 'validado' : 'sin_ubicacion';
    if (p.iaEstado === 'procesando') p.iaEstado = 'completado';
    p.historial.push({ fecha: State.today(), motivo: 'Validación inicial' });
    State.save();

    var msg = document.getElementById('validar-msgs');
    if (msg) {
      msg.innerHTML = '<div class="confirm">Plano ' +
        (parcela ? 'validado y disponible para la búsqueda general.' : 'guardado como "sin ubicación asignada" y disponible para la búsqueda general.') +
        '</div>';
    }

    selValidar = null;
    setTimeout(function() {
      renderValidarLista();
      renderValidarDetalle();
      if (window.PH && typeof window.PH.actualizarListas === 'function') {
        window.PH.actualizarListas();
      }
    }, 700);
  }

  function seleccionar(id) {
    selValidar = id;
    renderValidarLista();
    renderValidarDetalle();
  }

  window.PH = window.PH || {};
  window.PH.CUValidar = {
    renderLista: renderValidarLista,
    renderDetalle: renderValidarDetalle,
    confirmarValidacion: confirmarValidacion,
    seleccionar: seleccionar,
    getSeleccionadoId: function() { return selValidar; }
  };

  // Acceso directo para handlers en DOM
  window.PH.selValidar = seleccionar;
  window.PH.confirmarValidacion = confirmarValidacion;

})(window);
