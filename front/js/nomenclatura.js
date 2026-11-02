(function(window) {
  'use strict';
  var campos = [
    { key: 'circunscripcion', label: 'Circunscripción (Circ.)', ejemplo: '3' },
    { key: 'seccion', label: 'Sección (Secc.)', ejemplo: 'K' },
    { key: 'manzana', label: 'Manzana (Mza.)', ejemplo: '12 o 12 A' },
    { key: 'parcela_catastral', label: 'Parcela (Parc.)', ejemplo: '5 o 5 B' }
  ];
  function normalizar(datos, completa) {
    var resultado = {};
    campos.forEach(function(c, i) {
      var valor = String(datos[c.key] || '').trim().toUpperCase();
      var patron = i === 0 ? /^[0-9]+$/ : i === 1 ? /^[A-Z]+$/ : /^[0-9]+\s*[A-Z]*$/;
      if (!valor) {
        if (completa) throw { codigo: 'nomenclatura' };
        resultado[c.key] = '';
        return;
      }
      if (valor.length > 64 || !patron.test(valor)) throw { codigo: 'nomenclatura' };
      if (i !== 1) {
        valor = valor.replace(/\s+/g, '').replace(/^0+(?=[0-9])/, '');
        if (/^0(?:[A-Z]*$)/.test(valor)) throw { codigo: 'nomenclatura' };
      }
      resultado[c.key] = valor;
    });
    return resultado;
  }
  function leer(prefijo, completa) {
    var datos = {};
    campos.forEach(function(c) { datos[c.key] = document.getElementById(prefijo + c.key).value; });
    return normalizar(datos, completa);
  }
  function clave(datos) { return campos.map(function(c) { return datos[c.key]; }).join('-'); }
  function esc(valor) {
    return String(valor || '').replace(/[&<>"']/g, function(c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function formulario(prefijo, datos, completa) {
    datos = datos || {};
    return '<fieldset class="nomenclatura"><legend>Nomenclatura catastral' + (completa ? ' — búsqueda exacta' : '') + '</legend>'
      + (completa ? '<p>Completá los cuatro datos para buscar. Manzana y parcela pueden incluir una letra después del número.</p>' : '')
      + '<div class="grid2">' + campos.map(function(c, i) {
        return '<div class="field"><label for="' + prefijo + c.key + '">' + c.label + '</label>'
          + '<input type="text" ' + (completa ? 'required ' : '') + 'maxlength="64" ' + (i === 0 ? 'inputmode="numeric" onkeydown="if([\\\'-\\\',\\\'+\\\',\\\'e\\\',\\\'E\\\',\\\'.\\\',\\\',\\\',\\\'/\\\'].includes(event.key)) event.preventDefault();" oninput="this.value = this.value.replace(/[^0-9]/g, \\\'\\\');" ' : '')
          + 'id="' + prefijo + c.key + '" value="' + esc(datos[c.key]) + '" placeholder="' + c.ejemplo + '"></div>';
      }).join('') + '</div></fieldset>';
  }
  function titulo(datos) {
    return datos.nomenclatura || campos.some(function(c) { return datos[c.key]; })
      ? 'Circ. ' + (datos.circunscripcion || '-') + ' · Secc. ' + (datos.seccion || '-')
      + ' · Mza. ' + (datos.manzana || '-') + ' · Parc. ' + (datos.parcela_catastral || '-')
      : (datos.nombre_original || 'Plano ' + (datos.id || '')) + ' — Sin nomenclatura';
  }
  window.PH = window.PH || {};
  window.PH.Nomenclatura = { normalizar: normalizar, leer: leer, clave: clave, formulario: formulario, titulo: titulo };
})(window);
