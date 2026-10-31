# Esquema `tramitacion` (backend del otro grupo)

Copia sin modificar de `db/tramitacion.sql` y `db/extensiones_backend.sql` del proyecto
`ingenieria-de-software-2-backend`. El prefijo numérico fija el orden en que Postgres los
ejecuta desde `/docker-entrypoint-initdb.d`, y solo lo hace al crear un volumen vacío.

Nuestro backend solo lee `tramitacion.localidades` y `tramitacion.inmuebles`: al cargar,
validar o modificar un plano, `planos.planos.id_inmueble` apunta al inmueble con la misma
nomenclatura en la localidad `LOCALIDAD_PLANOS` (La Plata por defecto), si existe.
