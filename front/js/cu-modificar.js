/**
 * cu-modificar.js - Caso de Uso 03: Modificar catalogación y registro de auditoría
 */
(function(window) {
  'use strict';

  var State = window.PH.State;
  var selMod = null;
  var modBackup = null;

  function field(id, label, val) {
    return '<div class="field"><label>' + label + '</label><input type="text" id="' + id + '" value="' + State.esc(val) + '"></div>';
  }

  function renderModificarLista() {
    var cat = State.getPlanos().filter(function(p) {
      return p.estado === 'validado' || p.estado === 'sin_ubicacion';
    });

    var el = document.getElementById('modificar-lista');
    if (!el) return;

    if (!cat.length) {
      el.innerHTML = '<div class="empty">Todavía no hay planos catalogados.</div>';
      return;
    }

    el.innerHTML = cat.map(function(p) {
      return '<button class="row' + (p.id === selMod ? ' sel' : '') + '" onclick="PH.selModificar(\'' + p.id + '\')">' +
        '<div class="t">' + State.esc(p.dirOrig || p.archNombre) + ' ' + State.badge(p.estado) + '</div>' +
        '<div class="s">' + (p.exp || 'Sin expediente') + ' · ' + p.id + '</div></button>';
    }).join('');
  }

  function renderModificarDetalle() {
    var box = document.getElementById('modificar-detalle');
    if (!box) return;

    var p = State.byId(selMod);
    if (!p) {
      box.innerHTML = '<div class="empty">Elija un plano catalogado para modificarlo.</div>';
      return;
    }

    var a = p.auto || {
      arquitecto: '', anio: '', titulo: '', ubicacion: '',
      escala: '', tipo_de_plano: '', material_soporte: '', notas: ''
    };

    box.innerHTML = '<div class="card">' +
      '<div class="grid2">' +
        field('m-arquitecto', 'Arquitecto', a.arquitecto) + field('m-anio', 'Año', a.anio) +
        field('m-titulo', 'Título / obra', a.titulo) + field('m-escala', 'Escala', a.escala) +
        field('m-tipo', 'Tipo de plano', a.tipo_de_plano) + field('m-material', 'Material / soporte', a.material_soporte) +
      '</div>' + field('m-ubicacion', 'Ubicación mencionada en el plano', a.ubicacion) + field('m-notas', 'Notas', a.notas) +
      field('m-parcela', 'Dirección / parcela', p.parcela) +
      '<div class="field"><label>Motivo del cambio <span class="optional">(obligatorio para guardar)</span></label><input type="text" id="m-motivo" placeholder="Ej: corrección de superficie tras nueva lectura"></div>' +
      '<div id="modificar-msgs"></div>' +
      '<div class="det-actions"><button class="primary" onclick="PH.guardarModificacion()">Guardar cambios</button><button class="ghost" onclick="PH.cancelarModificacion()">Cancelar</button></div>' +
      (p.historial.length ?
        '<div class="hist"><h3>Historial de modificaciones</h3><ul>' +
        p.historial.slice().reverse().map(function(h) {
          return '<li>' + State.esc(h.fecha) + ' — ' + State.esc(h.motivo) + '</li>';
        }).join('') + '</ul></div>' : '') +
    '</div>';

    modBackup = JSON.parse(JSON.stringify(p));
  }

  function guardarModificacion() {
    var p = State.byId(selMod);
    if (!p) return;

    var motivo = State.val('m-motivo').trim();
    var msg = document.getElementById('modificar-msgs');
    if (!motivo) {
      if (msg) msg.innerHTML = '<div class="error">Ingrese una breve aclaración sobre por qué se modifica el plano.</div>';
      return;
    }

    p.auto = {
      arquitecto: State.val('m-arquitecto'),
      anio: State.val('m-anio'),
      titulo: State.val('m-titulo'),
      ubicacion: State.val('m-ubicacion'),
      escala: State.val('m-escala'),
      tipo_de_plano: State.val('m-tipo'),
      material_soporte: State.val('m-material'),
      notas: State.val('m-notas')
    };

    p.parcela = State.val('m-parcela').trim();
    p.estado = p.parcela ? 'validado' : 'sin_ubicacion';
    p.historial.push({ fecha: State.today(), motivo: motivo });
    State.save();

    if (msg) msg.innerHTML = '<div class="confirm">Los datos del plano quedaron actualizados.</div>';
    renderModificarLista();

    setTimeout(function() {
      renderModificarDetalle();
      if (window.PH && typeof window.PH.actualizarListas === 'function') {
        window.PH.actualizarListas();
      }
    }, 600);
  }

  function cancelarModificacion() {
    if (modBackup) {
      var planos = State.getPlanos();
      var i = planos.findIndex(function(p) { return p.id === modBackup.id; });
      if (i > -1) planos[i] = modBackup;
    }
    renderModificarDetalle();
  }

  function seleccionar(id) {
    selMod = id;
    renderModificarLista();
    renderModificarDetalle();
  }

  window.PH = window.PH || {};
  window.PH.CUModificar = {
    renderLista: renderModificarLista,
    renderDetalle: renderModificarDetalle,
    guardarModificacion: guardarModificacion,
    cancelarModificacion: cancelarModificacion,
    seleccionar: seleccionar
  };

  // Acceso directo para handlers en DOM
  window.PH.selModificar = seleccionar;
  window.PH.guardarModificacion = guardarModificacion;
  window.PH.cancelarModificacion = cancelarModificacion;

})(window);
