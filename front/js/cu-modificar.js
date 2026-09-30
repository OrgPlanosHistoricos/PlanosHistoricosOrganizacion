/**
<<<<<<< Updated upstream
 * cu-modificar.js - Caso de Uso 03: Modificar catalogación y registro de auditoría
=======
 * cu-modificar.js - CU3: Modificar catalogación de plano histórico.
>>>>>>> Stashed changes
 */
(function(window) {
  'use strict';

<<<<<<< Updated upstream
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
=======
  var API = window.PH.API;
  var seleccionadoId = null;

  var CAMPOS = [
    { key: 'titulo', label: 'Título' },
    { key: 'arquitecto', label: 'Arquitecto' },
    { key: 'ubicacion', label: 'Ubicación' },
    { key: 'anio', label: 'Año', type: 'number' },
    { key: 'escala', label: 'Escala' },
    { key: 'tipo_de_plano', label: 'Tipo de Plano' },
    { key: 'material_soporte', label: 'Material' },
    { key: 'notas', label: 'Notas' }
  ];

  function esc(s) {
    return (s === undefined || s === null || s === '') ? '' :
      String(s).replace(/[&<>]/g, function(c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; });
  }
  function attr(s) { return String(s || '').replace(/"/g, '&quot;'); }
  function tituloDoc(d) {
    return d.direccion_referencia || d.expediente || d.nombre_original;
  }

  async function renderLista() {
    var cont = document.getElementById('modificar-lista');
    try {
      // Modificar lista must show 'validado' and 'sin_ubicacion' since both are cataloged.
      var validados = await API.getAll('validado');
      var sinUbic = await API.getAll('sin_ubicacion');
      var indexados = validados.concat(sinUbic);

      if (indexados.length === 0) {
        cont.innerHTML = '<div class="empty">Todavía no hay planos catalogados.</div>';
        return;
      }
      cont.innerHTML = indexados.map(function(d) {
        var sel = d.id === seleccionadoId ? ' sel' : '';
        var badge = d.estado === 'sin_ubicacion'
          ? '<span class="badge sin_ubicacion">Sin ubicación</span>'
          : '<span class="badge validado">Validado</span>';
        return '<button class="row' + sel + '" onclick="PH.CUModificar.seleccionar(' + d.id + ')">' +
          '<div class="t">' + esc(tituloDoc(d)) + '</div>' +
          '<div class="s">' + badge + '</div>' +
          '</button>';
      }).join('');
    } catch (e) {
      cont.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
    }
>>>>>>> Stashed changes
  }

  function renderModificarDetalle() {
    var box = document.getElementById('modificar-detalle');
    if (!box) return;

<<<<<<< Updated upstream
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
=======
  function cancelar() {
    seleccionadoId = null;
    renderDetalle();
    renderLista();
  }

  async function renderDetalle() {
    var cont = document.getElementById('modificar-detalle');

    if (!seleccionadoId) {
      cont.innerHTML = '<div class="empty">Elija un plano catalogado para modificarlo.</div>';
      return;
    }

    try {
      var d = await API.getById(seleccionadoId);

      var historialHTML = d.historial && d.historial.length
        ? '<div class="hist"><h3>Historial de cambios</h3><ul>' +
          d.historial.slice().reverse().map(function(h) {
            var date = new Date(h.fecha).toLocaleString('es-AR');
            return '<li><strong>' + esc(date) + '</strong> — ' + esc(h.motivo) + '</li>';
          }).join('') + '</ul></div>'
        : '';

      cont.innerHTML = ''
        + '<img class="thumb" src="' + API.getArchivoUrl(d.id) + '" alt="Plano ' + esc(d.id) + '">'
        + CAMPOS.map(function(c) {
            var val = d[c.key] !== undefined && d[c.key] !== null ? d[c.key] : '';
            var type = c.type === 'number' ? 'number' : 'text';
            return '<div class="field"><label>' + c.label + '</label>' +
              '<input type="' + type + '" id="m-' + c.key + '" value="' + attr(val) + '"></div>';
          }).join('')
        + '<div class="field"><label>Parcela</label><input type="text" id="m-parcela" value="' + attr(d.parcela) + '"></div>'
        + '<div class="field"><label>Motivo del cambio</label>' +
          '<textarea id="m-motivo" rows="3" placeholder="Cuente brevemente por qué se corrige este dato"></textarea></div>'
        + '<div id="m-msg"></div>'
        + historialHTML
        + '<div class="det-actions">' +
          '<button class="ghost" onclick="PH.CUModificar.cancelar()">Cancelar</button>' +
          '<button class="primary" onclick="PH.CUModificar.guardar()">Guardar cambios</button>' +
          '</div>';

    } catch (e) {
      cont.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
    }
  }

  async function guardar() {
    if (!seleccionadoId) return;
>>>>>>> Stashed changes

    var motivo = State.val('m-motivo').trim();
    var msg = document.getElementById('modificar-msgs');
    if (!motivo) {
      if (msg) msg.innerHTML = '<div class="error">Ingrese una breve aclaración sobre por qué se modifica el plano.</div>';
      return;
    }

<<<<<<< Updated upstream
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
=======
    var datos = {};
    CAMPOS.forEach(function(c) {
      var v = document.getElementById('m-' + c.key).value.trim();
      datos[c.key] = v || null;
    });
    datos.parcela = document.getElementById('m-parcela').value.trim();
    datos.motivo = motivo;

    try {
      await API.modificar(seleccionadoId, datos);
      renderLista();
      renderDetalle();
      document.getElementById('m-msg').innerHTML = '<div class="confirm">Los cambios se guardaron correctamente.</div>';
      if (window.PH.actualizarListas) window.PH.actualizarListas();
    } catch (e) {
      document.getElementById('m-msg').innerHTML = '<div class="error">Error: ' + e.message + '</div>';
    }
>>>>>>> Stashed changes
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
