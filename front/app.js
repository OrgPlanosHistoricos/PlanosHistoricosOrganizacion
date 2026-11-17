/**
 * app.js - Orquestador principal de la aplicación Archivo de Planos Históricos
 */
(function(window) {
  'use strict';

  var CUCargar = window.PH.CUCargar;
  var CUValidar = window.PH.CUValidar;
  var CUModificar = window.PH.CUModificar;
  var CUConsultar = window.PH.CUConsultar;
  var Auth = window.PH.Auth;

  function puedeAcceder(tab) {
    return !Auth || typeof Auth.canAccessTab !== 'function' || Auth.canAccessTab(tab);
  }

  function mostrarVista(tab) {
    document.querySelectorAll('.tab').forEach(function(b) {
      b.classList.toggle('active', b.dataset.tab === tab);
    });
    document.querySelectorAll('.view').forEach(function(v) {
      v.classList.toggle('active', v.id === 'view-' + tab);
    });
  }

  function cargarDatosTab(tab) {
    if (tab === 'cargar') CUCargar.renderRecientes();
    if (tab === 'validar') {
      CUValidar.renderLista();
      CUValidar.renderDetalle();
    }
    if (tab === 'modificar') {
      CUModificar.renderLista();
      CUModificar.renderDetalle();
    }
    if (tab === 'consultar') {
      CUConsultar.renderLista('');
    }
  }

  function activarTab(tab) {
    if (!puedeAcceder(tab)) return;
    mostrarVista(tab);
    cargarDatosTab(tab);
  }

  function inicializarNavegacion() {
    document.querySelectorAll('.tab').forEach(function(btn) {
      var tab = btn.dataset.tab;
      if (!puedeAcceder(tab)) {
        btn.hidden = true;
        btn.setAttribute('aria-hidden', 'true');
        return;
      }
      btn.hidden = false;
      btn.removeAttribute('aria-hidden');
      btn.addEventListener('click', function() {
        activarTab(btn.dataset.tab);
      });
    });
  }

  function goTab(tab) {
    var target = puedeAcceder(tab) ? tab : (Auth && typeof Auth.getDefaultTab === 'function' ? Auth.getDefaultTab() : tab);
    if (target) activarTab(target);
  }

  function actualizarListas() {
    if (puedeAcceder('cargar')) CUCargar.renderRecientes();
    if (puedeAcceder('validar')) CUValidar.renderLista();
    if (puedeAcceder('modificar')) CUModificar.renderLista();
  }

  function initApp() {
    if (Auth && typeof Auth.requireSession === 'function' && !Auth.requireSession()) {
      return;
    }
    if (document.body && document.body.classList) {
      document.body.classList.remove('auth-pending');
    }
    if (Auth && typeof Auth.renderUserBadge === 'function') {
      Auth.renderUserBadge();
    }

    inicializarNavegacion();
    if (puedeAcceder('cargar')) CUCargar.inicializar();
    if (puedeAcceder('consultar')) CUConsultar.inicializar();

    var tabInicial = (Auth && typeof Auth.getDefaultTab === 'function' && Auth.getDefaultTab()) || 'cargar';
    mostrarVista(tabInicial);

    if (puedeAcceder('cargar')) CUCargar.renderRecientes();
    if (puedeAcceder('validar')) CUValidar.renderLista();
    if (puedeAcceder('modificar')) CUModificar.renderLista();
    if (puedeAcceder('consultar')) CUConsultar.renderLista('');

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
