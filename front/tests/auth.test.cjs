const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function createStorage() {
  const map = new Map();
  return {
    getItem(k) { return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { map.set(k, String(v)); },
    removeItem(k) { map.delete(k); },
    _raw: map
  };
}

function makeEl(id, extra = {}) {
  const listeners = {};
  const attrs = {};
  const classes = new Set(extra.classes || []);
  return {
    id,
    innerHTML: '',
    value: '',
    textContent: '',
    type: extra.type || 'text',
    checked: extra.checked !== undefined ? extra.checked : false,
    hidden: false,
    files: [],
    dataset: extra.dataset || {},
    style: {},
    classList: {
      toggle(cls, force) {
        if (force === undefined) {
          if (classes.has(cls)) { classes.delete(cls); return false; }
          classes.add(cls); return true;
        }
        if (force) classes.add(cls); else classes.delete(cls);
        return Boolean(force);
      },
      contains(cls) { return classes.has(cls); },
      add(cls) { classes.add(cls); },
      remove(cls) { classes.delete(cls); }
    },
    setAttribute(k, v) { attrs[k] = String(v); },
    getAttribute(k) { return attrs[k]; },
    removeAttribute(k) { delete attrs[k]; },
    addEventListener(ev, fn) { (listeners[ev] ||= []).push(fn); },
    dispatch(ev, payload = { preventDefault() {} }) {
      for (const fn of (listeners[ev] || [])) fn(payload);
    },
    querySelectorAll() { return []; },
    reset() {},
    focus() {}
  };
}

function setupAuth(opts = {}) {
  const elements = {};
  const sessionStorage = createStorage();
  const localStorage = createStorage();
  const locationCalls = { replace: [], assign: [] };
  const location = {
    pathname: opts.pathname || '/planos-historicos.html',
    search: opts.search || '',
    href: '',
    replace(u) { locationCalls.replace.push(u); },
    assign(u) { locationCalls.assign.push(u); }
  };
  const body = makeEl('body', { classes: ['auth-pending'] });

  const tabs = ['cargar', 'validar', 'modificar', 'consultar'].map(t =>
    makeEl('tab-' + t, { dataset: { tab: t }, classes: t === 'cargar' ? ['tab', 'active'] : ['tab'] })
  );
  const views = ['cargar', 'validar', 'modificar', 'consultar'].map(t =>
    makeEl('view-' + t, { classes: t === 'cargar' ? ['view', 'active'] : ['view'] })
  );

  const context = vm.createContext({
    URLSearchParams,
    FormData,
    SyntaxError,
    setInterval: opts.setInterval || (() => 1),
    window: {
      PH: {},
      location,
      sessionStorage,
      localStorage
    },
    document: {
      readyState: 'loading',
      body,
      addEventListener() {},
      getElementById(id) {
        return elements[id] ||= makeEl(id);
      },
      querySelectorAll(sel) {
        if (sel === '.tab') return tabs;
        if (sel === '.view') return views;
        return [];
      }
    }
  });
  context.window.window = context.window;
  context.fetch = opts.fetch || (async () => ({ ok: true, json: async () => [] }));

  const files = opts.files || ['auth', 'state', 'nomenclatura', 'cu-cargar', 'cu-consultar', 'cu-modificar', 'cu-validar'];
  for (const file of files) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../js/' + file + '.js'), 'utf8'), context);
  }
  if (opts.loadApp) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../app.js'), 'utf8'), context);
  }

  return {
    PH: context.window.PH,
    context,
    elements,
    sessionStorage,
    localStorage,
    locationCalls,
    tabs,
    views,
    body
  };
}

test('auth: login exitoso por usuario o correo y permisos por rol', () => {
  const { PH } = setupAuth();

  const casos = [
    ['Operador', 'operador123', 'operador', ['cargar', 'consultar'], 'lfernandez (Operador)'],
    ['validador@giuos.gob.ar', 'validador123', 'validador', ['validar', 'modificar', 'consultar'], 'msosa (Validador)'],
    ['  consulta  ', 'consulta123', 'consulta', ['consultar'], 'cmartinez (Consulta)'],
    ['admin@giuos.gob.ar', 'admin123', 'admin', ['cargar', 'validar', 'modificar', 'consultar'], 'vprieto (Admin)']
  ];

  for (const [id, clave, rol, tabsEsperados, auditId] of casos) {
    const res = PH.Auth.login(id, clave, true);
    assert.equal(res.ok, true);
    assert.equal(res.sesion.rol, rol);
    assert.deepEqual(Array.from(PH.Auth.getAllowedTabs()), tabsEsperados);
    assert.equal(PH.Auth.getDefaultTab(), tabsEsperados[0]);
    assert.equal(PH.Auth.getUsuarioId(), auditId);
    assert.equal(PH.Auth.canAccessTab('consultar'), true);
    assert.equal(PH.Auth.canAccessTab('validar'), tabsEsperados.includes('validar'));
    PH.Auth.logout();
    assert.equal(PH.Auth.getSession(), null);
  }
});

test('auth: rechaza credenciales vacías o incorrectas sin crear sesión', () => {
  const { PH } = setupAuth();
  assert.equal(PH.Auth.login('', 'operador123').ok, false);
  assert.equal(PH.Auth.login('operador', '').ok, false);
  assert.equal(PH.Auth.login('operador', 'incorrecta').ok, false);
  assert.equal(PH.Auth.login('inexistente', '123456').ok, false);
  assert.equal(PH.Auth.getSession(), null);
});

test('auth: recordar=false guarda solo en sessionStorage y recordar=true en ambos; logout limpia ambos', () => {
  const { PH, sessionStorage, localStorage } = setupAuth();

  PH.Auth.login('operador', 'operador123', false);
  assert.ok(sessionStorage.getItem('ph_sesion_usuario'));
  assert.equal(localStorage.getItem('ph_sesion_usuario'), null);

  PH.Auth.login('validador', 'validador123', true);
  assert.ok(sessionStorage.getItem('ph_sesion_usuario'));
  assert.ok(localStorage.getItem('ph_sesion_usuario'));

  PH.Auth.logout();
  assert.equal(sessionStorage.getItem('ph_sesion_usuario'), null);
  assert.equal(localStorage.getItem('ph_sesion_usuario'), null);
});

test('auth: descarta y limpia sesiones corruptas o manipuladas en storage', () => {
  const { PH, localStorage } = setupAuth();
  localStorage.setItem('ph_sesion_usuario', '{json roto');
  assert.equal(PH.Auth.getSession(), null);
  assert.equal(localStorage.getItem('ph_sesion_usuario'), null);

  localStorage.setItem('ph_sesion_usuario', JSON.stringify({ usuario: '<script>xss</script>', rol: 'admin' }));
  assert.equal(PH.Auth.getSession(), null);
  assert.equal(localStorage.getItem('ph_sesion_usuario'), null);

  localStorage.setItem('ph_sesion_usuario', JSON.stringify({ usuario: 'consulta', rol: 'admin' }));
  assert.equal(PH.Auth.getSession(), null);
});

test('auth: destinoSeguro previene open-redirect y requireSession redirige cuando falta sesión', () => {
  const { PH, locationCalls } = setupAuth({ pathname: '/Archivo_de_Planos_Hist%C3%B3ricos.html' });
  assert.equal(PH.Auth.destinoSeguro('planos-historicos.html'), 'planos-historicos.html');
  assert.equal(PH.Auth.destinoSeguro('Archivo_de_Planos_Históricos.html'), 'Archivo_de_Planos_Históricos.html');
  assert.equal(PH.Auth.destinoSeguro('https://evil.example'), 'planos-historicos.html');
  assert.equal(PH.Auth.destinoSeguro('//evil.example'), 'planos-historicos.html');

  assert.equal(PH.Auth.requireSession(), null);
  assert.equal(
    locationCalls.replace[0],
    'index.html?motivo=sesion_requerida&destino=Archivo_de_Planos_Hist%C3%B3ricos.html'
  );
});

test('integración API: operaciones envían el auditId del usuario autenticado', async () => {
  const calls = [];
  const doc = { id: 1, estado: 'pendiente', ia_estado: 'completado', procesamientos: [] };
  const { PH, context } = setupAuth({
    fetch: async (url, options) => {
      calls.push({ url, options });
      return { ok: true, json: async () => url.includes('/1') ? doc : [doc] };
    }
  });

  PH.Auth.login('operador', 'operador123', true);
  await PH.API.create(new Blob(['img']), '', '', '', {});
  assert.equal(calls[0].options.body.get('usuario_id'), 'lfernandez (Operador)');

  await PH.API.eliminar(5);
  assert.equal(calls[1].url, '/api/planos/5?usuario_id=lfernandez%20(Operador)');

  PH.Auth.login('validador', 'validador123', true);
  PH.CUValidar.seleccionar(1);
  await PH.CUValidar.renderDetalle();
  for (const [k, v] of Object.entries({ circunscripcion: '3', seccion: 'K', manzana: '12', parcela_catastral: '5' })) {
    context.document.getElementById('v-' + k).value = v;
  }
  await PH.CUValidar.confirmar();
  const validarCall = calls.find(c => c.url === '/api/planos/1/validar');
  assert.equal(JSON.parse(validarCall.options.body).usuario_id, 'msosa (Validador)');

  await PH.CUValidar.reintentar(1);
  const reintentoVal = calls.find(c => c.url.startsWith('/api/planos/1/reintentar_ia'));
  assert.equal(reintentoVal.url, '/api/planos/1/reintentar_ia?usuario_id=msosa%20(Validador)');

  PH.CUModificar.seleccionar(1);
  await PH.CUModificar.renderDetalle();
  for (const [k, v] of Object.entries({ circunscripcion: '3', seccion: 'K', manzana: '12', parcela_catastral: '5' })) {
    context.document.getElementById('m-' + k).value = v;
  }
  context.document.getElementById('m-motivo').value = 'Corrección de título';
  await PH.CUModificar.guardar();
  const modifCall = calls.find(c => c.url === '/api/planos/1/modificar');
  assert.equal(JSON.parse(modifCall.options.body).usuario_id, 'msosa (Validador)');
});

test('app: sin sesión redirige sin consultar la API; con rol consulta solo habilita Consultar', async () => {
  let fetches = 0;
  const sinSesion = setupAuth({
    loadApp: true,
    fetch: async () => { fetches++; return { ok: true, json: async () => [] }; }
  });
  sinSesion.PH.initApp();
  assert.equal(fetches, 0);
  assert.equal(sinSesion.locationCalls.replace.length, 1);
  assert.equal(sinSesion.body.classList.contains('auth-pending'), true);

  const fetchUrls = [];
  let pollFn;
  const conConsulta = setupAuth({
    loadApp: true,
    setInterval(fn) { pollFn = fn; return 1; },
    fetch: async (url) => { fetchUrls.push(url); return { ok: true, json: async () => [] }; }
  });
  conConsulta.PH.Auth.login('consulta', 'consulta123', true);
  conConsulta.PH.initApp();

  assert.equal(conConsulta.body.classList.contains('auth-pending'), false);
  assert.deepEqual(conConsulta.tabs.map(t => [t.dataset.tab, t.hidden]), [
    ['cargar', true],
    ['validar', true],
    ['modificar', true],
    ['consultar', false]
  ]);
  assert.equal(conConsulta.views.find(v => v.id === 'view-consultar').classList.contains('active'), true);
  assert.equal(conConsulta.views.find(v => v.id === 'view-cargar').classList.contains('active'), false);
  assert.ok(conConsulta.elements['user-session'].innerHTML.includes('Carolina Martínez'));
  assert.ok(conConsulta.elements['user-session'].innerHTML.includes('Usuario de Consulta'));

  const antesPoll = fetchUrls.length;
  pollFn();
  assert.equal(fetchUrls.length, antesPoll);
});

test('app: rol validador muestra validar, modificar y consultar; oculta cargar y arranca en validar', () => {
  const app = setupAuth({ loadApp: true });
  app.PH.Auth.login('validador', 'validador123', true);
  app.PH.initApp();

  assert.deepEqual(app.tabs.map(t => [t.dataset.tab, t.hidden]), [
    ['cargar', true],
    ['validar', false],
    ['modificar', false],
    ['consultar', false]
  ]);
  assert.equal(app.views.find(v => v.id === 'view-validar').classList.contains('active'), true);
  app.PH.goTab('cargar');
  assert.equal(app.views.find(v => v.id === 'view-cargar').classList.contains('active'), false);
});

test('login page: renderiza perfiles demo, completa credenciales y valida envío', () => {
  const { PH, context, elements, locationCalls } = setupAuth({
    files: ['auth'],
    search: '?motivo=sesion_requerida&destino=planos-historicos.html'
  });

  const demoList = context.document.getElementById('demo-users-list');
  const demoBtns = [
    { dataset: { demoUser: 'operador' }, addEventListener(ev, fn) { this._click = fn; } }
  ];
  demoList.querySelectorAll = () => demoBtns;

  PH.Auth.initLoginPage();
  assert.ok(elements['login-msgs'].innerHTML.includes('Iniciá sesión para acceder'));
  assert.ok(demoList.innerHTML.includes('Lucía Fernández'));
  assert.ok(demoList.innerHTML.includes('Martín Sosa'));
  assert.ok(demoList.innerHTML.includes('Carolina Martínez'));
  assert.ok(demoList.innerHTML.includes('Victoria Prieto'));

  demoBtns[0]._click();
  assert.equal(elements['login-usuario'].value, 'operador');
  assert.equal(elements['login-clave'].value, 'operador123');

  elements['login-clave'].value = 'erronea';
  elements['form-login'].dispatch('submit');
  assert.ok(elements['login-msgs'].innerHTML.includes('Usuario o contraseña incorrectos'));
  assert.equal(locationCalls.assign.length, 0);

  elements['login-clave'].value = 'operador123';
  elements['login-recordar'].checked = true;
  elements['form-login'].dispatch('submit');
  assert.equal(locationCalls.assign[0], 'planos-historicos.html');
  assert.equal(PH.Auth.getSession().rol, 'operador');
});

test('HTML: index.html no enlaza a Tramitar Nueva Obra y las páginas principales están sincronizadas', () => {
  const indexHtml = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
  assert.equal(/tramitar nueva obra/i.test(indexHtml), false);
  assert.equal(/pr[oó]ximamente/i.test(indexHtml), false);
  assert.ok(indexHtml.includes('id="form-login"'));
  assert.ok(indexHtml.includes('id="demo-users-list"'));
  assert.ok(indexHtml.includes('js/auth.js'));

  const planosHtml = fs.readFileSync(path.join(__dirname, '../planos-historicos.html'), 'utf8');
  const archivoHtml = fs.readFileSync(path.join(__dirname, '../Archivo_de_Planos_Históricos.html'), 'utf8');
  assert.equal(planosHtml, archivoHtml);
  assert.ok(planosHtml.includes('id="user-session"'));
  assert.ok(planosHtml.includes('src="js/auth.js"'));
});
