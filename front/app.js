/**
 * app.js - Orquestador principal de la aplicación Archivo de Planos Históricos
 */
(function(window) {
  'use strict';

  var CUCargar = window.PH.CUCargar;
  var CUValidar = window.PH.CUValidar;
  var CUModificar = window.PH.CUModificar;
  var CUConsultar = window.PH.CUConsultar;

  function inicializarNavegacion() {
    document.querySelectorAll('.tab').forEach(function(btn) {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.tab').forEach(function(b) { b.classList.remove('active'); });
        document.querySelectorAll('.view').forEach(function(v) { v.classList.remove('active'); });

        btn.classList.add('active');
        var view = document.getElementById('view-' + btn.dataset.tab);
        if (view) view.classList.add('active');

        if (btn.dataset.tab === 'cargar') CUCargar.renderRecientes();
        if (btn.dataset.tab === 'validar') {
          CUValidar.renderLista();
          CUValidar.renderDetalle();
        }
        if (btn.dataset.tab === 'modificar') {
          CUModificar.renderLista();
          CUModificar.renderDetalle();
        }
        if (btn.dataset.tab === 'consultar') {
          CUConsultar.renderLista('');
        }
      });
    });
  }

  function goTab(tab) {
    var btn = document.querySelector('.tab[data-tab="' + tab + '"]');
    if (btn) btn.click();
  }

  function actualizarListas() {
    CUCargar.renderRecientes();
    CUValidar.renderLista();
    CUModificar.renderLista();
  }

  function initApp() {
    inicializarNavegacion();
    CUCargar.inicializar();
    CUConsultar.inicializar();

    CUCargar.renderRecientes();
    CUValidar.renderLista();
    CUModificar.renderLista();
    CUConsultar.renderLista('');

    // Poll every 5 seconds to get background processing updates
    setInterval(actualizarListas, 5000);
  }

  window.PH = window.PH || {};
  window.PH.goTab = goTab;
  window.PH.actualizarListas = actualizarListas;
  window.PH.initApp = initApp;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }

})(window);
