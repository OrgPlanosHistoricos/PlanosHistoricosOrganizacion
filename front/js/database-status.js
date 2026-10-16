(function(window) {
  'use strict';

  var running = false;

  function render(state, message) {
    var indicator = document.getElementById('database-status');
    if (!indicator) return;
    indicator.dataset.state = state;
    document.getElementById('database-status-text').textContent = message;
  }

  async function check() {
    if (running) return;
    running = true;
    var controller = new AbortController();
    var timeout = setTimeout(function() { controller.abort(); }, 8000);
    try {
      var response = await fetch('/api/health/database', {
        cache: 'no-store', signal: controller.signal
      });
      var body = await response.json();
      if (response.ok && body.database === 'connected') {
        render('connected', 'Base de datos conectada');
      } else if (response.status === 503 && body.database === 'disconnected') {
        render('disconnected', 'Base de datos sin conexión');
      } else {
        render('unknown', 'No se pudo verificar la base de datos');
      }
    } catch (error) {
      render('unknown', 'No se pudo verificar la base de datos');
    } finally {
      clearTimeout(timeout);
      running = false;
    }
  }

  function init() {
    check();
    setInterval(check, 15000);
    window.addEventListener('online', check);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
