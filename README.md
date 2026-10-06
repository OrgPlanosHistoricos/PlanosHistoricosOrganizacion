# API de Reconocimiento de Planos Históricos

Extrae datos (arquitecto, año, ubicación, etc.) de planos históricos
escaneados usando el modelo de visión Qwen2.5-VL 3B servido por Ollama,
y los devuelve en JSON estructurado.

## Uso

```bash
docker compose up -d
```

La API espera hasta 300 segundos por la respuesta de Ollama, ya que la
inferencia puede tardar más cuando se ejecuta con CPU. Este valor se puede
ajustar mediante la variable `OLLAMA_TIMEOUT`.

La primera vez, el servicio `ollama-pull` descarga el modelo
(~2-3 GB) automáticamente. Puede tardar varios minutos según tu
conexión. Podés seguir el progreso con:

```bash
docker compose logs -f ollama-pull
```

Una vez levantado todo:

### Modo asíncrono (predeterminado y recomendado para la app web):
```bash
curl -X POST http://localhost:8000/procesar-plano \
  -F "archivo=@/ruta/a/tu/plano.jpg"
```

Respuesta inmediata (HTTP 202 Accepted):
```json
{
  "task_id": "e1c97abb-85b4-4ab3-ba57-86858af023da",
  "status": "pending",
  "mensaje": "Plano recibido. El procesamiento con IA se está ejecutando en segundo plano."
}
```

Consultar estado y resultado de la tarea:
```bash
curl http://localhost:8000/tareas/e1c97abb-85b4-4ab3-ba57-86858af023da
```

Respuesta cuando finaliza (`status: "completed"`):
```json
{
  "task_id": "e1c97abb-85b4-4ab3-ba57-86858af023da",
  "status": "completed",
  "filename": "plano.jpg",
  "resultado": {
    "arquitecto": "Francisco Salamone",
    "anio": 1936,
    "titulo": "Palacio Municipal de Azul",
    "ubicacion": "Azul, Buenos Aires",
    "escala": "1:50",
    "tipo_de_plano": "fachada principal",
    "material_soporte": "papel tela",
    "notas": null
  },
  "error": null,
  "supabase_url": "https://<proyecto>.supabase.co/storage/v1/object/public/planos_escaneados/<uuid>.jpg"
}
```

## Funcionamiento del Procesamiento con IA (Pipeline en 2 Pasos con Grounding)

El procesamiento de planos combina las normas de dibujo técnico (**IRAM 4504** en Argentina e **ISO 7200** a nivel internacional) con las capacidades de **Grounding y Detección de Objetos** del modelo **Qwen2.5-VL 3B**.

### El desafío en planos de gran formato
Los planos arquitectónicos digitalizados suelen tener resoluciones gigantescas (ej. 4000×3000 px o más). Si se envía el plano completo comprimido a 1600 px a un modelo de visión, los textos críticos (año, cotas, firmas a mano, escalas y nomenclatura catastral) quedan reducidos a un puñado de píxeles borrosos e ilegibles.

Por norma técnica, la información legal, catastral y de autoría se concentra siempre en el **cajetín, carimbo o rótulo**, ubicado reglamentariamente en la **esquina inferior derecha**. Por eso, el sistema no analiza todo el plano de una sola vez: divide la tarea en **dos pasos estratégicos**.

```
[ Plano Original en Alta Resolución ]
                  │
                  ▼
 1. Preprocesamiento liviano (preview ~1600px)
                  │
                  ▼
 2. Paso 1: Grounding con Qwen2.5-VL ─────► {"bbox_2d": [ymin, xmin, ymax, xmax]}
                  │                         (Fallback: Cuadrante inferior derecho IRAM)
                  ▼
 3. Recorte HD sobre imagen ORIGINAL con margen de seguridad (Padding 2%)
                  │
                  ▼
 4. Mejora de contraste y nitidez (Pillow: autocontrast + sharpness)
                  │
                  ▼
 5. Paso 2: Inferencia de extracción con Qwen2.5-VL ──► JSON estructurado (PlanoHistorico)
```

---

### Paso 1: Detección y Grounding del Cajetín

Se genera una vista previa optimizada del plano para no sobrecargar la memoria de la GPU ni dilatar el tiempo de inferencia, y se le pide al modelo que localice la caja delimitadora (**Bounding Box**) del cuadro técnico.

- **Prompt utilizado en el Paso 1:**
  ```text
  Detecta el cajetín, carimbo o cuadro de datos técnicos del plano.
  Devuelve únicamente un JSON con la bounding box en formato [ymin, xmin, ymax, xmax] normalizado de 0 a 1000.
  Por normas técnicas IRAM e ISO, el cajetín suele encontrarse en la zona inferior derecha del plano.
  Ejemplo de respuesta: {"bbox_2d": [750, 700, 990, 990]}
  ```

- **Structured Output:** Se fuerza mediante Ollama (`format: CajetinBBoxSchema.model_json_schema()`) asegurando que la salida sea un JSON estrictamente tipado.
- **Validación y Fallback IRAM:** El sistema valida que las coordenadas cumplan `0 <= ymin < ymax <= 1000` y `0 <= xmin < xmax <= 1000`. Si la detección falla, el modelo no responde o la caja es anómala, se activa automáticamente el **fallback por norma técnica IRAM 4504** (`[600, 500, 1000, 1000]`), garantizando que la tubería nunca se interrumpa.

---

### Recorte en Alta Resolución (Crop & Preprocesamiento)

Implementado en `api/preprocessing.py` con la función `crop_cajetin_from_bbox`:

1. **Desnormalización:** Las coordenadas `[0..1000]` se convierten a píxeles exactos de la **imagen original sin comprimir**.
2. **Margen de seguridad (*Padding*):** Se expande la caja un 2% en ancho y alto para evitar cortar palabras o sellos que rocen los márgenes del cajetín.
3. **Optimización con Pillow (`preprocess_cajetin`):**
   - **Autocontraste:** Recupera trazos en tinta descolorida o papel amarillento (`ImageOps.autocontrast`).
   - **Realce de nitidez:** Aplica un filtro de nitidez (`ImageEnhance.Sharpness.enhance(1.5)`) para destacar tipografías pequeñas, números catastrales y firmas caligráficas.

---

### Paso 2: Extracción Estructurada de Datos Técnicos en HD

Se envía **únicamente el recorte del cajetín en máxima resolución** a Qwen2.5-VL con el esquema JSON completo de `PlanoHistorico` (`api/schemas.py`). Al tener solo el rótulo en primer plano, el modelo dispone del 100% de su capacidad atencional y de resolución óptica en el texto que importa.

- **Prompt utilizado en el Paso 2:**
  ```text
  Respondé únicamente con el objeto JSON solicitado, sin explicaciones ni razonamiento.
  Analizá este recorte en alta resolución del cajetín / carimbo / rótulo de datos técnicos del plano histórico y respondé en español basándote solo en lo visible.

  Completá estos campos:
  - texto_extraido: transcripción fiel y completa de todo el texto legible visible en este cajetín (rótulos, firmas, sellos, datos catastrales, fechas, notas y escalas).
  - arquitecto: autor o proyectista (arquitecto, ingeniero o profesional firmante), sin el título profesional.
  - anio: año del plano o proyecto como número de cuatro dígitos (ej. 1936).
  - titulo: obra, edificio, proyecto o descripción de la vista.
  - ubicacion: datos de ubicación o catastrales (ciudad, dirección, circunscripción, sección, manzana, parcela).
  - escala: escala indicada en el rótulo (ej. 1:100, 1:50).
  - tipo_de_plano: planta, corte, fachada, relevamiento, detalle, etc.
  - material_soporte: solo si aparece escrito en el plano, no lo deduzcas.
  - notas: números de expediente, sellos municipales, aprobaciones o datos técnicos que no encajen en otro campo.

  Transcribí fielmente. No inventes ni corrijas datos. Usá null si un dato no aparece o es ilegible. Devolvé JSON válido y ningún texto fuera del JSON.
  ```

- **Campos del Esquema Resultante (`PlanoHistorico`):**
  - `texto_extraido`: Transcripción integral de texto (OCR del cajetín).
  - `arquitecto`: Nombre del proyectista o profesional firmante.
  - `anio`: Año de confección o visado (4 dígitos).
  - `titulo`: Nombre de la obra, proyecto o designación de la lámina.
  - `ubicacion`: Localidad, calle o nomenclatura catastral.
  - `escala`: Relación de escala métrica (ej. `1:100`).
  - `tipo_de_plano`: Tipología gráfica (planta, corte, fachada, etc.).
  - `material_soporte`: Sustrato indicado explícitamente (papel vegetal, tela, etc.).
  - `notas`: Referencias a expedientes, números de archivo o sellos.

---

### Resiliencia y Manejo de Errores

- **Reintentos automáticos:** Tanto `tasks.py` como `planos_worker.py` ejecutan reintentos automáticos si la llamada al modelo no responde en el primer intento.
- **Doble Fallback:** Si por algún caso extremo la extracción sobre el recorte del cajetín fallase, el sistema reintenta la extracción sobre el plano completo para no dejar la petición en error.
- **Concurrencia no bloqueante:** Toda la inferencia pesada corre en hilos separados (`asyncio.to_thread`) para mantener ágil el event loop de FastAPI.

---

## Almacenamiento: Supabase + MongoDB

_Agregado: 2026-09-29_

Cada plano procesado (tanto en modo asíncrono como con `?sync=true`)
se persiste en dos lugares:


- **Supabase Storage** (bucket `planos_escaneados`): guarda el archivo
  original que subió el usuario y expone su URL pública (`supabase_url`
  en la respuesta de `/tareas/{task_id}`).
- **MongoDB** (base `planos_db`, colección `extracciones`): guarda el
  documento completo (fecha de procesamiento, datos del archivo y la
  extracción de Qwen) con el esquema `DocumentoExtraccion`
  (`api/schemas.py`).

Esta lógica vive en `api/tasks.py` (función `_guardar_extraccion`),
que se llama tanto desde el worker asíncrono como desde
`procesar_directo` (modo `sync`), después de que Qwen devuelve el
resultado. La subida a Supabase usa `api/storage_client.py` y el
insert a Mongo usa `api/db_client.py`.

### Variables de entorno

Están en `.env` (no se commitea, ver `.env.example`):

```
MONGODB_URI=mongodb+srv://usuario:password@cluster.mongodb.net/?appName=...
SUPABASE_URL=https://<proyecto>.supabase.co
SUPABASE_KEY=<service_role key>
```

`docker-compose.yml` las toma del `.env` de la raíz y se las pasa al
contenedor `api`.

**Importante sobre `SUPABASE_KEY`**: tiene que ser la **service_role
key** (Supabase Dashboard → Settings → API), no la `anon`/`publishable`.
El bucket tiene Row Level Security activado, así que la key anónima no
tiene permiso de `INSERT` y el upload falla con
`403 new row violates row-level security policy`. La service_role
bypasea RLS y nunca se expone al frontend - solo la usa este backend.

**Importante sobre `MONGODB_URI`**: la IP desde la que corre la API
tiene que estar en la whitelist de Atlas (Network Access → Add IP
Address). Si no, las operaciones se cuelgan con
`ServerSelectionTimeoutError`.

## Catálogo: PostgreSQL + MinIO (Fase 2)

_Agregado: 2026-09-29_

El catálogo de planos (datos de origen, estado de validación e
historial) se guarda en **PostgreSQL**, y los archivos originales en
**MinIO** (bucket `planos`). Ambos corren como servicios del
`docker-compose.yml`: no hace falta crear cuentas ni instalar nada,
las tablas se crean solas al arrancar la API.

Variables en `.env` (ver `.env.example`; si no están, se usan esos
mismos valores por defecto):

```
POSTGRES_USER=planos
POSTGRES_PASSWORD=planos
POSTGRES_DB=planos_db
```

Postgres queda expuesto en `localhost:5432` para inspeccionarlo con
cualquier cliente (DBeaver, pgAdmin, `psql`), y la consola de MinIO en
http://localhost:9001.

### Tablas

- **`planos`**: archivo (`nombre_original`, `content_type`,
  `minio_path`), datos de origen (`ubicacion_fisica`, `expediente`,
  `direccion_referencia`, `parcela`), `estado` (`pendiente` |
  `validado` | `sin_ubicacion`), estado de la IA (`ia_estado`:
  `procesando` | `completado` | `error` | `no_aplica`, más `ia_error`),
  los metadatos del plano (`arquitecto`, `anio`, `titulo`, `ubicacion`,
  `escala`, `tipo_de_plano`, `material_soporte`, `notas`) y fechas de
  creación/actualización.
- **`historial_modificaciones`**: `plano_id` (FK), `fecha`, `motivo`.

### Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/planos` | Multipart: `archivo` + `ubicacion_fisica`, `expediente`, `direccion_referencia` (opcionales). Sube a MinIO, crea el plano como `pendiente` y, si es imagen, dispara la IA en segundo plano (`ia_estado=procesando`). Los PDF quedan con `ia_estado=no_aplica`. |
| `GET` | `/planos` | Lista. Filtros: `estado` (repetible: `?estado=validado&estado=sin_ubicacion`) y `q` (busca en dirección, parcela, expediente, ubicación física, arquitecto, título, ubicación y año). |
| `GET` | `/planos/{id}` | Detalle con historial. Sirve para consultar si la IA terminó (`ia_estado`). |
| `GET` | `/planos/{id}/archivo` | Devuelve el archivo original. |
| `PUT` | `/planos/{id}/validar` | JSON con los metadatos revisados + `parcela`. Queda `validado` si hay parcela, si no `sin_ubicacion`. Agrega "Validación inicial" al historial. Devuelve 409 si el plano ya fue validado. |
| `PUT` | `/planos/{id}/modificar` | JSON con los metadatos + `parcela` + `motivo` (obligatorio, 400 si falta). Actualiza el plano y agrega el motivo al historial. |

Ejemplo:

```bash
curl -X POST http://localhost:8000/planos \
  -F "archivo=@plano.jpg" -F "expediente=EXP-1936-045" \
  -F "ubicacion_fisica=Estante 3, caja 12"

curl -X PUT http://localhost:8000/planos/1/modificar \
  -H "Content-Type: application/json" \
  -d '{"arquitecto": "Francisco Salamone", "anio": 1936, "parcela": "Lote 4", "motivo": "Corrección de año"}'
```

Detalles de comportamiento:

- `validar` y `modificar` reemplazan **todos** los metadatos: un campo
  que no se manda queda en `null` (igual que el formulario del front,
  que siempre manda el objeto completo). `anio` acepta `""` como `null`.
- Si una persona valida un plano mientras la IA todavía lo procesa, el
  resultado de la IA no pisa los datos cargados a mano.
- Si la API se reinicia con planos en `procesando`, los vuelve a
  encolar al arrancar.
- Esto convive con `/procesar-plano` y `/tareas` (y su persistencia en
  Supabase/MongoDB), que siguen funcionando igual.

## Notas

- El esquema de campos a extraer está en `app/schemas.py` (Pydantic).
  Agregá o quitá campos ahí y se propagan automáticamente al modelo.
- Sin GPU, cada plano puede tardar entre 20 y 90 segundos según
  resolución. Con GPU (ver comentario en `docker-compose.yml`) baja
  drásticamente.
- `app/preprocessing.py` redimensiona y mejora el contraste de la
  imagen antes de mandarla al modelo - ajustá `MAX_DIMENSION` si tus
  planos tienen mucho detalle fino.
# planosHistoricos
# planosHistoricos
# planosHistoricos

IMPORTANTE
Se debe desacargar un modelo en ollama (configurado actualmente qwen2.5vl:3b) se peude consultar el estado de la descarga en cualquier momento con:

```bash
docker exec -it ollama ollama list
```

el ingreso a la app debe hacerse desde http://localhost:8080 en el navegador. Sino se bloquea el uso de la API de reconocimiento de imagenes.
Los formatos admitidos actualmente son solamente JPEG, PNG .... NO PDF!!!

El procesamiento por CPU tarda de 60 a 90 segundos.

.
