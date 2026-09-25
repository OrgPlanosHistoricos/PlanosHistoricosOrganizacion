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
  "arquitecto": "Francisco Salamone",
  "anio": 1936,
  "titulo": "Palacio Municipal de Azul",
  "ubicacion": "Azul, Buenos Aires",
  "escala": "1:50",
  "tipo_de_plano": "fachada principal",
  "material_soporte": "papel tela",
  "notas": null
}
```

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
