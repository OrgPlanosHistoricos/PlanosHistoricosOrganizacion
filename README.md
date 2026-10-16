# API y Sistema de Reconocimiento de Planos Históricos

Sistema integral para la gestión, procesamiento, extracción de metadatos, catálogo y consulta de planos históricos utilizando FastAPI, Qwen2.5-VL 3B (vía Ollama), MinIO, PostgreSQL, Supabase, MongoDB y un frontend servido con Nginx.

---

## Información Importante y Requisitos Previos

- Acceso a la Aplicación Web: Se debe ingresar desde http://localhost:8080 en el navegador. De lo contrario, las peticiones pueden ser bloqueadas por políticas CORS o restricción de acceso a la API.
- Formatos Admitidos: JPEG, PNG, WEBP, TIFF y PDF (para archivos PDF se analiza y previsualiza la primera página del plano).
- Modelo de Visión: El sistema descarga automáticamente el modelo qwen2.5vl:3b mediante Ollama al levantar el contenedor.
- Tiempos de Inferencia: En ejecuciones por CPU, la inferencia de cada plano toma habitualmente entre 60 y 90 segundos.

---

## Arquitectura del Sistema

El proyecto está diseñado bajo una arquitectura modular desacoplada containerizada mediante Docker Compose:

```text
├── api/                    # Backend en Python (FastAPI)
│   ├── main.py             # Punto de entrada de la API
│   ├── planos_router.py    # Endpoints para operaciones sobre planos y catálogo
│   ├── planos_worker.py    # Procesamiento asíncrono y workers en segundo plano
│   ├── tasks.py            # Gestión de tareas y persistencia
│   ├── preprocessing.py    # Preprocesamiento, recorte HD y mejora con Pillow
│   ├── vision_client.py   # Integración con Ollama (Qwen2.5-VL 3B)
│   ├── storage_client.py  # Cliente para Supabase Storage
│   ├── minio_client.py    # Cliente para MinIO (almacenamiento de objetos S3)
│   ├── db_client.py       # Conexión e inserción en MongoDB
│   ├── database.py         # Configuración y ORM para PostgreSQL
│   ├── models.py           # Modelos de datos / ORM
│   └── schemas.py          # Esquemas Pydantic y DTOs
│
├── front/                  # Frontend Web y Servidor Web
│   ├── js/                 # Flujos de uso (cu-cargar, cu-consultar, cu-validar, cu-modificar)
│   ├── nginx.conf          # Configuración del servidor Nginx
│   └── *.html / *.css      # Vistas e interfaz de usuario
│
├── docker-compose.yml      # Orquestación de servicios (API, Ollama, Postgres, MinIO, Front)
├── Dockerfile              # Construcción de la imagen del backend
└── requirements.txt        # Dependencias de Python
```

---

## Tecnologías Utilizadas

- Backend: Python 3.14+, FastAPI, Pydantic, SQLAlchemy.
- IA / Visión por Computadora: Qwen2.5-VL 3B servido por Ollama, Pillow (autocontrast y sharpness).
- Bases de Datos y Almacenamiento:
  - PostgreSQL: Catálogo general de planos, estados e historial de modificaciones.
  - MinIO: Almacenamiento interno de objetos S3 (bucket planos).
  - Supabase Storage: Almacenamiento público de planos escaneados (bucket planos_escaneados).
  - MongoDB: Registro documental de extracciones completas por IA (planos_db).
- Frontend: HTML5, CSS3, JavaScript (Vanilla Modular), Nginx.
- Despliegue: Docker y Docker Compose.

---

## Despliegue Rápido con Docker Compose

1. Clonar el repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd PlanosHistoricosOrganizacion
   ```

2. Configurar variables de entorno:
   Copiar el archivo de ejemplo .env.example para crear la configuración local .env:
   ```bash
   cp .env.example .env
   ```

3. Iniciar los servicios:
   ```bash
   docker compose up -d
   ```

4. Verificar descarga del modelo de visión:
   La primera vez, el servicio ollama-pull descarga automáticamente el modelo (~2-3 GB). Se puede verificar el estado ejecutando:
   ```bash
   docker exec -it ollama ollama list
   ```
   O monitorear los logs del proceso:
   ```bash
   docker compose logs -f ollama-pull
   ```

5. URLs de Acceso:
   - Aplicación Web: http://localhost:8080
   - Documentación de la API (Swagger UI): http://localhost:8000/docs
   - Consola de MinIO: http://localhost:9001
   - PostgreSQL: localhost:5432

---

## Uso de la API

La API aguarda hasta 300 segundos por la respuesta de Ollama (OLLAMA_TIMEOUT).

### Procesamiento Asíncrono (Recomendado)

1. Enviar un plano a procesar:
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

2. Consultar estado y resultado de la tarea:
   ```bash
   curl http://localhost:8000/tareas/e1c97abb-85b4-4ab3-ba57-86858af023da
   ```
   Respuesta completada (status: "completed"):
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

## Pipeline de Procesamiento con IA (2 Pasos con Grounding)

El procesamiento de planos combina las normas de dibujo técnico (IRAM 4504 e ISO 7200) con las capacidades de Grounding y Detección de Objetos del modelo Qwen2.5-VL 3B.

### El Desafío en Planos de Gran Formato
Los planos digitalizados suelen tener resoluciones elevadas (ej. 4000×3000 px). Si se envía la imagen completa reducida a un modelo de visión, las tipografías pequeñas (año, cotas, firmas, escala y nomenclatura catastral) pierden definición e inteligibilidad.

Por norma técnica, la información legal y catastral se ubica reglamentariamente en el cajetín, carimbo o rótulo, ubicado en la esquina inferior derecha. Por ende, el sistema realiza un procesamiento estratégico en dos pasos:

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

Se genera una vista previa optimizada y se solicita al modelo detectar la caja delimitadora (Bounding Box) del cuadro técnico.

- Prompt utilizado:
  ```text
  Detecta el cajetín, carimbo o cuadro de datos técnicos del plano.
  Devuelve únicamente un JSON con la bounding box en formato [ymin, xmin, ymax, xmax] normalizado de 0 a 1000.
  Por normas técnicas IRAM e ISO, el cajetín suele encontrarse en la zona inferior derecha del plano.
  Ejemplo de respuesta: {"bbox_2d": [750, 700, 990, 990]}
  ```
- Structured Output: Forzado mediante el esquema Pydantic en Ollama (`format: CajetinBBoxSchema.model_json_schema()`).
- Fallback IRAM 4504: Si la detección falla o la caja es anómala, el sistema aplica automáticamente la norma IRAM 4504 (`[600, 500, 1000, 1000]`).

---

### Recorte en Alta Resolución (Crop y Preprocesamiento)

Implementado en `api/preprocessing.py` (`crop_cajetin_from_bbox`):

1. Desnormalización: Conversión de coordenadas `[0..1000]` a píxeles exactos de la imagen original en alta resolución.
2. Padding: Expansión del 2% en ancho y alto para evitar cortar sellos o márgenes.
3. Optimización con Pillow (`preprocess_cajetin`):
   - Autocontraste (`ImageOps.autocontrast`): Recupera trazos en tinta descolorida o papel oxidado.
   - Realce de Nitidez (`ImageEnhance.Sharpness`): Resalta números catastrales, detalles finos y firmas.

---

### Paso 2: Extracción Estructurada de Datos Técnicos en HD

Se envía únicamente el recorte del cajetín en máxima resolución a Qwen2.5-VL con el esquema JSON completo de `PlanoHistorico` (`api/schemas.py`).

- Campos del Esquema (`PlanoHistorico`):
  - `texto_extraido`: Transcripción integral del texto legible visible (OCR).
  - `arquitecto`: Autor, proyectista o profesional firmante.
  - `anio`: Año del proyecto o confección (4 dígitos).
  - `titulo`: Nombre de la obra, proyecto o designación de la lámina.
  - `ubicacion`: Localidad, dirección o datos catastrales.
  - `escala`: Relación de escala métrica (ej. 1:100).
  - `tipo_de_plano`: Planta, corte, fachada, relevamiento, etc.
  - `material_soporte`: Sustrato explícito (papel vegetal, tela, etc.).
  - `notas`: Referencias a expedientes, sellos municipales o aprobaciones.

---

## Gestión del Catálogo y Endpoints

### Endpoints del Catálogo (PostgreSQL + MinIO)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/planos` | Multipart: `archivo` + datos opcionales. Sube a MinIO, crea el plano en estado `pendiente` y dispara la IA en segundo plano (`ia_estado=procesando`). |
| `GET` | `/planos` | Listado con filtros por `estado` (`?estado=validado&estado=sin_ubicacion`) y búsqueda por texto `q`. |
| `GET` | `/planos/{id}` | Detalle completo del plano e historial de modificaciones. |
| `GET` | `/planos/{id}/archivo` | Descarga el archivo original (imagen o PDF). |
| `GET` | `/planos/{id}/preview` | Devuelve la imagen de previsualización (JPEG). |
| `PUT` | `/planos/{id}/validar` | Valida metadatos revisados + `parcela`. Asigna estado `validado` o `sin_ubicacion`. |
| `PUT` | `/planos/{id}/modificar` | Actualiza metadatos + `parcela` + `motivo` (obligatorio). Registra el cambio en el historial. |

---

## Variables de Entorno (`.env`)

```env
# MongoDB
MONGODB_URI=mongodb+srv://usuario:password@cluster.mongodb.net/?appName=...

# Supabase
SUPABASE_URL=https://<proyecto>.supabase.co
SUPABASE_KEY=<service_role_key>

# PostgreSQL
POSTGRES_USER=planos
POSTGRES_PASSWORD=planos
POSTGRES_DB=planos_db
```

Nota: La clave `SUPABASE_KEY` debe ser la **service_role key** para omitir las políticas RLS durante la subida desde el backend.