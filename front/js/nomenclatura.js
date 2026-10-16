(function(window) {
  'use strict';
  var campos = [
    { key: 'circunscripcion', label: 'Circunscripción (Circ.)', ejemplo: '3' },
    { key: 'seccion', label: 'Sección (Secc.)', ejemplo: 'K' },
    { key: 'manzana', label: 'Manzana (Mza.)', ejemplo: '12 o 12 A' },
    { key: 'parcela_catastral', label: 'Parcela (Parc.)', ejemplo: '5 o 5 B' }
  ];
  function normalizar(datos) {
    var resultado = {};
    campos.forEach(function(c, i) {
      var valor = String(datos[c.key] || '').trim().toUpperCase();
      var patron = i === 0 ? /^[0-9]+$/ : i === 1 ? /^[A-Z]+$/ : /^[0-9]+\s*[A-Z]*$/;
      if (!valor || valor.length > 64 || !patron.test(valor)) throw { codigo: 'nomenclatura' };
      if (i !== 1) {
        valor = valor.replace(/\s+/g, '').replace(/^0+(?=[0-9])/, '');
        if (/^0(?:[A-Z]*$)/.test(valor)) throw { codigo: 'nomenclatura' };
      }
      resultado[c.key] = valor;
    });
    return resultado;
  }
  function leer(prefijo) {
    var datos = {};
    campos.forEach(function(c) { datos[c.key] = document.getElementById(prefijo + c.key).value; });
    return normalizar(datos);
  }
  function clave(datos) { return campos.map(function(c) { return datos[c.key]; }).join('-'); }
  function esc(valor) {
    return String(valor || '').replace(/[&<>"']/g, function(c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function formulario(prefijo, datos) {
    datos = datos || {};
    return '<fieldset class="nomenclatura"><legend>Nomenclatura catastral — obligatoria</legend>'
      + '<p>Completá los cuatro datos. Manzana y parcela pueden incluir una letra después del número.</p>'
      + '<div class="grid2">' + campos.map(function(c, i) {
        return '<div class="field"><label for="' + prefijo + c.key + '">' + c.label + '</label>'
          + '<input type="text" required maxlength="64" ' + (i === 0 ? 'inputmode="numeric" ' : '')
          + 'id="' + prefijo + c.key + '" value="' + esc(datos[c.key]) + '" placeholder="' + c.ejemplo + '"></div>';
      }).join('') + '</div></fieldset>';
  }
  function titulo(datos) {
    return datos.nomenclatura ? 'Circ. ' + datos.circunscripcion + ' · Secc. ' + datos.seccion
      + ' · Mza. ' + datos.manzana + ' · Parc. ' + datos.parcela_catastral : 'Nomenclatura pendiente de completar';
  }
  window.PH = window.PH || {};
  window.PH.Nomenclatura = { normalizar: normalizar, leer: leer, clave: clave, formulario: formulario, titulo: titulo };
})(window);
