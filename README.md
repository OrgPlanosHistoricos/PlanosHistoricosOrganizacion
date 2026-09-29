# API de Reconocimiento de Planos Históricos

Extrae datos (arquitecto, año, ubicación, etc.) de planos históricos
escaneados usando el modelo de visión Qwen2.5-VL 3B servido por Ollama,
y los devuelve en JSON estructurado.

## Uso

```bash
docker compose up -d
```

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

### Modo síncrono (espera la respuesta en la misma petición):
```bash
curl -X POST "http://localhost:8000/procesar-plano?sync=true" \
  -F "archivo=@/ruta/a/tu/plano.jpg"
```

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
Se debe desacargar un modelo en ollama (configurado actualmente qwen2.5vl:3b que pesa aprox 3.2 gb) se peude consultar el estado de la descarga en cualquier momento con:

```bash
docker exec -it ollama ollama list
```

el ingreso a la app debe hacerse desde http://localhost:8080 en el navegador. Sino se bloquea el uso de la API de reconocimiento de imagenes.
Los formatos admitidos actualmente son solamente JPEG, PNG .... NO PDF!!!

El procesamiento por CPU tarda de 60 a 90 segundos.

.
