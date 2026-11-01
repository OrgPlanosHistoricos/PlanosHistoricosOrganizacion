const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup(fetch) {
  const elements = {};
  const context = vm.createContext({ window: { PH: {} }, fetch, URLSearchParams, FormData, SyntaxError,
    document: { getElementById(id) { return elements[id] ||= { innerHTML: '', value: '', files: [], reset() {}, addEventListener() {} }; } } });
  for (const file of ['state', 'nomenclatura', 'cu-cargar', 'cu-consultar', 'cu-modificar', 'cu-validar']) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../js/' + file + '.js'), 'utf8'), context);
  }
  return { PH: context.window.PH, elements, context };
}
const raw = '<script>secret stack trace SQL token</script>';
const operations = api => [
  () => api.getAll(), () => api.getById(1),
  () => api.create(new Blob(['image']), '', '', ''),
  () => api.validar(1, {}), () => api.modificar(1, {}), () => api.reintentarIA(1), () => api.eliminar(1)
];

for (const [name, fetch, expected] of [
  ['red', async () => { throw new TypeError(raw); }, 'red'],
  ['servidor', async () => ({ ok: false, status: 503, text() { throw Error('must not read body'); } }), 'servidor'],
  ['plano ausente', async () => ({ ok: false, status: 404 }), 'faltante'],
  ['respuesta inválida', async () => ({ ok: true, json: async () => { throw new SyntaxError(raw); } }), 'respuesta'],
  ['lectura interrumpida', async () => ({ ok: true, json: async () => { throw new TypeError(raw); } }), 'red']
]) {
  test(name + ': todas las operaciones dan mensajes seguros', async () => {
    const { PH } = setup(fetch);
    for (const [index, operation] of operations(PH.API).entries()) {
      const code = expected === 'faltante' && (index === 0 || index === 2) ? 'servidor' : expected;
      await assert.rejects(operation(), error => error.codigo === code && error.message === PH.Errores.mensajes[code]);
    }
  });
}
test('formato inválido, validación y reintento fallido', async () => {
  const { PH } = setup(async () => ({ ok: false, status: 400 }));
  for (const [operation, code] of [[operations(PH.API)[2], 'formato'], [operations(PH.API)[3], 'datos'], [operations(PH.API)[5], 'ia']]) {
    await assert.rejects(operation(), e => e.codigo === code);
  }
});
test('errores desconocidos nunca reutilizan message', () => {
  const { PH } = setup();
  assert.equal(PH.Errores.mensaje(new Error(raw)), PH.Errores.mensajes.inesperado);
  assert.equal(PH.Errores.mensaje({ codigo: 'inventado', message: raw }), PH.Errores.mensajes.inesperado);
});
test('las listas muestran errores de red sin texto técnico', async () => {
  const { PH, elements } = setup(async () => { throw Error(raw); });
  await PH.CUCargar.renderRecientes();
  await PH.CUConsultar.renderLista('3-K-12-5');
  await PH.CUModificar.renderLista();
  await PH.CUValidar.renderLista();
  for (const id of ['cargar-recientes', 'consultar-lista', 'modificar-lista', 'validar-lista']) {
    assert.ok(elements[id].innerHTML.includes(PH.Errores.mensajes.red));
    assert.ok(!elements[id].innerHTML.includes(raw));
  }
});
for (const ia_error of [raw, 'La respuesta no es JSON válido: ' + raw]) {
  test('detalle de IA oculta diagnóstico y no avisa por expediente opcional: ' + ia_error.slice(0, 12), async () => {
    const doc = { id: 1, estado: 'pendiente', ia_estado: 'error', ia_error, procesamientos: [], expediente: '' };
    const { PH, elements } = setup(async url => ({ ok: true, json: async () => url === '/api/planos/1' ? doc : [doc] }));
    PH.CUValidar.seleccionar(1);
    await PH.CUValidar.renderDetalle();
    const html = elements['validar-detalle'].innerHTML;
    assert.ok(!html.includes(raw));
    assert.ok(!html.includes('JSON'));
    assert.ok(html.includes('manualmente'));
    assert.ok(html.includes('Reintentar análisis'));
    assert.ok(!html.includes('Falta el expediente'));
  });
}
test('éxito preserva datos y opciones de envío', async () => {
  const calls = [];
  const { PH } = setup(async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => ({ id: 1 }) }; });
  for (const operation of operations(PH.API)) assert.equal((await operation()).id, 1);
  assert.equal(calls[2].options.method, 'POST');
  assert.equal(calls[3].options.method, 'PUT');
  assert.equal(calls[4].options.method, 'PUT');
  assert.equal(calls[5].options.method, 'POST');
  assert.equal(calls[6].options.method, 'DELETE');
});

test('eliminar: cancelar conserva el plano; confirmar envía DELETE y actualiza la cola', async () => {
  const calls = [];
  const { PH, context, elements } = setup(async (url, options) => {
    calls.push({url, options});
    return {ok:true, json:async () => options && options.method === 'DELETE' ? {eliminado:true} : []};
  });
  context.window.confirm = () => false;
  await PH.CUCargar.eliminar(7);
  assert.equal(calls.length, 0);
  context.window.confirm = () => true;
  const button = {disabled:false};
  await PH.CUCargar.eliminar(7, button);
  assert.equal(calls[0].url, '/api/planos/7');
  assert.equal(calls[0].options.method, 'DELETE');
  assert.equal(button.disabled, false);
  assert.ok(elements['cargar-msgs'].innerHTML.includes('eliminó correctamente'));
});
test('carga: rechaza extensión inválida y confirma sin avisos por expediente opcional', async () => {
  let submit;
  let calls = 0;
  const { PH, elements, context } = setup(async url => {
    calls++;
    return { ok: true, json: async () => url === '/api/planos' ? [] : {} };
  });
  context.document.getElementById('form-cargar').addEventListener = (_, handler) => { submit = handler; };
  PH.CUCargar.inicializar();
  context.document.getElementById('f-archivo').files = [{ name: 'plano.exe' }];
  submit({ preventDefault() {} });
  assert.equal(calls, 0);
  assert.ok(elements['cargar-msgs'].innerHTML.includes('JPG, PNG, WEBP o PDF'));
  const file = new Blob(['image']);
  file.name = 'plano.jpg';
  elements['f-archivo'].files = [file];
  for (const id of ['f-ubic', 'f-exp', 'f-dir']) context.document.getElementById(id);
  for (const [key,value] of Object.entries({circunscripcion:'3',seccion:'K',manzana:'12',parcela_catastral:'5'})) context.document.getElementById('f-'+key).value=value;
  submit({ preventDefault() {} });
  await new Promise(resolve => setImmediate(resolve));
  assert.ok(calls > 0);
  assert.ok(elements['cargar-msgs'].innerHTML.includes('se guardó correctamente'));
  assert.equal(elements['cargar-msgs'].innerHTML, '<div class="confirm">El plano se guardó correctamente</div>');
});
test('archivo demasiado grande: explica el límite sin mostrar la respuesta de nginx', async () => {
  const { PH } = setup(async () => ({ ok: false, status: 413, text() { throw Error('must not read body'); } }));
  await assert.rejects(operations(PH.API)[2](), error => {
    assert.equal(error.codigo, 'tamano');
    assert.ok(PH.Errores.mensaje(error).includes('20 MB'));
    return true;
  });
});
test('códigos heredados no se consideran mensajes de pantalla', () => {
  const { PH } = setup();
  assert.equal(PH.Errores.mensaje({ codigo: 'constructor' }), PH.Errores.mensajes.inesperado);
});
test('servidor sin ruta de carga: no confunde un servicio ausente con un plano faltante', async () => {
  for (const status of [404, 405]) {
    const { PH } = setup(async () => ({ ok: false, status }));
    await assert.rejects(PH.API.create(new Blob(['pdf']), '', '', ''), e => e.codigo === 'servidor');
  }
});
function completar(context, prefijo, datos = {circunscripcion:'03',seccion:'k',manzana:'012 a',parcela_catastral:'05 b'}) {
  for (const [key,value] of Object.entries(datos)) context.document.getElementById(prefijo+key).value=value;
}
test('nomenclatura: normaliza ceros, espacios y letras; permite vacíos y rechaza símbolos', () => {
  const { PH } = setup();
  const valid = {circunscripcion:'03',seccion:' k ',manzana:'012 a',parcela_catastral:'05 b'};
  assert.equal(PH.Nomenclatura.clave(PH.Nomenclatura.normalizar(valid)), '3-K-12A-5B');
  for (const key of Object.keys(valid)) {
    for (const value of ['???', '<script>']) assert.throws(() => PH.Nomenclatura.normalizar({...valid,[key]:value}), e=> e.codigo === 'nomenclatura');
  }
  for (const key of ['circunscripcion','manzana','parcela_catastral']) assert.throws(() => PH.Nomenclatura.normalizar({...valid,[key]:'0'}));
});
test('carga: nomenclatura inválida no hace solicitudes y conserva el archivo', async () => {
  let calls = 0, submit;
  const { PH, context, elements } = setup(async () => { calls++; });
  context.document.getElementById('form-cargar').addEventListener=(_,handler)=>{submit=handler;};
  PH.CUCargar.inicializar();
  context.document.getElementById('f-circunscripcion').value='???';
  const file={name:'plano.pdf'};
  context.document.getElementById('f-archivo').files=[file];
  submit({preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls,0);
  assert.ok(elements['cargar-msgs'].innerHTML.includes(PH.Errores.mensajes.nomenclatura));
  assert.equal(elements['f-archivo'].files[0],file);
});
test('consulta: lista cinco planos, pagina y filtra en vivo por componentes catastrales', async () => {
  const calls = [];
  const docs = Array.from({ length: 12 }, (_, i) => ({ id: i + 1, estado: 'validado', circunscripcion: i < 7 ? '3' : '4', seccion: 'K', manzana: String(i + 1), parcela_catastral: '5B' }));
  docs.push({ id: 99, estado: 'pendiente', circunscripcion: '3' });
  let input;
  const { PH, context, elements } = setup(async url => { calls.push(url); return { ok: true, json: async () => docs }; });
  context.document.getElementById('form-consultar').addEventListener = (event, handler) => { if (event === 'input') input = handler; };
  PH.CUConsultar.inicializar();
  await PH.CUConsultar.renderLista();
  assert.equal((elements['consultar-lista'].innerHTML.match(/class="row/g) || []).length, 5);
  assert.ok(elements['consultar-paginacion'].innerHTML.includes('1–5 de 12'));
  PH.CUConsultar.cambiarPagina(1);
  assert.ok(elements['consultar-lista'].innerHTML.includes('seleccionar(6)'));
  assert.ok(elements['consultar-paginacion'].innerHTML.includes('6–10 de 12'));
  PH.CUConsultar.cambiarPagina(1);
  assert.equal((elements['consultar-lista'].innerHTML.match(/class="row/g) || []).length, 2);
  assert.ok(elements['consultar-paginacion'].innerHTML.includes('11–12 de 12'));
  completar(context, 'c-', { circunscripcion: '03' });
  input();
  assert.ok(elements['consultar-paginacion'].innerHTML.includes('1–5 de 7'));
  completar(context, 'c-', { manzana: '01' });
  input();
  assert.equal((elements['consultar-lista'].innerHTML.match(/class="row/g) || []).length, 1);
  assert.ok(elements['consultar-lista'].innerHTML.includes('seleccionar(1)'));
  completar(context, 'c-', { seccion: 'z' });
  input();
  assert.ok(elements['consultar-lista'].innerHTML.includes('No se encontraron'));
  assert.equal(elements['consultar-paginacion'].innerHTML, '');
  completar(context, 'c-', { circunscripcion: '', seccion: '', manzana: '', parcela_catastral: '' });
  input();
  assert.ok(elements['consultar-paginacion'].innerHTML.includes('1–5 de 12'));
  assert.deepEqual(calls, ['/api/planos']);
});
test('API: envía los cuatro campos de carga y conserva los opcionales vacíos', async () => {
  let body;
  const {PH}=setup(async (_,options)=>{body=options.body;return {ok:true,json:async()=>({id:1})};});
  const datos={circunscripcion:'3',seccion:'K',manzana:'12A',parcela_catastral:'5B'};
  await PH.API.create(new Blob(['pdf']),'','','',datos);
  for(const [key,value] of Object.entries(datos)) assert.equal(body.get(key),value);
  assert.equal(body.get('expediente'),'');
});
test('API: códigos acordados explican duplicados y nomenclatura sin mostrar texto recibido', async () => {
  for(const [status,detail,expected] of [
    [409,{codigo:'duplicado'},'duplicado'],
    [409,{codigo:'procesando_ia'},'procesando_ia'],
    [422,{codigo:'nomenclatura'},'nomenclatura'],
    [422,[{loc:['body','seccion'],msg:raw}],'nomenclatura'],
    [409,{codigo:raw},'inesperado']
  ]) {
    const {PH}=setup(async()=>({ok:false,status,json:async()=>({detail})}));
    await assert.rejects(PH.API.create(new Blob(['pdf']),'','',''),e=>e.codigo===expected && !PH.Errores.mensaje(e).includes(raw));
  }
});
test('carga: bloquea subida si ya hay un plano en estado procesando', async () => {
  let submit;
  let postCalls = 0;
  const { PH, context, elements } = setup(async (url, options) => {
    if (options && options.method === 'POST') postCalls++;
    return {
      ok: true,
      json: async () => [{ id: 10, estado: 'pendiente', ia_estado: 'procesando', nombre_original: 'uno.jpg' }]
    };
  });
  context.document.getElementById('form-cargar').addEventListener = (_, handler) => { submit = handler; };
  context.document.getElementById('btn-cargar');
  PH.CUCargar.inicializar();
  await PH.CUCargar.renderRecientes();
  assert.equal(elements['btn-cargar'].disabled, true);

  const file = new Blob(['image']);
  file.name = 'plano2.jpg';
  context.document.getElementById('f-archivo').files = [file];
  completar(context, 'f-');
  submit({ preventDefault() {} });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(postCalls, 0);
  assert.ok(elements['cargar-msgs'].innerHTML.includes(PH.Errores.mensajes.procesando_ia));
});
test('revisión y modificación: envían nomenclatura normalizada y bloquean datos inválidos', async () => {
  for(const [module,prefix,select,save] of [['CUValidar','v-','seleccionar','confirmar'],['CUModificar','m-','seleccionar','guardar']]) {
    const calls=[];
    const doc={id:1,estado:'pendiente',ia_estado:'error',procesamientos:[]};
    const {PH,context}=setup(async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>url.includes('/1')?doc:[]};});
    PH[module][select](1);
    await new Promise(resolve=>setImmediate(resolve));
    assert.match(context.document.getElementById(prefix === 'v-' ? 'validar-detalle' : 'modificar-detalle').innerHTML,
      new RegExp('<textarea id="' + prefix + 'texto_extraido"[^>]* readonly>'));
    for(const key of ['texto_extraido','titulo','arquitecto','ubicacion','anio','escala','tipo_de_plano','material_soporte','notas']) context.document.getElementById(prefix+key);
    if(prefix==='m-') context.document.getElementById('m-motivo').value='Corrección';
    context.document.getElementById(prefix+'seccion').value='???';
    await PH[module][save]();
    assert.equal(calls.filter(c=>c.options?.method==='PUT').length,0);
    completar(context,prefix);
    await PH[module][save]();
    const put=calls.find(c=>c.options?.method==='PUT');
    assert.ok(put);
    assert.equal(Object.hasOwn(JSON.parse(put.options.body), 'texto_extraido'), false);
    assert.equal(JSON.parse(put.options.body).manzana,'12A');
    assert.equal(JSON.parse(put.options.body).parcela_catastral,'5B');
  }
});

test('max_intentos: reintentar_ia explica límite sin texto técnico', async () => {
  const { PH } = setup(async () => ({ ok: false, status: 400, json: async () => ({ detail: { codigo: 'max_intentos' } }) }));
  await assert.rejects(PH.API.reintentarIA(1), e => e.codigo === 'max_intentos' && e.message === PH.Errores.mensajes.max_intentos);
});

test('modificar catalogación: propuesta de IA renderiza banner y tabla de antes y después', async () => {
  const doc = {
    id: 1,
    estado: 'validado',
    ia_estado: 'completado',
    titulo: 'Original',
    ia_propuesta: JSON.stringify({ titulo: 'Propuesto por IA' }),
    procesamientos: [{ intento: 1, estado: 'completado' }],
    eventos: []
  };
  const { PH, context } = setup(async url => ({ ok: true, json: async () => url.includes('/1') ? doc : [doc] }));
  PH.CUModificar.seleccionar(1);
  await new Promise(resolve => setImmediate(resolve));
  const html = context.document.getElementById('modificar-detalle').innerHTML;
  assert.ok(html.includes('Hay una nueva propuesta de la IA disponible'));
  assert.ok(html.includes('Ver Antes y Después'));
  assert.ok(html.includes('Descartar propuesta'));

  PH.CUModificar.abrirComparacion();
  const modalHtml = context.document.getElementById('m-modal-comparacion').innerHTML;
  assert.ok(modalHtml.includes('Original'));
  assert.ok(modalHtml.includes('Propuesto por IA'));
  assert.ok(modalHtml.includes('>Aplicar cambios</button>'));
  assert.ok(modalHtml.includes('<th>Estado</th><th>Aplicar</th>'));
  assert.ok(modalHtml.includes('id="m-aplicar-titulo" checked'));
  const titulo = context.document.getElementById('m-titulo');
  titulo.value = 'Original';
  const seleccion = context.document.getElementById('m-aplicar-titulo');
  seleccion.checked = false;
  PH.CUModificar.aplicarPropuesta();
  assert.equal(titulo.value, 'Original');
  seleccion.checked = true;
  PH.CUModificar.aplicarPropuesta();
  assert.equal(titulo.value, 'Propuesto por IA');
});

test('historial: usa eventos, ordena por instante y muestra cambios escapados', async () => {
  const doc = { id: 1, estado: 'validado', ia_estado: 'completado', eventos: [
    { id: 1, fecha: '2026-11-01T10:00:00Z', usuario_id: 'ana', motivo: 'Primero', valores_anteriores: null, valores_nuevos: null },
    { id: 2, fecha: '2026-11-01T11:00:00Z', usuario_id: '<usuario>', motivo: 'Segundo', valores_anteriores: JSON.stringify({ titulo: 'Antes', anio: 1930 }), valores_nuevos: JSON.stringify({ titulo: '<Nuevo>', anio: 1930 }) }
  ] };
  const { PH, elements } = setup(async url => ({ ok: true, json: async () => url === '/api/planos/1' ? doc : [doc] }));
  PH.CUModificar.seleccionar(1);
  await PH.CUModificar.renderDetalle();
  const html = elements['modificar-detalle'].innerHTML;
  const table = html.slice(html.indexOf('<table class="hist-table">'), html.indexOf('</table>') + 8);
  assert.ok(table.includes('Fecha') && table.includes('Hora') && table.includes('Usuario'));
  assert.ok(table.indexOf('Segundo') < table.indexOf('Primero'));
  assert.ok(table.includes('&lt;usuario&gt;') && table.includes('&lt;Nuevo&gt;') && table.includes('Antes'));
  assert.ok(!table.includes('1930'));
});

test('escala: acepta relaciones positivas y casos especiales; rechaza texto arbitrario', () => {
  const { PH } = setup();
  for (const valor of [null, '', '1:100', ' 1 : 50 ', '2:1', '1:2,5', 'Sin escala', 'Escalas varias']) {
    assert.equal(PH.validarEscala(valor), true, String(valor));
  }
  for (const valor of ['CHINO', '0:100', '1:0', '-1:100', '1:100 basura']) {
    assert.equal(PH.validarEscala(valor), false, valor);
  }
});

test('escala: normaliza null real, literal y vacío antes de validar', () => {
  const { PH } = setup();
  for (const valor of [null, undefined, '', '   ', 'null', ' NULL ']) {
    assert.equal(PH.normalizarEscala(valor), null);
    assert.equal(PH.validarEscala(valor), true);
  }
  assert.equal(PH.normalizarEscala(' 1:100 '), '1:100');
  assert.equal(PH.validarEscala('CHINO'), false);
});

test('historial: no muestra escala cuando solo cambia null literal por vacío', async () => {
  const doc = { id: 1, estado: 'validado', ia_estado: 'completado', eventos: [
    { id: 1, fecha: '2026-11-01T17:39:23Z', motivo: 'Corregir año', valores_anteriores: JSON.stringify({ anio: null, escala: 'null' }), valores_nuevos: JSON.stringify({ anio: 1999, escala: null }) }
  ] };
  const { PH, elements } = setup(async url => ({ ok: true, json: async () => url === '/api/planos/1' ? doc : [doc] }));
  PH.CUModificar.seleccionar(1);
  await PH.CUModificar.renderDetalle();
  const html = elements['modificar-detalle'].innerHTML;
  const table = html.slice(html.indexOf('<table class="hist-table">'), html.indexOf('</table>') + 8);
  assert.ok(table.includes('Año') && table.includes('1999'));
  assert.ok(!table.includes('Escala'));
});

test('nomenclatura opcional: acepta vacíos y parciales; exige formato solo si hay contenido', () => {
  const { PH } = setup();
  const vacia = PH.Nomenclatura.normalizar({});
  assert.ok(Object.values(vacia).every(v => v === ''));
  const parcial = PH.Nomenclatura.normalizar({ circunscripcion: '03', manzana: '012 a' });
  assert.equal(parcial.circunscripcion, '3');
  assert.equal(parcial.manzana, '12A');
  assert.equal(parcial.seccion, '');
  assert.ok(!PH.Nomenclatura.formulario('f-').includes(' required '));
  assert.ok(PH.Nomenclatura.formulario('c-', null, true).includes('required'));
  assert.throws(() => PH.Nomenclatura.normalizar({}, true));
});

test('carga: permite guardar un plano sin nomenclatura', async () => {
  let submit, body;
  const { PH, context } = setup(async (url, options) => {
    if (options?.method === 'POST') body = options.body;
    return { ok: true, json: async () => options?.method === 'POST' ? { id: 1 } : [] };
  });
  context.document.getElementById('form-cargar').addEventListener = (_, handler) => { submit = handler; };
  PH.CUCargar.inicializar();
  const archivo = new Blob(['imagen']);
  archivo.name = 'plano.jpg';
  context.document.getElementById('f-archivo').files = [archivo];
  submit({ preventDefault() {} });
  await new Promise(resolve => setImmediate(resolve));
  assert.ok(body);
  for (const key of ['circunscripcion', 'seccion', 'manzana', 'parcela_catastral']) assert.equal(body.get(key), '');
});

test('consulta: filtros de calle, altura, expediente, año y parcela se combinan', async () => {
  const docs = [
    { id: 1, estado: 'validado', direccion_referencia: 'San Martín 620', expediente: 'EXP-1936-045', anio: 1936, parcela_catastral: '5B' },
    { id: 2, estado: 'validado', direccion_referencia: 'San Martin 6200', expediente: 'EXP-1936-046', anio: 1936, parcela_catastral: '5B' },
    { id: 3, estado: 'validado', direccion_referencia: 'Calle 47 N.º 620', expediente: 'EXP-2000', anio: 2000, parcela_catastral: '2' },
    { id: 4, estado: 'validado', ubicacion: 'Belgrano 620', anio: null },
    { id: 5, estado: 'validado', direccion_referencia: 'Calle 47', anio: 1947 },
    { id: 6, estado: 'pendiente', direccion_referencia: 'San Martín 620', anio: 1936 }
  ];
  const { PH, context, elements } = setup(async () => ({ ok: true, json: async () => docs }));
  PH.CUConsultar.inicializar();
  await PH.CUConsultar.renderLista();
  const ids = () => [...elements['consultar-lista'].innerHTML.matchAll(/seleccionar\((\d+)\)/g)].map(m => Number(m[1]));
  completar(context, 'c-', { calle: 'san martin' });
  PH.CUConsultar.buscar();
  assert.deepEqual(ids(), [1, 2]);
  completar(context, 'c-', { numero: '00620', expediente: '1936-045', anio: '193', parcela_catastral: '5b' });
  PH.CUConsultar.buscar();
  assert.deepEqual(ids(), [1]);
  completar(context, 'c-', { calle: '', numero: '', expediente: '', anio: '', parcela_catastral: '' });
  completar(context, 'c-', { calle: 'calle 47', numero: '620' });
  PH.CUConsultar.buscar();
  assert.deepEqual(ids(), [3]);
  completar(context, 'c-', { calle: 'belgrano' });
  PH.CUConsultar.buscar();
  assert.deepEqual(ids(), [4]);
  completar(context, 'c-', { calle: 'calle 47', numero: '47' });
  PH.CUConsultar.buscar();
  assert.deepEqual(ids(), []);
  assert.ok(elements['consultar-lista'].innerHTML.includes('criterios de búsqueda'));
  completar(context, 'c-', { calle: '', numero: '', anio: 'null' });
  PH.CUConsultar.buscar();
  assert.deepEqual(ids(), []);
});
