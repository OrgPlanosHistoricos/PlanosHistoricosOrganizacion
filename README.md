# Reconocimiento de Planos Históricos

Extrae datos (arquitecto, año, ubicación, etc.) de planos históricos
escaneados usando modelos de visión artificial (Qwen2.5-VL o Gemma 3) servidos por Ollama (localmente o en Google Colab con GPU T4 gratuita),
y los devuelve en JSON estructurado y normalizado.

---

<a id="indice"></a>
## 📑 Tabla de Contenidos

- [1. Puesta en Marcha Rápida (Uso)](#1-puesta-en-marcha-rápida-uso)
  - [1.1 Inicio del Entorno con Docker](#11-inicio-del-entorno-con-docker)
  - [1.2 Acceso a la Aplicación Web](#12-acceso-a-la-aplicación-web)
  - [1.3 Extracción con MongoDB y Supabase (procesar-plano)](#13-extracción-con-mongodb-y-supabase-procesar-plano)
- [2. Estructura y Arquitectura del Backend](#2-estructura-y-arquitectura-del-backend)
  - [2.1 Capas dentro de cada recurso](#21-capas-dentro-de-cada-recurso)
  - [2.2 Detalle de carpetas y módulos](#22-detalle-de-carpetas-y-módulos)
- [3. Procesamiento Acelerado con GPU en Google Colab (Paso a Paso)](#3-procesamiento-acelerado-con-gpu-en-google-colab-paso-a-paso)
- [4. Funcionamiento del Procesamiento con IA (Pipeline en 2 Pasos con Grounding)](#4-funcionamiento-del-procesamiento-con-ia-pipeline-en-2-pasos-con-grounding)
  - [4.1 El desafío en planos de gran formato](#41-el-desafío-en-planos-de-gran-formato)
  - [4.2 Paso 1: Detección y Grounding del Cajetín](#42-paso-1-detección-y-grounding-del-cajetín)
  - [4.3 Recorte en Alta Resolución (Crop y Preprocesamiento)](#43-recorte-en-alta-resolución-crop-y-preprocesamiento)
  - [4.4 Paso 2: Extracción Estructurada de Datos Técnicos en HD](#44-paso-2-extracción-estructurada-de-datos-técnicos-en-hd)
  - [4.5 Resiliencia y Manejo de Errores](#45-resiliencia-y-manejo-de-errores)
- [5. Catálogo y Base de Datos Relacional (PostgreSQL y MinIO)](#5-catálogo-y-base-de-datos-relacional-postgresql-y-minio)
  - [5.1 Variables de Entorno y Conexión](#51-variables-de-entorno-y-conexión)
  - [5.2 Funcionamiento de la Base de Datos](#52-funcionamiento-de-la-base-de-datos)
  - [5.3 Tablas y Campos](#53-tablas-y-campos)
    - [Tabla planos](#1-tabla-planos-clase-plano-y-planobase)
    - [Tabla eventos_auditoria](#2-tabla-eventos_auditoria-clase-eventoauditoria)
    - [Tabla procesamientos_ia](#3-tabla-procesamientos_ia-clase-procesamientoia)
  - [5.4 Diagrama Entidad-Relación](#54-diagrama-entidad-relación)
  - [5.5 Endpoints del Catálogo (planos)](#55-endpoints-del-catálogo-planos)
- [6. Almacenamiento Secundario (Supabase y MongoDB)](#6-almacenamiento-secundario-supabase-y-mongodb)
  - [6.1 Variables de Entorno](#61-variables-de-entorno)
- [7. Reglas de Negocio, Nomenclatura y Pruebas](#7-reglas-de-negocio-nomenclatura-y-pruebas)
  - [7.1 Nomenclatura Catastral y Reglas del Archivo](#71-nomenclatura-catastral-y-reglas-del-archivo)
  - [7.2 Indicador de Conexión a la Base de Datos](#72-indicador-de-conexión-a-la-base-de-datos)
  - [7.3 Ejecución de Pruebas Automatizadas](#73-ejecución-de-pruebas-automatizadas)
- [8. Notas y Parámetros Técnicos](#8-notas-y-parámetros-técnicos)

---

## 1. Puesta en Marcha Rápida (Uso)

### 1.1 Inicio del Entorno con Docker

Para levantar el entorno local completo (PostgreSQL, MinIO, API y Frontend) usando Google Colab como motor de IA:

```bash
docker compose up -d
```

> **Nota sobre Ollama local:** Los contenedores locales `ollama` y `ollama-pull` están bajo el perfil opcional `local-ai`, por lo que `docker compose up -d` **no los levanta ni descarga modelos localmente**. Si en algún momento querés correr Ollama localmente en Docker en lugar de usar Google Colab, ejecutá:
> ```bash
> docker compose --profile local-ai up -d
> ```
> y podés seguir la descarga inicial con `docker compose logs -f ollama-pull`.

La API espera hasta 300 segundos por la respuesta de Ollama (ajustable mediante la variable `OLLAMA_TIMEOUT`).

### 1.2 Acceso a la Aplicación Web

El ingreso a la aplicación web debe realizarse desde [http://localhost:8080](http://localhost:8080) (o directamente a [http://localhost:8080/planos-historicos.html](http://localhost:8080/planos-historicos.html)) en el navegador.

> **Importante**: No abras el archivo HTML directamente desde el explorador ni a través de Live Server sin proxy, ya que el frontend se comunica con el backend mediante rutas relativas (`/api/...`) que Nginx reenvía internamente al contenedor `api:8000`, evitando problemas de CORS y resolución de red.

Formatos de archivo admitidos: JPEG, PNG, WEBP, TIFF y PDF (se analiza y previsualiza la primera página del plano).

### 1.3 Extracción con MongoDB y Supabase (procesar-plano)

> **Nota**: Este endpoint procesa planos de manera aislada utilizando Supabase Storage y MongoDB. Para el catálogo completo con PostgreSQL, MinIO y auditoría, consultá la sección [Catálogo y Base de Datos Relacional](#5-catálogo-y-base-de-datos-relacional-postgresql--minio).

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

[↑ Volver a la tabla de contenidos](#indice)

---

## 2. Estructura y Arquitectura del Backend

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

### 2.1 Capas dentro de cada recurso

Cada subcarpeta de recurso en `backend/src/` se organiza en las mismas cuatro capas:

```text
<recurso>/
├── routes.py       Define los endpoints HTTP (APIRouter con su prefijo) sin lógica de negocio
├── controllers.py  Adapta la petición HTTP <-> servicio y construye las respuestas HTTP
├── services.py     Contiene las reglas de negocio, validaciones y el acceso a base de datos/almacenamiento
└── schemas.py      Modelos Pydantic/SQLModel para validación de entrada y serialización de salida
```

### 2.2 Detalle de carpetas y módulos

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
  - `routes.py`, `controllers.py`, `services.py` y `schemas.py`: alta de planos con archivo y nomenclatura, listado con filtros, consulta de detalle con historial, descarga de archivo original y vista previa, validación inicial, modificación con auditoría, reintento de IA y baja lógica (*soft delete*).
  - `nomenclatura.py`: normalización y validación del formato catastral (`circunscripción-sección-manzana-parcela`) y generación de su clave única.
  - `worker.py`: cola asíncrona (`planos_worker`) que procesa con IA los planos recién creados o reintentados y persiste los metadatos extraídos en PostgreSQL, retomando pendientes tras un reinicio.
- **`backend/src/tareas/` (procesamiento por cola de tareas — `/procesar-plano` y `/tareas`)**:
  - `routes.py`, `controllers.py`, `services.py` y `schemas.py`: gestor en memoria (`task_manager`) para procesar archivos de forma asíncrona (`POST /procesar-plano` y consulta en `GET /tareas/{task_id}`) o síncrona (`?sync=true`), definiendo el esquema `PlanoHistorico` que guía la salida JSON del modelo de visión.
- **`backend/tests/` (pruebas unitarias y de integración)**:
  - `test_health.py`: pruebas del endpoint `/health/database` ante conexión exitosa o fallo de PostgreSQL.
  - `test_nomenclatura.py`: pruebas de normalización catastral, unicidad, ciclo de validación/modificación, preservación de transcripción original y borrado.
  - `test_vision_colab.py`: pruebas del cliente de visión, selección dinámica de modelo en Google Colab (`colab-activo`), recarga de `.env` y pipeline en 2 pasos.

[↑ Volver a la tabla de contenidos](#indice)

---

## 3. Procesamiento acelerado con GPU en Google Colab (Paso a Paso)

Si no contás con una placa de video NVIDIA local, podés ejecutar **Ollama en Google Colab** aprovechando su GPU **NVIDIA T4 gratuita (16 GB VRAM)** y conectarlo a tu backend local mediante un túnel seguro de **Ngrok**. Esto reduce el tiempo de procesamiento de 60–90 segundos en CPU a unos pocos segundos por plano y permite elegir modelos más grandes (como `qwen2.5vl:7b` o `gemma3:12b`) directamente desde el notebook.

### Paso 1: Obtener tu Authtoken gratuito de Ngrok
1. Creá una cuenta gratuita o iniciá sesión en [https://dashboard.ngrok.com](https://dashboard.ngrok.com).
2. Ingresá a la sección **Your Authtoken**: [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).
3. Copiá tu token personal.

### Paso 2: Abrir el notebook en Google Colab y activar la GPU
1. Subí o abrí el archivo `ollama_colab.ipynb` incluido en la raíz de este repositorio en [Google Colab](https://colab.research.google.com/).
2. En el menú superior de Colab, entrá en **Entorno de ejecución** → **Cambiar tipo de entorno de ejecución**.
3. Seleccioná **GPU T4 (para los modelos de hasta 7b) o GPU L4 (para los modelos más grandes, este no está disponible con Google Colab gratis solo con planes de pago)** en "Acelerador por hardware" y guardá los cambios.

### Paso 3: Configurar y ejecutar la Celda 1 (Arranque Principal)
El notebook ollama_colab.ipynb está optimizado en **2 celdas**:
1. En la **Celda 1** (🚀 1. Arranque Principal: Almacenamiento, Ollama, Modelo y Túnel Ngrok), completá los parámetros del formulario:
   - NGROK_TOKEN: pegá tu Authtoken de Ngrok.
   - MODELO: seleccioná el modelo de visión del desplegable (por ejemplo qwen2.5vl:7b, qwen2.5vl:3b, gemma3:12b, minicpm-v:8b) o escribí cualquier modelo compatible con Ollama.
   - USAR_GOOGLE_DRIVE (True/False):
     - En True, monta tu Google Drive personal (drive.mount('/content/drive')) y guarda los modelos en OLLAMA_MODELS=/content/drive/MyDrive/ollama_models (cada integrante usa su propia cuenta sin afectar al resto).
     - En False, usa almacenamiento efímero local (/content/ollama_models) si no tenés espacio en Drive.
2. Ejecutá la **Celda 1**. El script:
   - Instala e inicia ollama serve apuntando a la carpeta de modelos elegida.
   - Consulta http://127.0.0.1:11434/api/tags antes de descargar: si el modelo ya existe en tu Drive o carpeta local, **omite la descarga** y lo usa directamente; si no existe, lo descarga una única vez.
   - Registra el alias colab-activo (ollama cp {MODELO} colab-activo) para que el backend local detecte automáticamente el modelo activo sin tocar VISION_MODEL en .env.
   - Levanta el túnel Ngrok en el puerto 11434 y muestra al final el banner listo para copiar:
   `	ext
   ======================================================================
   🚀 ¡OLLAMA ESTÁ CORRIENDO EN GOOGLE COLAB!
   📂 Almacenamiento: Google Drive personal (/content/drive/MyDrive/ollama_models)
   🎯 Modelo activo:  qwen2.5vl:7b (alias: colab-activo)
   ----------------------------------------------------------------------
   Copia y pega esta línea en tu archivo .env local:
   OLLAMA_HOST=https://xxxx.ngrok-free.app
   ======================================================================
   `

### Paso 4: Mantener la sesión activa y ver logs (Opcional)
1. Ejecutá la **Celda 2** (📜 2. Mantenimiento de sesión y logs de Ollama en vivo) para mantener la pestaña de Colab en ejecución y observar en tiempo real las peticiones que llegan desde tu entorno local.

### Paso 5: Vincular tu entorno local con Google Colab
1. Abrí el archivo .env en la raíz del proyecto local y pegá la URL generada en la Celda 1:
   `env
   OLLAMA_HOST=https://xxxx.ngrok-free.app
   `
2. Si todavía no levantaste los contenedores locales, ejecutá:
   `ash
   docker compose up -d
   `
   *(Nota: Como .env está montado en el contenedor de la API y se lee dinámicamente en cada extracción, si cambiás OLLAMA_HOST en .env por una nueva sesión de Colab no necesitás recrear el contenedor).*

### Paso 6: Ejecutar las pruebas de integración con Colab
Para verificar el funcionamiento del cliente de visión y la selección dinámica de modelos:
`ash
docker compose exec -T api python -m unittest tests.test_vision_colab -v
`

[↑ Volver a la tabla de contenidos](#indice)

---

## 4. Funcionamiento del Procesamiento con IA (Pipeline en 2 Pasos con Grounding)

El procesamiento de planos combina las normas de dibujo técnico (**IRAM 4504** en Argentina e **ISO 7200** a nivel internacional) con las capacidades de **Grounding y Detección de Objetos** del modelo **Qwen2.5-VL 3B**.

### 4.1 El desafío en planos de gran formato
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

### 4.2 Paso 1: Detección y Grounding del Cajetín

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

### 4.3 Recorte en Alta Resolución (Crop y Preprocesamiento)

Implementado en `backend/src/compartido/preprocessing.py` con la función `crop_cajetin_from_bbox`:

1. **Desnormalización:** Las coordenadas `[0..1000]` se convierten a píxeles exactos de la **imagen original sin comprimir**.
2. **Margen de seguridad (*Padding*):** Se expande la caja un 2% en ancho y alto para evitar cortar palabras o sellos que rocen los márgenes del cajetín.
3. **Optimización con Pillow (`preprocess_cajetin`):**
   - **Autocontraste:** Recupera trazos en tinta descolorida o papel amarillento (`ImageOps.autocontrast`).
   - **Realce de nitidez:** Aplica un filtro de nitidez (`ImageEnhance.Sharpness.enhance(1.5)`) para destacar tipografías pequeñas, números catastrales y firmas caligráficas.

---

### 4.4 Paso 2: Extracción Estructurada de Datos Técnicos en HD

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

### 4.5 Resiliencia y Manejo de Errores

- **Reintentos automáticos:** Tanto el gestor de tareas asíncronas (`backend/src/tareas/services.py`) como el worker del catálogo (`backend/src/planos/worker.py`) ejecutan reintentos automáticos si la llamada al modelo no responde en el primer intento.
- **Doble Fallback:** Si por algún caso extremo la extracción sobre el recorte del cajetín fallase, el sistema reintenta la extracción sobre el plano completo para no dejar la petición en error.
- **Concurrencia no bloqueante:** Toda la inferencia pesada corre en hilos separados (`asyncio.to_thread`) para mantener ágil el event loop de FastAPI.

[↑ Volver a la tabla de contenidos](#indice)

---

## 5. Catálogo y Base de Datos Relacional (PostgreSQL y MinIO)

El catálogo de planos (datos de origen, estado de validación, auditoría
e historial) se guarda en **PostgreSQL**, y los archivos originales en
**MinIO** (bucket `planos`). Ambos corren como servicios del
`docker-compose.yml`: las tablas se crean e inicializan solas al arrancar la API.

### 5.1 Variables de Entorno y Conexión

Variables en `.env` (ver `.env.example`; si no están, se usan esos
mismos valores por defecto):

```env
POSTGRES_USER=planos
POSTGRES_PASSWORD=planos
POSTGRES_DB=planos_db
```

Postgres queda expuesto en `localhost:5432` para inspeccionarlo con
cualquier cliente (DBeaver, pgAdmin, `psql`), y la consola de MinIO en
[http://localhost:9001](http://localhost:9001).

### 5.2 Funcionamiento de la Base de Datos

La persistencia del catálogo se apoya en **PostgreSQL** mediante **SQLModel** (integración entre Pydantic y SQLAlchemy en `backend/src/models.py`), complementada por **MinIO** para el almacenamiento de archivos binarios:

1. **Inicialización y Migraciones Automáticas (`init_db`)**:
   - Al arrancar la aplicación (`main.py`), `init_db()` ejecuta `SQLModel.metadata.create_all(engine)`.
   - Adicionalmente, aplica sentencias idempotentes `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` y `CREATE UNIQUE INDEX IF NOT EXISTS`. Esto permite actualizar esquemas existentes sin pérdida de información ni requerir scripts de migración manuales.

2. **Integridad de Archivos y Almacenamiento Híbrido**:
   - Los archivos originales (JPEG, PNG, WEBP, TIFF, PDF) y sus previsualizaciones JPEG se suben al bucket `planos` de MinIO.
   - En PostgreSQL se registra la ruta relativa (`minio_path`), el peso del documento (`tamano_bytes`) y la firma criptográfica **SHA-256** (`hash_sha256`) calculada en memoria antes de la subida para garantizar que el archivo nunca haya sido alterado.

3. **Unicidad de Nomenclatura Catastral**:
   - Cada plano posee cuatro componentes obligatorios: `circunscripcion`, `seccion`, `manzana` y `parcela_catastral`.
   - La concatenación normalizada (ej. `3-K-12A-5B`) se indexa de forma única con el índice `ux_planos_nomenclatura`, impidiendo duplicados en el catálogo activo.

4. **Trazabilidad y Auditoría de Operaciones (`eventos_auditoria`)**:
   - Toda mutación (`Carga`, `Validación`, `Modificación`, `Observación`, `Caducidad`) genera un registro inmutable.
   - Se guardan snapshots en formato JSON (`valores_anteriores` y `valores_nuevos`), el motivo justificado, el operador responsable y la dirección IP de origen (`ip_origen`).

5. **Baja Lógica (*Soft Delete*)**:
   - Al ejecutar `DELETE /planos/{id}`, el sistema no destruye los datos ni borra los archivos físicos en MinIO: marca `activo = False`, libera la nomenclatura (asignándole `null` para permitir reclasificaciones futuras) y añade un evento de auditoría con la acción `'Caducidad'`.

6. **Trazabilidad de Inferencia IA (`procesamientos_ia`)**:
   - Cada intento de extracción automática por el modelo de visión (hasta un máximo de 3 intentos) se registra de forma independiente.
   - Se documenta el modelo utilizado (`modelo_ia`), la versión del prompt (`version_prompt`), los parámetros de preprocesamiento aplicados (`parametros_preprocesamiento`), el texto OCR crudo (`texto_extraido_raw`), la respuesta JSON íntegra (`respuesta_json_raw`) y el tiempo de respuesta (`duracion_ms`).

---

### 5.3 Tablas y Campos

#### 1. Tabla planos (Clase Plano y PlanoBase)

Representa la ficha del plano histórico dentro del archivo municipal o institucional.

| Campo | Tipo SQL | Restricciones / Default | Descripción |
|---|---|---|---|
| `id` | `INTEGER` | Primary Key, Autoincremental | Identificador único del plano. |
| `minio_path` | `TEXT` | NOT NULL | Clave o ruta del archivo original almacenado en MinIO (ej. `<uuid>.<ext>`). |
| `hash_sha256` | `VARCHAR(64)` | Nullable | Hash SHA-256 del archivo original para verificar su integridad. |
| `tamano_bytes` | `INTEGER` | Nullable | Tamaño exacto del archivo original subido, expresado en bytes. |
| `nombre_original` | `TEXT` | NOT NULL | Nombre original del archivo proporcionado por el usuario al subirlo. |
| `content_type` | `TEXT` | NOT NULL | Tipo MIME del archivo (ej. `image/jpeg`, `application/pdf`). |
| `circunscripcion` | `TEXT` | NOT NULL, Default `''` | Circunscripción catastral normalizada (ej. `3`). |
| `seccion` | `TEXT` | NOT NULL, Default `''` | Sección catastral normalizada (ej. `K`). |
| `manzana` | `TEXT` | NOT NULL, Default `''` | Manzana catastral normalizada (ej. `12A`). |
| `parcela_catastral`| `TEXT` | NOT NULL, Default `''` | Parcela catastral normalizada (ej. `5B`). |
| `nomenclatura` | `TEXT` | Nullable, Unique Index | Clave unificada (ej. `3-K-12A-5B`). Se setea a `null` si se da de baja lógica. |
| `ubicacion_fisica` | `TEXT` | Default `''` | Ubicación del documento en el archivo físico (estante, planera, caja). |
| `expediente` | `TEXT` | Default `''` | Número o código del expediente administrativo vinculado. |
| `direccion_referencia` | `TEXT` | Default `''` | Dirección urbana aproximada o de referencia. |
| `parcela` | `TEXT` | Default `''` | Parcela o lote libre asignado en catalogación. |
| `estado` | `VARCHAR` | Default `'pendiente'` | Estado de catalogación humana: `pendiente`, `validado`, `sin_ubicacion`. |
| `ia_estado` | `VARCHAR` | Default `'procesando'`| Estado de análisis del worker: `procesando`, `completado`, `error`, `no_aplica`. |
| `ia_error` | `TEXT` | Nullable | Detalle del error devuelto por la IA si la extracción falló. |
| `ia_propuesta` | `TEXT` | Nullable | JSON con propuesta sugerida por la IA tras un reintento en plano ya validado. |
| `creado_por` | `TEXT` | Nullable | Identificador del usuario u operador que realizó la carga. |
| `validado_por` | `TEXT` | Nullable | Identificador del operador técnico que aprobó la catalogación. |
| `validado_en` | `TIMESTAMPTZ`| Nullable | Fecha y hora exacta de la validación inicial (independiente de actualizaciones posteriores). |
| `activo` | `BOOLEAN` | NOT NULL, Default `TRUE` | Bandera de baja lógica (*soft delete*). `False` indica que el plano fue dado de baja. |
| `texto_extraido` | `TEXT` | Nullable | Transcripción OCR final consolidada y searchable del plano. |
| `arquitecto` | `TEXT` | Nullable | Autor, proyectista o profesional firmante. |
| `anio` | `INTEGER` | Nullable | Año del plano o proyecto (número de 4 dígitos, ej. 1936). |
| `titulo` | `TEXT` | Nullable | Título de la obra, proyecto o designación de la lámina. |
| `ubicacion` | `TEXT` | Nullable | Localidad o ubicación geográfica leída del rótulo. |
| `escala` | `TEXT` | Nullable | Escala técnica indicada (ej. `1:100`, `1:50`). |
| `tipo_de_plano` | `TEXT` | Nullable | Tipología (planta, fachada, corte, detalle, etc.). |
| `material_soporte`| `TEXT` | Nullable | Soporte físico indicado expresamente (papel tela, calco, vegetal). |
| `notas` | `TEXT` | Nullable | Notas complementarias, sellos o anotaciones marginales. |
| `creado_en` | `TIMESTAMPTZ`| NOT NULL, Default `now()` | Fecha y hora de creación del registro (UTC). |
| `actualizado_en` | `TIMESTAMPTZ`| NOT NULL, Default `now()` | Fecha y hora de la última modificación (UTC). |

---

#### 2. Tabla eventos_auditoria (Clase EventoAuditoria)

Registra cada acción administrativa realizada sobre un plano para asegurar trazabilidad jurídica e institucional.

| Campo | Tipo SQL | Restricciones / Default | Descripción |
|---|---|---|---|
| `id` | `INTEGER` | Primary Key, Autoincremental | Identificador único del evento. |
| `plano_id` | `INTEGER` | NOT NULL, Foreign Key (`planos.id`) | Identificador del plano auditado (indexado). |
| `usuario_id` | `TEXT` | NOT NULL | Usuario o rol que ejecutó la operación (ej. `Operador`, `Validador`). |
| `fecha` | `TIMESTAMPTZ`| NOT NULL, Default `now()` | Fecha y hora de la operación en UTC. |
| `accion` | `VARCHAR(15)` | NOT NULL, Default `'Modificación'` | Clasificación del evento: `'Carga'`, `'Validación'`, `'Modificación'`, `'Observación'`, `'Caducidad'`. |
| `motivo` | `TEXT` | NOT NULL | Explicación o motivo obligatorio del cambio introducido. |
| `valores_anteriores` | `TEXT` | Nullable | Snapshot en formato JSON con el estado de los campos antes de la acción. |
| `valores_nuevos` | `TEXT` | Nullable | Snapshot en formato JSON con el estado de los campos después de la acción. |
| `ip_origen` | `VARCHAR(45)` | Nullable | Dirección IP (IPv4 o IPv6) desde la cual se emitió la solicitud HTTP. |

---

#### 3. Tabla procesamientos_ia (Clase ProcesamientoIA)

Almacena el historial y los resultados de cada intento de inferencia ejecutado por los modelos de visión sobre el plano.

| Campo | Tipo SQL | Restricciones / Default | Descripción |
|---|---|---|---|
| `id` | `INTEGER` | Primary Key, Autoincremental | Identificador único del intento de procesamiento. |
| `plano_id` | `INTEGER` | NOT NULL, Foreign Key (`planos.id`) | Identificador del plano procesado (indexado). |
| `intento` | `INTEGER` | NOT NULL | Número correlativo del intento (1, 2 o 3). |
| `estado` | `VARCHAR` | NOT NULL | Estado de este intento: `procesando`, `completado`, `error`, `no_aplica`. |
| `error` | `TEXT` | Nullable | Traza o detalle del error si el intento no prosperó. |
| `modelo_ia` | `VARCHAR(100)`| NOT NULL, Default `'qwen2.5-vl:3b'` | Nombre y versión exacta del modelo de visión que procesó el plano. |
| `version_prompt` | `VARCHAR(30)` | Nullable | Versión o etiqueta del prompt utilizado (ej. `v2.0-cajetin-2pasos`). |
| `parametros_preprocesamiento` | `TEXT` | Nullable | JSON con los parámetros aplicados en `preprocessing.py` (resolución, recorte, contraste, nitidez, rotación). |
| `texto_extraido_raw` | `TEXT` | Nullable | Transcripción íntegra cruda devuelta por el modelo sin edición posterior. |
| `respuesta_json_raw` | `TEXT` | Nullable | Payload JSON completo devuelto por el modelo para ese intento. |
| `duracion_ms` | `INTEGER` | Nullable | Duración total de la inferencia en milisegundos. |
| `fecha` | `TIMESTAMPTZ`| NOT NULL, Default `now()` | Fecha y hora en que se registró el intento (UTC). |

---

### 5.4 Diagrama Entidad-Relación

```mermaid
erDiagram
    planos ||--o{ eventos_auditoria : "registra historial"
    planos ||--o{ procesamientos_ia : "registra intentos"

    planos {
        int id PK
        string minio_path
        string hash_sha256
        int tamano_bytes
        string nombre_original
        string content_type
        string nomenclatura UK
        string estado
        string ia_estado
        boolean activo
        timestamptz validado_en
        timestamptz creado_en
        timestamptz actualizado_en
    }

    eventos_auditoria {
        int id PK
        int plano_id FK
        string usuario_id
        timestamptz fecha
        string accion
        string motivo
        text valores_anteriores
        text valores_nuevos
        string ip_origen
    }

    procesamientos_ia {
        int id PK
        int plano_id FK
        int intento
        string estado
        string modelo_ia
        string version_prompt
        text parametros_preprocesamiento
        text texto_extraido_raw
        text respuesta_json_raw
        int duracion_ms
        timestamptz fecha
    }
```

### 5.5 Endpoints del Catálogo (planos)

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/planos` | Multipart: `archivo`, `circunscripcion`, `seccion`, `manzana`, `parcela_catastral` (obligatorios) + `ubicacion_fisica`, `expediente`, `direccion_referencia` (opcionales). Sube a MinIO, crea el plano como `pendiente` y dispara la IA en segundo plano (`ia_estado=procesando`). Si es PDF, rasteriza la primera página para el análisis y la previsualización. |
| `GET` | `/planos` | Lista. Filtros: `estado` (repetible: `?estado=validado&estado=sin_ubicacion`) y `q` (coincidencia exacta de nomenclatura: `3-K-12A-5B`). |
| `GET` | `/planos/{id}` | Detalle con historial. Sirve para consultar si la IA terminó (`ia_estado`). |
| `DELETE` | `/planos/{id}` | Baja lógica (*soft delete*): marca `activo=False`, libera la nomenclatura y registra un evento de auditoría `'Caducidad'`. Conserva el documento original y su trazabilidad histórica. Devuelve 404 si el plano no existe o ya fue dado de baja. |
| `GET` | `/planos/{id}/archivo` | Devuelve el archivo original (imagen o PDF original). |
| `GET` | `/planos/{id}/preview` | Devuelve una imagen JPEG de previsualización (la imagen original o la primera página rasterizada si es PDF). |
| `PUT` | `/planos/{id}/validar` | JSON con los metadatos revisados + nomenclatura catastral obligatoria. Pasa a estado `validado`, registra `validado_en` y añade un evento `'Validación'` al historial de auditoría con snapshot JSON. Devuelve 409 si el plano ya fue validado. |
| `PUT` | `/planos/{id}/modificar` | JSON con los metadatos + nomenclatura + `motivo` (obligatorio, 400 si falta). Actualiza el plano, limpia `ia_propuesta` y añade un evento `'Modificación'` al historial con snapshot de valores anteriores y nuevos. |
| `POST` | `/planos/{id}/reintentar_ia` | Query param `usuario_id`. Dispara un reanálisis con IA si el plano no está en procesamiento y no superó el límite de 3 intentos. Si el plano ya estaba validado, la respuesta de la IA se guarda en `ia_propuesta` para revisión sin pisar los datos confirmados. |
| `POST` | `/planos/{id}/descartar_propuesta` | Descarta la propuesta sugerida por la IA (`ia_propuesta = null`) conservando los datos aprobados por el operador. |

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

[↑ Volver a la tabla de contenidos](#indice)

---

## 6. Almacenamiento Secundario (Supabase y MongoDB)

Cada plano procesado a través de los endpoints `/procesar-plano` y `/tareas` (tanto en modo asíncrono como con `?sync=true`) se persiste de forma aislada en dos servicios externos:

- **Supabase Storage** (bucket `planos_escaneados`): guarda el archivo original subido y expone su URL pública (`supabase_url` en la respuesta de `/tareas/{task_id}`).
- **MongoDB** (base `planos_db`, colección `extracciones`): guarda el documento completo (fecha de procesamiento, metadatos del archivo y la extracción realizada por el modelo) según el esquema `DocumentoExtraccion` (`backend/src/tareas/schemas.py`).

Esta lógica vive en `backend/src/tareas/services.py` (función `_guardar_extraccion`), utilizando los clientes `backend/src/compartido/storage_client.py` y `backend/src/compartido/db_client.py`.

### 6.1 Variables de Entorno

Definidas en `.env` (ver `.env.example`):

```env
MONGODB_URI=mongodb+srv://usuario:password@cluster.mongodb.net/?appName=...
SUPABASE_URL=https://<proyecto>.supabase.co
SUPABASE_KEY=<service_role key>
```

> **Importante sobre `SUPABASE_KEY`**: Debe ser la **service_role key** (Supabase Dashboard → Settings → API), no la `anon`/`publishable`. El bucket tiene Row Level Security (RLS) activado, por lo que la clave anónima no tiene permiso de `INSERT` y falla con error 403. La service_role key nunca se expone al cliente web.
>
> **Importante sobre `MONGODB_URI`**: La IP del servidor debe estar habilitada en la lista blanca de Atlas (Network Access → Add IP Address) para evitar errores `ServerSelectionTimeoutError`.

[↑ Volver a la tabla de contenidos](#indice)

---

## 7. Reglas de Negocio, Nomenclatura y Pruebas

### 7.1 Nomenclatura Catastral y Reglas del Archivo

La carga exige archivo, circunscripción, sección, manzana y parcela catastral. Expediente, dirección de referencia y ubicación física son opcionales. La combinación de los cuatro componentes es única para cada plano dentro del archivo. El ID numérico interno se conserva para las relaciones de base de datos.

- **Formato admitido**: Circunscripción numérica positiva, sección con letras A–Z, y manzana/parcela con número positivo y letras opcionales al final. Cada componente tiene un límite técnico de 64 caracteres.
- **Normalización**: Se normalizan espacios, mayúsculas y ceros iniciales: `03-k-012 a-05 b` se guarda y busca como `3-K-12A-5B`.
- **Búsqueda exacta**: La consulta en el catálogo es estricta por clave catastral; no realiza búsquedas parciales por expediente o año. Las colas de carga/revisión y las listas de modificación muestran sus registros sin requerir una búsqueda previa.
- **Migración de planos históricos**: Al iniciar la API, `init_db()` añade las columnas requeridas y el índice único preservando planos anteriores, los cuales quedan con nomenclatura pendiente hasta su revisión o modificación manual.

### 7.2 Indicador de Conexión a la Base de Datos

La barra lateral de la interfaz web muestra el estado de conexión con PostgreSQL en tiempo real (al ingresar y cada 15 segundos):
- **Verde**: Base de datos conectada y operativa.
- **Rojo**: Fallo de conexión o consulta rechazada.
- **Amarillo**: Estado desconocido (por ejemplo, si la API está caída o Nginx responde con 502).

El endpoint `GET /health/database` (o `/api/health/database` a través del proxy) ejecuta `SELECT 1` y devuelve `{"database":"connected"}` (HTTP 200) o `{"database":"disconnected"}` (HTTP 503), garantizando que nunca se expongan credenciales ni trazas de error internas al cliente.

### 7.3 Ejecución de Pruebas Automatizadas

El proyecto cuenta con suites de pruebas unitarias y de integración tanto para el backend (con SQLite temporal y mocks de almacenamiento/IA) como para el frontend (con simulación de DOM y red):

```bash
# Pruebas de reglas de negocio, endpoints y nomenclatura
docker compose exec -T api python -m unittest tests.test_nomenclatura -v

# Pruebas de salud del sistema y conexión a PostgreSQL
docker compose exec -T api python -m unittest tests.test_health -v

# Pruebas del cliente de visión e integración dinámica con Google Colab
docker compose exec -T api python -m unittest tests.test_vision_colab -v

# Pruebas del frontend (manejo de errores y estado de base de datos)
node --test front/tests/errors.test.cjs front/tests/database-status.test.cjs
```

[↑ Volver a la tabla de contenidos](#indice)

---

## 8. Notas y Parámetros Técnicos

- **Esquema de extracción**: Definido en `backend/src/tareas/schemas.py` (`PlanoHistorico` con Pydantic). Cualquier ajuste o nuevo campo agregado allí se propaga automáticamente a las directivas de extracción estructurada del modelo VLM.
- **Rendimiento con GPU vs CPU**: Sin GPU, cada plano puede demorar entre 20 y 90 segundos según su resolución óptica. Con aceleración por GPU (Google Colab T4 o GPU NVIDIA local), el tiempo se reduce a unos pocos segundos por lámina.
- **Ajuste de Preprocesamiento**: La función `backend/src/compartido/preprocessing.py` optimiza la resolución preliminar (`MAX_DIMENSION = 1600`) y la resolución del cajetín técnico (`MAX_CAJETIN_DIMENSION = 1800`) aplicando autocontraste y realce de nitidez con Pillow antes de consultar al modelo.

[↑ Volver a la tabla de contenidos](#indice)