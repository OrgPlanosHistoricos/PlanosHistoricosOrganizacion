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

  var hardwareDetectado = { gpu_disponible: true, tipo: 'GPU', nombre: 'GPU' };

  function actualizarUIGpu(usarGpu) {
    var toggle = document.getElementById('toggle-gpu');
    var badge = document.getElementById('gpu-status-badge');
    var desc = document.getElementById('gpu-desc-text');
    var hint = document.getElementById('cargar-modo-hint');

    if (toggle) toggle.checked = usarGpu;
    if (badge) {
      if (usarGpu) {
        var tipo = hardwareDetectado.tipo || 'GPU';
        badge.textContent = tipo;
        badge.className = 'badge-engine ' + (tipo.toLowerCase() === 'amd' ? 'amd' : 'nvidia');
      } else {
        badge.textContent = 'CPU';
        badge.className = 'badge-engine cpu';
      }
    }
    if (desc) {
      if (usarGpu) {
        desc.textContent = '⚡ Aceleración activa: ' + (hardwareDetectado.nombre || hardwareDetectado.tipo);
      } else {
        desc.textContent = 'Inferencia en CPU (predeterminado)';
      }
    }
    if (hint) {
      if (usarGpu) {
        hint.innerHTML = '⚙️ Procesamiento actual: <strong>GPU (' + hardwareDetectado.tipo + ')</strong>';
      } else {
        hint.innerHTML = '⚙️ Procesamiento actual: <strong>CPU</strong>';
      }
    }
  }

  async function inicializarControlGPU() {
    var toggle = document.getElementById('toggle-gpu');
    var preferencia = window.PH.API.getGpuPreference ? window.PH.API.getGpuPreference() : false;
    actualizarUIGpu(preferencia);

    if (window.PH.API.getHardwareInfo) {
      try {
        var info = await window.PH.API.getHardwareInfo();
        if (info) {
          hardwareDetectado = info;
          actualizarUIGpu(window.PH.API.getGpuPreference ? window.PH.API.getGpuPreference() : false);
        }
      } catch (e) {
        console.warn('No se pudo consultar información de hardware:', e);
      }
    }

    if (toggle) {
      toggle.addEventListener('change', function(ev) {
        var activo = ev.target.checked;
        if (window.PH.API.setGpuPreference) {
          window.PH.API.setGpuPreference(activo);
        }
        actualizarUIGpu(activo);
      });
    }
  }

  function initApp() {
    inicializarNavegacion();
    inicializarControlGPU();
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
