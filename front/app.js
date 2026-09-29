/**
 * app.js - Orquestador principal de la aplicación Archivo de Planos Históricos
 * Inicializa el estado, coordina los módulos por caso de uso y gestiona la navegación por pestañas.
 */
(function(window) {
  'use strict';

  var State = window.PH.State;
  var CUCargar = window.PH.CUCargar;
  var CUValidar = window.PH.CUValidar;
  var CUModificar = window.PH.CUModificar;
  var CUConsultar = window.PH.CUConsultar;

  // ---- Navegación por pestañas ----
  function inicializarNavegacion() {
    document.querySelectorAll('.tab').forEach(function(btn) {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.tab').forEach(function(b) { b.classList.remove('active'); });
        document.querySelectorAll('.view').forEach(function(v) { v.classList.remove('active'); });

        btn.classList.add('active');
        var view = document.getElementById('view-' + btn.dataset.tab);
        if (view) view.classList.add('active');

        // Actualizar datos según la pestaña activa
        if (btn.dataset.tab === 'cargar') {
          CUCargar.renderRecientes();
        }
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

  // Actualización reactiva cuando la IA completa o modifica un plano en background
  function onPlanoIAActualizado(p) {
    CUCargar.renderRecientes();
    CUValidar.renderLista();

    if (CUValidar.getSeleccionadoId && CUValidar.getSeleccionadoId() === p.id) {
      CUValidar.renderDetalle();
    }
  }

  function actualizarListas() {
    CUCargar.renderRecientes();
    CUValidar.renderLista();
    CUModificar.renderLista();
  }

  // ---- Inicialización general de la App ----
  function initApp() {
    // 1. Cargar o sembrar datos iniciales
    if (!State.load()) {
      State.seed();
      State.save();
    }

    // 2. Inicializar componentes y eventos
    inicializarNavegacion();
    CUCargar.inicializar();
    CUConsultar.inicializar();

    // 3. Reanudar polling de tareas que hayan quedado procesando en backend
    State.reanudarTareasPendientes();

    // 4. Renderizado inicial
    CUCargar.renderRecientes();
    CUValidar.renderLista();
    CUModificar.renderLista();
    CUConsultar.renderLista('');
  }

  // Exponer API global
  window.PH = window.PH || {};
  window.PH.goTab = goTab;
  window.PH.onPlanoIAActualizado = onPlanoIAActualizado;
  window.PH.actualizarListas = actualizarListas;
  window.PH.initApp = initApp;

  // Iniciar al cargar el DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }

})(window);
