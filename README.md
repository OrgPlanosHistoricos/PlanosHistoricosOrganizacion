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

```bash
curl -X POST http://localhost:8000/procesar-plano \
  -F "archivo=@/ruta/a/tu/plano.jpg"
```

Respuesta esperada:

```json
{
  "fecha_procesamiento": "2026-09-29T20:14:03.512Z",
  "archivo": {
    "nombre_original": "plano.jpg",
    "supabase_url": "https://<proyecto>.supabase.co/storage/v1/object/public/planos_escaneados/<uuid>.jpg"
  },
  "extraccion_qwen": {
    "arquitecto": "Francisco Salamone",
    "anio": 1936,
    "titulo": "Palacio Municipal de Azul",
    "ubicacion": "Azul, Buenos Aires",
    "escala": "1:50",
    "tipo_de_plano": "fachada principal",
    "material_soporte": "papel tela",
    "notas": null
  }
}
```

## Almacenamiento: Supabase + MongoDB

_Agregado: 2026-09-29_

Cada plano procesado se persiste en dos lugares:

- **Supabase Storage** (bucket `planos_escaneados`): guarda el archivo
  original que subió el usuario y expone su URL pública.
- **MongoDB** (base `planos_db`, colección `extracciones`): guarda el
  documento final devuelto por la API (fecha de procesamiento, datos
  del archivo y la extracción de Qwen).

El flujo en `api/main.py` (`POST /procesar-plano`) es: recibe el
archivo → lo sube a Supabase y obtiene la URL pública
(`api/storage_client.py`) → preprocesa la imagen y la manda a Qwen vía
Ollama (sin cambios respecto a antes) → arma el documento con el
esquema `DocumentoExtraccion` (`api/schemas.py`) → lo inserta en Mongo
(`api/db_client.py`) → devuelve el documento completo.

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
