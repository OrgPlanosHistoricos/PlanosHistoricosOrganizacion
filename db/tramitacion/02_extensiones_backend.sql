-- Complemento del backend sobre db/tramitacion.sql (no lo modifica).
-- Se ejecuta DESPUÉS de tramitacion.sql: depende del esquema `tramitacion`.
--
-- Agrega solo lo que el script base no cubre:
--   1. tramitacion.notificaciones: avisos in-app que genera el backend al
--      cambiar el estado de un expediente.
--   2. public.tramites_digitales: entidad de la consigna (Funciones 1 a 4).

BEGIN;

CREATE TABLE IF NOT EXISTS tramitacion.notificaciones (
    id_notificacion integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_notificaciones PRIMARY KEY,
    id_expediente integer NOT NULL CONSTRAINT fk_notificaciones_expedientes REFERENCES tramitacion.expedientes,
    rol_destino varchar(20) NOT NULL,
    destinatario_externo_id varchar(64),
    mensaje varchar(500) NOT NULL,
    fecha_hora timestamp(0) NOT NULL DEFAULT now(),
    leido boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_notificaciones_rol ON tramitacion.notificaciones (rol_destino, leido);

CREATE TABLE IF NOT EXISTS public.tramites_digitales (
    id_tramite  BIGINT PRIMARY KEY,
    id_usuario  INTEGER NOT NULL,
    accion      VARCHAR(100) NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tramites_usuario ON public.tramites_digitales (id_usuario);

COMMIT;
