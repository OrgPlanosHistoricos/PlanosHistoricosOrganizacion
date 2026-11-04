# Esquema `tramitacion` (backend del otro grupo)

Copia sin modificar de `db/tramitacion.sql` y `db/extensiones_backend.sql` del proyecto
`ingenieria-de-software-2-backend`. Mientras no nos conectemos a su base, lo cargamos a mano
y una sola vez en nuestro Postgres de Supabase (el prefijo numérico fija el orden):

```bash
docker run --rm -v "$PWD/db/tramitacion:/sql:ro" postgres:17-alpine \
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f /sql/01_tramitacion.sql -f /sql/02_extensiones_backend.sql
```

La API no arranca si falta `tramitacion.inmuebles`. Nuestras tablas las crea ella misma en el
esquema `planos`.

Nuestro backend solo lee `tramitacion.localidades` y `tramitacion.inmuebles`: al cargar,
validar o modificar un plano, `planos.planos.id_inmueble` apunta al inmueble con la misma
nomenclatura en la localidad `LOCALIDAD_PLANOS` (La Plata por defecto), si existe.
