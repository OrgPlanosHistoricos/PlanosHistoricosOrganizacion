/**
 * auth.js - Mockup de autenticación y control de roles para GIUOS / Planos Históricos.
 */
(function(window) {
  'use strict';

  var STORAGE_KEY = 'ph_sesion_usuario';
  var DESTINOS_PERMITIDOS = ['planos-historicos.html', 'Archivo_de_Planos_Históricos.html'];

  var ROLES = {
    operador: {
      id: 'operador',
      etiqueta: 'Operador Documental',
      tabs: ['cargar', 'consultar'],
      descripcion: 'Carga e ingesta de planos al análisis automático y consulta del catálogo.'
    },
    validador: {
      id: 'validador',
      etiqueta: 'Validador Documental',
      tabs: ['validar', 'modificar', 'consultar'],
      descripcion: 'Validación catastral, modificación de catalogación con auditoría y consulta.'
    },
    consulta: {
      id: 'consulta',
      etiqueta: 'Usuario de Consulta',
      tabs: ['consultar'],
      descripcion: 'Búsqueda, previsualización y descarga de planos históricos catalogados.'
    },
    admin: {
      id: 'admin',
      etiqueta: 'Administrador',
      tabs: ['cargar', 'validar', 'modificar', 'consultar'],
      descripcion: 'Acceso completo a carga, validación, modificación y consulta.'
    }
  };

  var USUARIOS = [
    {
      usuario: 'operador',
      correo: 'operador@giuos.gob.ar',
      clave: 'operador123',
      nombre: 'Lucía Fernández',
      iniciales: 'LF',
      rol: 'operador',
      auditId: 'lfernandez (Operador)'
    },
    {
      usuario: 'validador',
      correo: 'validador@giuos.gob.ar',
      clave: 'validador123',
      nombre: 'Martín Sosa',
      iniciales: 'MS',
      rol: 'validador',
      auditId: 'msosa (Validador)'
    },
    {
      usuario: 'consulta',
      correo: 'consulta@giuos.gob.ar',
      clave: 'consulta123',
      nombre: 'Carolina Martínez',
      iniciales: 'CM',
      rol: 'consulta',
      auditId: 'cmartinez (Consulta)'
    },
    {
      usuario: 'admin',
      correo: 'admin@giuos.gob.ar',
      clave: 'admin123',
      nombre: 'Victoria Prieto',
      iniciales: 'VP',
      rol: 'admin',
      auditId: 'vprieto (Admin)'
    }
  ];

  var ETIQUETAS_TAB = {
    cargar: 'Cargar plano',
    validar: 'Validar y catalogar',
    modificar: 'Modificar catalogación',
    consultar: 'Consultar'
  };

  function esc(valor) {
    return String(valor === undefined || valor === null ? '' : valor).replace(/[&<>"']/g, function(c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function storageGet(storageName, key) {
    try {
      var st = window[storageName];
      return st && typeof st.getItem === 'function' ? st.getItem(key) : null;
    } catch (e) {
      return null;
    }
  }

  function storageSet(storageName, key, value) {
    try {
      var st = window[storageName];
      if (st && typeof st.setItem === 'function') st.setItem(key, value);
    } catch (e) { /* Ignorar restricciones de almacenamiento en entorno sin storage. */ }
  }

  function storageRemove(storageName, key) {
    try {
      var st = window[storageName];
      if (st && typeof st.removeItem === 'function') st.removeItem(key);
    } catch (e) { /* Ignorar restricciones de almacenamiento. */ }
  }

  function construirSesion(usuarioObj) {
    var rolInfo = ROLES[usuarioObj.rol];
    return {
      usuario: usuarioObj.usuario,
      correo: usuarioObj.correo,
      nombre: usuarioObj.nombre,
      iniciales: usuarioObj.iniciales,
      rol: rolInfo.id,
      rolEtiqueta: rolInfo.etiqueta,
      auditId: usuarioObj.auditId,
      tabs: rolInfo.tabs.slice(),
      iniciadoEn: new Date().toISOString()
    };
  }

  function getSession() {
    var raw = storageGet('sessionStorage', STORAGE_KEY) || storageGet('localStorage', STORAGE_KEY);
    if (!raw) return null;
    try {
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object') {
        logout();
        return null;
      }
      var encontrado = USUARIOS.find(function(u) {
        return u.usuario === parsed.usuario && u.rol === parsed.rol;
      });
      if (!encontrado || !ROLES[encontrado.rol]) {
        logout();
        return null;
      }
      var sesion = construirSesion(encontrado);
      if (typeof parsed.iniciadoEn === 'string') sesion.iniciadoEn = parsed.iniciadoEn;
      return sesion;
    } catch (e) {
      logout();
      return null;
    }
  }

  function login(identificador, clave, recordar) {
    var idNorm = String(identificador || '').trim().toLowerCase();
    var claveStr = String(clave || '');
    if (!idNorm || !claveStr) {
      return { ok: false, mensaje: 'Ingresá tu usuario o correo electrónico y la contraseña.' };
    }
    var usuarioEncontrado = USUARIOS.find(function(u) {
      return (u.usuario === idNorm || u.correo === idNorm) && u.clave === claveStr;
    });
    if (!usuarioEncontrado) {
      return {
        ok: false,
        mensaje: 'Usuario o contraseña incorrectos. Verificá los datos o elegí uno de los perfiles de prueba.'
      };
    }
    var sesion = construirSesion(usuarioEncontrado);
    var serializado = JSON.stringify(sesion);
    storageSet('sessionStorage', STORAGE_KEY, serializado);
    if (recordar !== false) {
      storageSet('localStorage', STORAGE_KEY, serializado);
    } else {
      storageRemove('localStorage', STORAGE_KEY);
    }
    return { ok: true, sesion: sesion };
  }

  function logout() {
    storageRemove('sessionStorage', STORAGE_KEY);
    storageRemove('localStorage', STORAGE_KEY);
  }

  function getUsuarioId(fallback) {
    var sesion = getSession();
    return (sesion && sesion.auditId) || fallback || null;
  }

  function getAllowedTabs() {
    var sesion = getSession();
    return sesion ? sesion.tabs.slice() : [];
  }

  function canAccessTab(tab) {
    var tabs = getAllowedTabs();
    return tabs.indexOf(tab) !== -1;
  }

  function getDefaultTab() {
    var tabs = getAllowedTabs();
    return tabs.length ? tabs[0] : null;
  }

  function destinoSeguro(destino) {
    var limpio = String(destino || '').trim();
    return DESTINOS_PERMITIDOS.indexOf(limpio) !== -1 ? limpio : 'planos-historicos.html';
  }

  function paginaActual() {
    if (!window.location || !window.location.pathname) return 'planos-historicos.html';
    var partes = window.location.pathname.split('/');
    var nombre = partes[partes.length - 1] || '';
    try {
      nombre = decodeURIComponent(nombre);
    } catch (e) { /* Usar nombre crudo si falla decodeURIComponent. */ }
    return destinoSeguro(nombre);
  }

  function requireSession() {
    var sesion = getSession();
    if (sesion) return sesion;
    if (window.location && typeof window.location.replace === 'function') {
      var destino = paginaActual();
      window.location.replace('index.html?motivo=sesion_requerida&destino=' + encodeURIComponent(destino));
    }
    return null;
  }

  function logoutAndRedirect() {
    logout();
    if (window.location && typeof window.location.assign === 'function') {
      window.location.assign('index.html');
    } else if (window.location) {
      window.location.href = 'index.html';
    }
  }

  function renderUserBadge() {
    var cont = document.getElementById('user-session');
    if (!cont) return;
    var sesion = getSession();
    if (!sesion) {
      cont.innerHTML = '';
      return;
    }
    cont.innerHTML = ''
      + '<div class="user-session-info">'
      +   '<span class="user-avatar" aria-hidden="true">' + esc(sesion.iniciales) + '</span>'
      +   '<div class="user-meta">'
      +     '<div class="user-name">' + esc(sesion.nombre) + '</div>'
      +     '<span class="role-badge role-' + esc(sesion.rol) + '">' + esc(sesion.rolEtiqueta) + '</span>'
      +   '</div>'
      + '</div>'
      + '<button type="button" id="btn-logout" class="ghost user-logout">Cerrar sesión</button>';
    var btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
      btnLogout.addEventListener('click', logoutAndRedirect);
    }
  }

  function getDemoUsers() {
    return USUARIOS.map(function(u) {
      var rolInfo = ROLES[u.rol];
      return {
        usuario: u.usuario,
        correo: u.correo,
        clave: u.clave,
        nombre: u.nombre,
        iniciales: u.iniciales,
        rol: u.rol,
        rolEtiqueta: rolInfo.etiqueta,
        tabs: rolInfo.tabs.slice(),
        descripcion: rolInfo.descripcion
      };
    });
  }

  function getRoles() {
    var copia = {};
    Object.keys(ROLES).forEach(function(key) {
      copia[key] = {
        id: ROLES[key].id,
        etiqueta: ROLES[key].etiqueta,
        tabs: ROLES[key].tabs.slice(),
        descripcion: ROLES[key].descripcion
      };
    });
    return copia;
  }

  function describirPermisos(tabs) {
    return tabs.map(function(t) { return ETIQUETAS_TAB[t] || t; }).join(' · ');
  }

  function leerParametrosUrl() {
    var search = (window.location && window.location.search) || '';
    if (typeof URLSearchParams === 'undefined') return { motivo: '', destino: 'planos-historicos.html' };
    var params = new URLSearchParams(search);
    return {
      motivo: params.get('motivo') || '',
      destino: destinoSeguro(params.get('destino'))
    };
  }

  function renderizarPerfilesDemo(seleccionado) {
    var cont = document.getElementById('demo-users-list');
    if (!cont) return;
    cont.innerHTML = getDemoUsers().map(function(u) {
      var selClass = seleccionado === u.usuario ? ' selected' : '';
      return '<button type="button" class="demo-user-btn' + selClass + '" data-demo-user="' + esc(u.usuario) + '" aria-pressed="' + (seleccionado === u.usuario ? 'true' : 'false') + '">'
        + '<div class="demo-user-head">'
        +   '<strong>' + esc(u.nombre) + '</strong>'
        +   '<span class="role-badge role-' + esc(u.rol) + '">' + esc(u.rolEtiqueta) + '</span>'
        + '</div>'
        + '<div class="demo-user-creds">Usuario: <code>' + esc(u.usuario) + '</code> · Clave: <code>' + esc(u.clave) + '</code></div>'
        + '<div class="demo-user-perms">Módulos: ' + esc(describirPermisos(u.tabs)) + '</div>'
        + '</button>';
    }).join('');

    cont.querySelectorAll('.demo-user-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var user = USUARIOS.find(function(u) { return u.usuario === btn.dataset.demoUser; });
        if (!user) return;
        var inputUser = document.getElementById('login-usuario');
        var inputPass = document.getElementById('login-clave');
        var msgs = document.getElementById('login-msgs');
        if (inputUser) inputUser.value = user.usuario;
        if (inputPass) inputPass.value = user.clave;
        if (msgs) msgs.innerHTML = '';
        renderizarPerfilesDemo(user.usuario);
        var submitBtn = document.getElementById('btn-login-submit');
        if (submitBtn && typeof submitBtn.focus === 'function') submitBtn.focus();
      });
    });
  }

  function actualizarVistaPortal(destino) {
    var form = document.getElementById('form-login');
    var sesionActiva = document.getElementById('login-sesion-activa');
    var msgs = document.getElementById('login-msgs');
    var sesion = getSession();

    if (sesion && sesionActiva && form) {
      form.hidden = true;
      sesionActiva.hidden = false;
      sesionActiva.innerHTML = ''
        + '<div class="session-summary">'
        +   '<div class="user-session-info">'
        +     '<span class="user-avatar" aria-hidden="true">' + esc(sesion.iniciales) + '</span>'
        +     '<div class="user-meta">'
        +       '<div class="user-name">' + esc(sesion.nombre) + '</div>'
        +       '<div class="session-email">' + esc(sesion.correo) + '</div>'
        +       '<span class="role-badge role-' + esc(sesion.rol) + '">' + esc(sesion.rolEtiqueta) + '</span>'
        +     '</div>'
        +   '</div>'
        +   '<p class="session-perms"><strong>Secciones habilitadas:</strong> ' + esc(describirPermisos(sesion.tabs)) + '</p>'
        +   '<div class="session-actions">'
        +     '<a class="btn-primary-link" href="' + esc(destino) + '">Ingresar a Planos Históricos →</a>'
        +     '<button type="button" id="btn-cerrar-sesion-portal" class="ghost">Cerrar sesión / Cambiar usuario</button>'
        +   '</div>'
        + '</div>';
      var btnSalir = document.getElementById('btn-cerrar-sesion-portal');
      if (btnSalir) {
        btnSalir.addEventListener('click', function() {
          logout();
          if (typeof form.reset === 'function') form.reset();
          renderizarPerfilesDemo(null);
          if (msgs) msgs.innerHTML = '';
          actualizarVistaPortal(destino);
        });
      }
    } else if (form && sesionActiva) {
      form.hidden = false;
      sesionActiva.hidden = true;
      sesionActiva.innerHTML = '';
    }
  }

  function initLoginPage() {
    var form = document.getElementById('form-login');
    if (!form) return;
    var query = leerParametrosUrl();
    var msgs = document.getElementById('login-msgs');
    if (query.motivo === 'sesion_requerida' && msgs && !getSession()) {
      msgs.innerHTML = '<div class="hint">Iniciá sesión para acceder al Archivo de Planos Históricos.</div>';
    }

    renderizarPerfilesDemo(null);
    actualizarVistaPortal(query.destino);

    var toggleBtn = document.getElementById('toggle-clave');
    var inputClave = document.getElementById('login-clave');
    if (toggleBtn && inputClave) {
      toggleBtn.addEventListener('click', function() {
        var mostrar = inputClave.type === 'password';
        inputClave.type = mostrar ? 'text' : 'password';
        toggleBtn.textContent = mostrar ? 'Ocultar' : 'Mostrar';
        toggleBtn.setAttribute('aria-pressed', String(mostrar));
      });
    }

    form.addEventListener('submit', function(ev) {
      ev.preventDefault();
      var usuario = document.getElementById('login-usuario').value;
      var clave = document.getElementById('login-clave').value;
      var recordarEl = document.getElementById('login-recordar');
      var recordar = recordarEl ? Boolean(recordarEl.checked) : true;
      var resultado = login(usuario, clave, recordar);
      if (!resultado.ok) {
        if (msgs) msgs.innerHTML = '<div class="error">' + esc(resultado.mensaje) + '</div>';
        return;
      }
      if (msgs) msgs.innerHTML = '';
      if (window.location && typeof window.location.assign === 'function') {
        window.location.assign(query.destino);
      } else if (window.location) {
        window.location.href = query.destino;
      }
    });
  }

  window.PH = window.PH || {};
  window.PH.Auth = {
    ROLES: getRoles(),
    getRoles: getRoles,
    getDemoUsers: getDemoUsers,
    login: login,
    logout: logout,
    logoutAndRedirect: logoutAndRedirect,
    getSession: getSession,
    getUsuarioId: getUsuarioId,
    getAllowedTabs: getAllowedTabs,
    canAccessTab: canAccessTab,
    getDefaultTab: getDefaultTab,
    destinoSeguro: destinoSeguro,
    requireSession: requireSession,
    renderUserBadge: renderUserBadge,
    initLoginPage: initLoginPage
  };

})(window);
