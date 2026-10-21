# API de Reconocimiento de Planos Históricos

Extrae datos (arquitecto, año, ubicación, etc.) de planos históricos
escaneados usando el modelo de visión Qwen2.5-VL 3B servido por Ollama,
y los devuelve en JSON estructurado.

## Uso

Para levantar el entorno local (PostgreSQL, MinIO, API y Frontend) usando Google Colab como motor de IA:

```bash
docker compose up -d
```

> **Nota sobre Ollama local:** Los contenedores locales `ollama` y `ollama-pull` están bajo el perfil opcional `local-ai`, por lo que `docker compose up -d` **no los levanta ni descarga modelos localmente**. Si en algún momento querés correr Ollama localmente en Docker en lugar de usar Google Colab, ejecutá:
> ```bash
> docker compose --profile local-ai up -d
> ```
> y podés seguir la descarga inicial con `docker compose logs -f ollama-pull`.

La API espera hasta 300 segundos por la respuesta de Ollama (ajustable mediante la variable `OLLAMA_TIMEOUT`).

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

---

## Estructura del Backend

El backend sigue una arquitectura organizada por recursos y capas (`routes → controllers → services → models`), manteniendo separada la infraestructura compartida de la lógica de cada dominio.

```text
backend/
├── Dockerfile
├── requirements.txt
├── tests/
│   ├── test_health.py
│   ├── test_nomenclatura.py
│   └── test_vision_colab.py
└── src/
    ├── __init__.py
    ├── main.py                  # Instancia FastAPI, lifespan y registro de routers
    ├── config.py                # Configuración central (CORS y formatos aceptados)
    ├── models.py                # Tablas SQLModel y motor/sesión de PostgreSQL
    ├── schemas.py               # Reexportación central de esquemas
    ├── errors.py                # Excepciones de dominio (ExtraccionError, ErrorServicio)
    ├── routes.py                # Rutas generales de salud (/health y /health/database)
    ├── controllers.py           # Controladores de salud
    ├── services.py              # Servicios de salud y verificación de base de datos
    ├── compartido/              # Infraestructura común a los recursos
    │   ├── __init__.py
    │   ├── sesion.py            # Motor y sesión de PostgreSQL
    │   ├── minio_client.py      # Cliente MinIO
    │   ├── storage_client.py    # Cliente Supabase Storage
    │   ├── db_client.py         # Cliente MongoDB
    │   ├── preprocessing.py     # Preprocesamiento y recorte de imágenes/PDF
    │   └── vision_client.py     # Cliente HTTP hacia Ollama (pipeline en 2 pasos)
    ├── planos/                  # Recurso /planos (CRUD, validación, preview y worker IA)
    │   ├── __init__.py
    │   ├── routes.py
    │   ├── controllers.py
    │   ├── services.py
    │   ├── schemas.py
    │   ├── nomenclatura.py
    │   └── worker.py
    └── tareas/                  # Recurso /tareas y /procesar-plano
        ├── __init__.py
        ├── routes.py
        ├── controllers.py
        ├── services.py
        └── schemas.py
```

### Capas dentro de cada recurso (`<recurso>/`)

Cada subcarpeta de recurso en `backend/src/` se organiza en las mismas cuatro capas:

```text
<recurso>/
├── routes.py       Define los endpoints HTTP (APIRouter con su prefijo) sin lógica de negocio
├── controllers.py  Adapta la petición HTTP <-> servicio y construye las respuestas HTTP
├── services.py     Contiene las reglas de negocio, validaciones y el acceso a base de datos/almacenamiento
└── schemas.py      Modelos Pydantic/SQLModel para validación de entrada y serialización de salida
```

### Detalle de carpetas y módulos

- **`backend/` (raíz del servicio)**:
  - `Dockerfile` y `requirements.txt`: imagen Docker de Python y dependencias necesarias para levantar el contenedor de la API.
- **`backend/src/` (núcleo de la aplicación)**:
  - `main.py`: punto de entrada de FastAPI; inicializa la base de datos y los workers en segundo plano durante el ciclo de vida (`lifespan`), configura CORS y registra los routers de cada recurso.
  - `config.py`: centraliza variables de entorno y constantes transversales (orígenes CORS, formatos de imagen y PDF soportados).
  - `models.py`: define las tablas relacionales con SQLModel (`Plano`, `EventoAuditoria`, `ProcesamientoIA`), sus relaciones y la inicialización del esquema en PostgreSQL (`init_db`).
  - `schemas.py`: punto único de reexportación de los esquemas de `planos` y `tareas`.
  - `errors.py`: define las excepciones de dominio (`ExtraccionError`, `ErrorServicio`) y su conversión a respuestas HTTP.
  - `routes.py`, `controllers.py` y `services.py`: implementan los endpoints generales de estado del servicio (`GET /health`) y comprobación de conexión a PostgreSQL (`GET /health/database`).
- **`backend/src/compartido/` (infraestructura y clientes externos)**:
  - `sesion.py`: provee el `engine` y el generador de sesiones (`get_session`) de PostgreSQL para inyección de dependencias.
  - `minio_client.py`: subida, descarga, verificación y borrado de planos originales y previsualizaciones en el bucket de MinIO.
  - `storage_client.py` y `db_client.py`: clientes de Supabase Storage y MongoDB utilizados por el flujo de extracción directa/asíncrona.
  - `preprocessing.py`: rasterización de páginas PDF (`pypdfium2`), recorte de alta resolución del cajetín técnico según coordenadas normalizadas y mejora de contraste/nitidez (`Pillow`).
  - `vision_client.py`: cliente HTTP hacia Ollama (local o Google Colab vía Ngrok) que ejecuta la detección de bounding box del cajetín (Paso 1) y la extracción JSON estructurada (Paso 2), incluyendo detección automática del modelo activo en Colab.
- **`backend/src/planos/` (catálogo de planos históricos — `/planos`)**:
  - `routes.py`, `controllers.py`, `services.py` y `schemas.py`: alta de planos con archivo y nomenclatura, listado con filtros, consulta de detalle con historial, descarga de archivo original y vista previa, validación inicial, modificación con auditoría, reintento de IA y baja física.
  - `nomenclatura.py`: normalización y validación del formato catastral (`circunscripción-sección-manzana-parcela`) y generación de su clave única.
  - `worker.py`: cola asíncrona (`planos_worker`) que procesa con IA los planos recién creados o reintentados y persiste los metadatos extraídos en PostgreSQL, retomando pendientes tras un reinicio.
- **`backend/src/tareas/` (procesamiento por cola de tareas — `/procesar-plano` y `/tareas`)**:
  - `routes.py`, `controllers.py`, `services.py` y `schemas.py`: gestor en memoria (`task_manager`) para procesar archivos de forma asíncrona (`POST /procesar-plano` y consulta en `GET /tareas/{task_id}`) o síncrona (`?sync=true`), definiendo el esquema `PlanoHistorico` que guía la salida JSON del modelo de visión.
- **`backend/tests/` (pruebas unitarias y de integración)**:
  - `test_health.py`: pruebas del endpoint `/health/database` ante conexión exitosa o fallo de PostgreSQL.
  - `test_nomenclatura.py`: pruebas de normalización catastral, unicidad, ciclo de validación/modificación, preservación de transcripción original y borrado.
  - `test_vision_colab.py`: pruebas del cliente de visión, selección dinámica de modelo en Google Colab (`colab-activo`), recarga de `.env` y pipeline en 2 pasos.

---

## Procesamiento acelerado con GPU en Google Colab (Paso a Paso)

Si no contás con una placa de video NVIDIA local, podés ejecutar **Ollama en Google Colab** aprovechando su GPU **NVIDIA T4 gratuita (16 GB VRAM)** y conectarlo a tu backend local mediante un túnel seguro de **Ngrok**. Esto reduce el tiempo de procesamiento de 60–90 segundos en CPU a unos pocos segundos por plano y permite elegir modelos más grandes (como `qwen2.5vl:7b` o `gemma3:12b`) directamente desde el notebook.

### Paso 1: Obtener tu Authtoken gratuito de Ngrok
1. Creá una cuenta gratuita o iniciá sesión en [https://dashboard.ngrok.com](https://dashboard.ngrok.com).
2. Ingresá a la sección **Your Authtoken**: [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).
3. Copiá tu token personal.

### Paso 2: Abrir el notebook en Google Colab y activar la GPU
1. Subí o abrí el archivo `ollama_colab.ipynb` incluido en la raíz de este repositorio en [Google Colab](https://colab.research.google.com/).
2. En el menú superior de Colab, entrá en **Entorno de ejecución** → **Cambiar tipo de entorno de ejecución**.
3. Seleccioná **GPU T4 (para los modelos de hasta 7b) o GPU L4 (para los modelos mas grandes, este no esta disponible con google colab gratis solo con planes de pago)** en "Acelerador por hardware" y guardá los cambios.

### Paso 3: Instalar e iniciar Ollama + Túnel Ngrok
1. Ejecutá la **Celda 1** (`📦 1. Instalar dependencias, Ollama y pyngrok`) y esperá a que finalice la instalación (~30–60 segundos).
2. En la **Celda 2** (`⚙️ Iniciar Ollama y generar URL pública`), pegá tu token en el campo `NGROK_TOKEN` y ejecutá la celda.
3. Al finalizar, la consola mostrará un bloque similar a este:
   ```text
   =================================================================
   🚀 ¡OLLAMA ESTÁ CORRIENDO EN GOOGLE COLAB!
   Copia esta URL en tu archivo .env local:
   OLLAMA_HOST=https://xxxx-xx-xx-xx.ngrok-free.dev
   =================================================================
   ```

### Paso 4: Elegir y activar el modelo de visión desde Google Colab
1. En la **Celda 3** (`🎯 Seleccionar y activar modelo de visión`), elegí el modelo que querés utilizar desde el selector desplegable `MODELO` (por ejemplo `qwen2.5vl:3b`, `qwen2.5vl:7b`, `qwen2.5vl:32b`, `gemma3:12b`, `gemma3:27b`, `mistral-small3.1:24b`, `minicpm-v:8b`) o escribí cualquier otro modelo de visión compatible con Ollama.
2. Ejecutá la celda. El notebook descargará el modelo en Colab y lo registrará automáticamente con el alias interno `colab-activo`.
3. **No hace falta modificar `VISION_MODEL` en tu `.env` local ni reiniciar Docker**: antes de procesar cada plano, el backend consulta los modelos de la instancia de Colab y utiliza automáticamente el que hayas dejado activo en esta celda.
4. Si en cualquier momento querés probar otro modelo, simplemente cambialo en el desplegable de la **Celda 3** y volvé a ejecutarla.

### Paso 5: Verificar el estado del túnel en Colab
1. Ejecutá la **Celda 4** (`🩺 Test de salud del túnel y modelo activo`) para confirmar que el túnel responde correctamente y verificar qué modelo está activo.
2. *(Opcional)* Ejecutá la **Celda 6** (`📜 6. Ver logs de Ollama en vivo`) para mantener la pestaña de Colab activa y observar en tiempo real las peticiones que llegan desde tu entorno local.

### Paso 6: Vincular tu entorno local con Google Colab
1. Abrí el archivo `.env` en la raíz del proyecto local y pegá la URL generada en el Paso 3:
   ```env
   OLLAMA_HOST=https://xxxx-xx-xx-xx.ngrok-free.dev
   ```
2. Si todavía no levantaste los contenedores locales, ejecutá:
   ```bash
   docker compose up -d
   ```
   *(Nota: Como `.env` está montado en el contenedor de la API y se lee dinámicamente en cada extracción, si cambiás `OLLAMA_HOST` en `.env` por una nueva sesión de Colab no necesitás recrear el contenedor).*

### Paso 7: Ejecutar las pruebas de integración con Colab
Para verificar el funcionamiento del cliente de visión y la selección dinámica de modelos:
```bash
docker compose exec -T api python -m unittest tests.test_vision_colab -v
```

---

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

Implementado en `backend/src/compartido/preprocessing.py` con la función `crop_cajetin_from_bbox`:

1. **Desnormalización:** Las coordenadas `[0..1000]` se convierten a píxeles exactos de la **imagen original sin comprimir**.
2. **Margen de seguridad (*Padding*):** Se expande la caja un 2% en ancho y alto para evitar cortar palabras o sellos que rocen los márgenes del cajetín.
3. **Optimización con Pillow (`preprocess_cajetin`):**
   - **Autocontraste:** Recupera trazos en tinta descolorida o papel amarillento (`ImageOps.autocontrast`).
   - **Realce de nitidez:** Aplica un filtro de nitidez (`ImageEnhance.Sharpness.enhance(1.5)`) para destacar tipografías pequeñas, números catastrales y firmas caligráficas.

---

### Paso 2: Extracción Estructurada de Datos Técnicos en HD

Se envía **únicamente el recorte del cajetín en máxima resolución** a Qwen2.5-VL con el esquema JSON completo de `PlanoHistorico` (`backend/src/tareas/schemas.py`). Al tener solo el rótulo en primer plano, el modelo dispone del 100% de su capacidad atencional y de resolución óptica en el texto que importa.

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
  (`backend/src/tareas/schemas.py`).

Esta lógica vive en `backend/src/tareas/services.py` (función `_guardar_extraccion`),
que se llama tanto desde el worker asíncrono como desde
`procesar_directo` (modo `sync`), después de que Qwen devuelve el
resultado. La subida a Supabase usa `backend/src/compartido/storage_client.py` y el
insert a Mongo usa `backend/src/compartido/db_client.py`.

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
| `POST` | `/planos` | Multipart: `archivo`, `circunscripcion`, `seccion`, `manzana`, `parcela_catastral` (obligatorios) + `ubicacion_fisica`, `expediente`, `direccion_referencia` (opcionales). Sube a MinIO, crea el plano como `pendiente` y dispara la IA en segundo plano (`ia_estado=procesando`). Si es PDF, rasteriza la primera página para el análisis y la previsualización. |
| `GET` | `/planos` | Lista. Filtros: `estado` (repetible: `?estado=validado&estado=sin_ubicacion`) y `q` (coincidencia exacta de nomenclatura: `3-K-12A-5B`). |
| `GET` | `/planos/{id}` | Detalle con historial. Sirve para consultar si la IA terminó (`ia_estado`). |
| `DELETE` | `/planos/{id}` | Elimina permanentemente el plano, su archivo, previsualización, auditoría y registros de IA. Devuelve 404 si no existe y 503 si falla el almacenamiento. |
| `GET` | `/planos/{id}/archivo` | Devuelve el archivo original (imagen o PDF original). |
| `GET` | `/planos/{id}/preview` | Devuelve una imagen JPEG de previsualización (la imagen original o la primera página rasterizada si es PDF). |
| `PUT` | `/planos/{id}/validar` | JSON con los metadatos revisados + `parcela`. Queda `validado` si hay parcela, si no `sin_ubicacion`. Agrega "Validación inicial" al historial. Devuelve 409 si el plano ya fue validado. |
| `PUT` | `/planos/{id}/modificar` | JSON con los metadatos + `parcela` + `motivo` (obligatorio, 400 si falta). Actualiza el plano y agrega el motivo al historial. |

Ejemplo:

```bash
curl -X POST http://localhost:8000/planos \
  -F "archivo=@plano.jpg" -F "circunscripcion=3" -F "seccion=K" -F "manzana=12A" -F "parcela_catastral=5B" -F "expediente=EXP-1936-045" \
  -F "ubicacion_fisica=Estante 3, caja 12"

curl -X PUT http://localhost:8000/planos/1/modificar \
  -H "Content-Type: application/json" \
  -d '{"arquitecto": "Francisco Salamone", "anio": 1936, "parcela": "Lote 4", "motivo": "Corrección de año"}'
```

Detalles de comportamiento:

- `validar` y `modificar` reemplazan **todos** los metadatos: un campo
  que no se manda queda en `null`, salvo `texto_extraido`, que conserva la
  transcripción original de la IA y se muestra como solo lectura (igual que el formulario del front,
  que siempre manda el objeto completo). `anio` acepta `""` como `null`.
- Si una persona valida un plano mientras la IA todavía lo procesa, el
  resultado de la IA no pisa los datos cargados a mano.
- Si la API se reinicia con planos en `procesando`, los vuelve a
  encolar al arrancar.
- Esto convive con `/procesar-plano` y `/tareas` (y su persistencia en
  Supabase/MongoDB), que siguen funcionando igual.

## Notas

- El esquema de campos a extraer está en `backend/src/tareas/schemas.py` (Pydantic).
  Agregá o quitá campos ahí y se propagan automáticamente al modelo.
- Sin GPU, cada plano puede tardar entre 20 y 90 segundos según
  resolución. Con GPU (ver comentario en `docker-compose.yml`) baja
  drásticamente.
- `backend/src/compartido/preprocessing.py` redimensiona y mejora el contraste de la
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
Formatos admitidos: JPEG, PNG, WEBP, TIFF y PDF (se analiza y previsualiza la primera página del plano).

El procesamiento por CPU tarda de 60 a 90 segundos.

### Nomenclatura del archivo y pruebas del frontend

La carga exige archivo, circunscripción, sección, manzana y parcela catastral.
Expediente, dirección de referencia y ubicación física siguen siendo opcionales.
La combinación de los cuatro componentes es única para cada plano, por regla
de este proyecto. El ID numérico interno se conserva para las relaciones.

El formato del proyecto admite circunscripción numérica positiva, sección con
letras A–Z, y manzana/parcela con número positivo y letras opcionales al final.
Cada componente tiene un límite técnico de 64 caracteres. Estos límites no son
una certificación de ARBA ni verifican la existencia real de la parcela.
Se normalizan espacios, mayúsculas y ceros iniciales: `03-k-012 a-05 b`
se guarda y busca como `3-K-12A-5B`. La consulta del catálogo es exacta;
ya no busca por dirección, expediente o año. Las colas de carga/revisión y las
listas de modificación siguen mostrando sus registros sin exigir una búsqueda.

Al iniciar la API se agregan columnas y un índice único, conservando los planos
anteriores. Estos quedan con nomenclatura pendiente, sin valores inventados;
se puede completar desde Revisión o Modificar antes de guardar. En Consultar
sólo aparecen planos catalogados. Los nuevos cambios requieren reiniciar la API:

```powershell
docker compose restart api
```

Pruebas (frontend con solicitudes simuladas; backend con SQLite temporal y
almacenamiento/IA simulados, sin modificar los planos del proyecto):

```powershell
node --test front/tests/errors.test.cjs
docker compose exec -T api python -m unittest tests.test_nomenclatura -v
```

Para probar la página usá `http://localhost:8080/planos-historicos.html`.
Live Server no reenvía `/api` al backend.

### Indicador de conexión a la base de datos

La barra lateral del módulo muestra el estado de PostgreSQL al ingresar y cada
15 segundos: verde si está conectada, rojo si la consulta falla y amarillo si
no se puede verificar (por ejemplo, si la API no responde o nginx devuelve 502).
El texto acompaña al color. Al recuperarse el servicio, se actualiza automáticamente.

`GET /health/database` en la API (o `/api/health/database` desde el front) ejecuta
`SELECT 1`: devuelve 200 con `{"database":"connected"}` o 503 con
`{"database":"disconnected"}`, sin exponer errores internos ni credenciales.
Comprueba la base del catálogo; MongoDB y los servicios de archivos no forman
parte de este indicador. Si la API no pudo iniciar por una falla de PostgreSQL,
el front muestra que no se pudo verificar el estado.

Para activar el endpoint, reiniciá la API y recargá la página:

```powershell
docker compose restart api
node --test front/tests/errors.test.cjs front/tests/database-status.test.cjs
docker compose exec -T api python -m unittest tests.test_health -v
```
