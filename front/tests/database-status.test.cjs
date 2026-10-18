const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup(fetch) {
  const indicator = { dataset: {} };
  const label = { textContent: '' };
  let check;
  const context = vm.createContext({
    fetch, AbortController, setTimeout, clearTimeout,
    setInterval(fn, delay) { assert.equal(delay, 15000); check = fn; },
    window: { addEventListener() {} },
    document: {
      readyState: 'complete',
      getElementById(id) { return id === 'database-status' ? indicator : label; }
    }
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../js/database-status.js'), 'utf8'), context);
  return { indicator, label, check: () => check(), settle: () => new Promise(resolve => setImmediate(resolve)) };
}

test('conexión, caída y recuperación actualizan el indicador', async () => {
  let connected = true;
  const app = setup(async (url, options) => {
    assert.equal(url, '/api/health/database');
    assert.equal(options.cache, 'no-store');
    return { ok: connected, status: connected ? 200 : 503,
      json: async () => ({ database: connected ? 'connected' : 'disconnected' }) };
  });
  await app.settle();
  assert.equal(app.indicator.dataset.state, 'connected');
  connected = false;
  await app.check();
  assert.equal(app.indicator.dataset.state, 'disconnected');
  connected = true;
  await app.check();
  assert.equal(app.indicator.dataset.state, 'connected');
});

for (const [name, fetch] of [
  ['red', async () => { throw Error('secret'); }],
  ['502 HTML', async () => ({ ok: false, status: 502, json: async () => { throw SyntaxError('nginx'); } })],
  ['respuesta inesperada', async () => ({ ok: true, status: 200, json: async () => ({}) })]
]) {
  test(name + ' muestra estado desconocido sin diagnóstico interno', async () => {
    const app = setup(fetch);
    await app.settle();
    assert.equal(app.indicator.dataset.state, 'unknown');
    assert.equal(app.label.textContent, 'No se pudo verificar la base de datos');
  });
}
