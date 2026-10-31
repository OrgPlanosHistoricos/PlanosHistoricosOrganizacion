DO $$
BEGIN
    EXECUTE format('ALTER DATABASE %I SET timezone TO %L', current_database(), 'America/Argentina/Buenos_Aires');
END $$;

BEGIN;

CREATE SCHEMA tramitacion;

CREATE TABLE tramitacion.localidades (
    id_localidad integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_localidades PRIMARY KEY,
    nombre varchar(120) NOT NULL,
    codigo varchar(4) NOT NULL
        CONSTRAINT uq_localidades_codigo UNIQUE
        CONSTRAINT ck_localidades_codigo_formato CHECK (codigo ~ '^[A-Z]{2,4}$'),
    activo boolean NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX ux_localidades_nombre ON tramitacion.localidades (lower(nombre));

CREATE TABLE tramitacion.tipos_obra (
    id_tipo_obra integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_tipos_obra PRIMARY KEY,
    nombre varchar(120) NOT NULL CONSTRAINT uq_tipos_obra_nombre UNIQUE,
    descripcion varchar(255),
    activo boolean NOT NULL DEFAULT true
);

CREATE TABLE tramitacion.requisitos (
    id_requisito integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_requisitos PRIMARY KEY,
    descripcion varchar(255) NOT NULL CONSTRAINT uq_requisitos_descripcion UNIQUE,
    categoria varchar(30) NOT NULL
        CONSTRAINT ck_requisitos_categoria CHECK (categoria IN ('Documentación', 'Sellos', 'Habilitaciones', 'Código de Urbanismo'))
);

CREATE TABLE tramitacion.requisitos_checklist (
    id_localidad integer NOT NULL CONSTRAINT fk_requisitos_checklist_localidades REFERENCES tramitacion.localidades,
    id_tipo_obra integer NOT NULL CONSTRAINT fk_requisitos_checklist_tipos_obra REFERENCES tramitacion.tipos_obra,
    id_requisito integer NOT NULL CONSTRAINT fk_requisitos_checklist_requisitos REFERENCES tramitacion.requisitos,
    obligatorio boolean NOT NULL DEFAULT true,
    activo boolean NOT NULL DEFAULT true,
    CONSTRAINT pk_requisitos_checklist PRIMARY KEY (id_localidad, id_tipo_obra, id_requisito)
);

CREATE TABLE tramitacion.solicitantes (
    id_solicitante integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_solicitantes PRIMARY KEY,
    nombre_razon_social varchar(200) NOT NULL,
    tipo_identificacion varchar(4) NOT NULL
        CONSTRAINT ck_solicitantes_tipo_identificacion CHECK (tipo_identificacion IN ('DNI', 'CUIT', 'CUIL')),
    numero_identificacion varchar(11) NOT NULL
        CONSTRAINT ck_solicitantes_numero_formato CHECK (numero_identificacion ~ '^[0-9]{7,11}$'),
    activo boolean NOT NULL DEFAULT true,
    CONSTRAINT uq_solicitantes_identificacion UNIQUE (tipo_identificacion, numero_identificacion)
);

CREATE TABLE tramitacion.inmuebles (
    id_inmueble integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_inmuebles PRIMARY KEY,
    nomenclatura_catastral varchar(60) NOT NULL
        CONSTRAINT ck_inmuebles_nomenclatura_formato CHECK (nomenclatura_catastral ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'),
    id_localidad integer NOT NULL CONSTRAINT fk_inmuebles_localidades REFERENCES tramitacion.localidades,
    activo boolean NOT NULL DEFAULT true,
    CONSTRAINT uq_inmuebles_nomenclatura UNIQUE (id_localidad, nomenclatura_catastral)
);

CREATE TABLE tramitacion.expedientes (
    id_expediente integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_expedientes PRIMARY KEY,
    numero_expediente varchar(20) NOT NULL
        CONSTRAINT uq_expedientes_numero UNIQUE
        CONSTRAINT ck_expedientes_numero_formato CHECK (numero_expediente ~ '^EXP-[A-Z]{2,4}-[0-9]{4}-[0-9]{6}$'),
    id_profesional_externo varchar(64) NOT NULL,
    id_solicitante integer NOT NULL CONSTRAINT fk_expedientes_solicitantes REFERENCES tramitacion.solicitantes,
    id_inmueble integer NOT NULL CONSTRAINT fk_expedientes_inmuebles REFERENCES tramitacion.inmuebles,
    id_tipo_obra integer NOT NULL CONSTRAINT fk_expedientes_tipos_obra REFERENCES tramitacion.tipos_obra,
    estado_actual varchar(20) NOT NULL DEFAULT 'Presentado'
        CONSTRAINT ck_expedientes_estado CHECK (estado_actual IN ('Presentado', 'En Revisión', 'Observado', 'Conforme', 'Aprobado', 'Rechazado')),
    fecha_presentacion timestamp(0) NOT NULL DEFAULT now(),
    fecha_vencimiento_permiso date,
    activo boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_expedientes_vencimiento CHECK (fecha_vencimiento_permiso IS NULL OR fecha_vencimiento_permiso > fecha_presentacion::date)
);
CREATE INDEX ix_expedientes_profesional ON tramitacion.expedientes (id_profesional_externo);

CREATE TABLE tramitacion.documentos (
    id_documento integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_documentos PRIMARY KEY,
    id_expediente integer NOT NULL CONSTRAINT fk_documentos_expedientes REFERENCES tramitacion.expedientes,
    id_requisito integer NOT NULL CONSTRAINT fk_documentos_requisitos REFERENCES tramitacion.requisitos,
    version smallint NOT NULL CONSTRAINT ck_documentos_version CHECK (version >= 1),
    nombre_archivo varchar(255) NOT NULL,
    formato varchar(10) NOT NULL
        CONSTRAINT ck_documentos_formato CHECK (formato IN ('PDF', 'AutoCAD 2D', 'Otro')),
    hash char(64) NOT NULL CONSTRAINT ck_documentos_hash_formato CHECK (hash ~ '^[0-9a-f]{64}$'),
    estado_documento varchar(10) NOT NULL DEFAULT 'Vigente'
        CONSTRAINT ck_documentos_estado CHECK (estado_documento IN ('Vigente', 'Caducado')),
    CONSTRAINT uq_documentos_version UNIQUE (id_expediente, id_requisito, version)
);
CREATE UNIQUE INDEX ux_documentos_un_vigente ON tramitacion.documentos (id_expediente, id_requisito) WHERE estado_documento = 'Vigente';

CREATE SEQUENCE tramitacion.seq_log;

CREATE TABLE tramitacion.historial_estados (
    id_historial integer DEFAULT nextval('tramitacion.seq_log') CONSTRAINT pk_historial_estados PRIMARY KEY,
    id_expediente integer NOT NULL CONSTRAINT fk_historial_estados_expedientes REFERENCES tramitacion.expedientes,
    estado_anterior varchar(20)
        CONSTRAINT ck_historial_estados_anterior CHECK (estado_anterior IN ('Presentado', 'En Revisión', 'Observado', 'Conforme', 'Aprobado', 'Rechazado')),
    estado_nuevo varchar(20) NOT NULL
        CONSTRAINT ck_historial_estados_nuevo CHECK (estado_nuevo IN ('Presentado', 'En Revisión', 'Observado', 'Conforme', 'Aprobado', 'Rechazado')),
    fecha_hora timestamp(0) NOT NULL DEFAULT now(),
    actor_externo_id varchar(64) NOT NULL,
    motivo varchar(500),
    CONSTRAINT ck_historial_estados_motivo CHECK (estado_nuevo NOT IN ('Observado', 'Rechazado') OR (motivo IS NOT NULL AND length(trim(motivo)) > 0))
);

CREATE TABLE tramitacion.historial_documentos (
    id_historial_doc integer DEFAULT nextval('tramitacion.seq_log') CONSTRAINT pk_historial_documentos PRIMARY KEY,
    id_documento integer NOT NULL CONSTRAINT fk_historial_documentos_documentos REFERENCES tramitacion.documentos,
    accion varchar(15) NOT NULL
        CONSTRAINT ck_historial_documentos_accion CHECK (accion IN ('Carga', 'Observación', 'Caducidad')),
    detalle varchar(500),
    fecha_hora timestamp(0) NOT NULL DEFAULT now(),
    actor_externo_id varchar(64) NOT NULL,
    CONSTRAINT ck_historial_documentos_observacion_detalle CHECK (accion <> 'Observación' OR (detalle IS NOT NULL AND length(trim(detalle)) > 0))
);

CREATE TABLE tramitacion.checklist_expediente (
    id_checklist_exp integer GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_checklist_expediente PRIMARY KEY,
    id_expediente integer NOT NULL CONSTRAINT fk_checklist_expediente_expedientes REFERENCES tramitacion.expedientes,
    id_requisito integer NOT NULL CONSTRAINT fk_checklist_expediente_requisitos REFERENCES tramitacion.requisitos,
    cumplido boolean,
    observacion varchar(500),
    id_revisor_externo varchar(64),
    fecha_verificacion timestamp(0),
    CONSTRAINT uq_checklist_expediente_requisito UNIQUE (id_expediente, id_requisito),
    CONSTRAINT ck_checklist_expediente_verificacion CHECK (
        (cumplido IS NULL AND id_revisor_externo IS NULL AND fecha_verificacion IS NULL)
        OR (cumplido IS NOT NULL AND id_revisor_externo IS NOT NULL AND fecha_verificacion IS NOT NULL)
    ),
    CONSTRAINT ck_checklist_expediente_observacion CHECK (cumplido IS NOT FALSE OR (observacion IS NOT NULL AND length(trim(observacion)) > 0))
);

INSERT INTO tramitacion.localidades (nombre, codigo) VALUES
    ('La Plata', 'LP'),
    ('San Isidro', 'SI'),
    ('Quilmes', 'QUI'),
    ('Vicente López', 'VL'),
    ('Mar del Plata', 'MDQ'),
    ('Arrecifes', 'ACF'),
    ('Ensenada', 'ENS'),
    ('Lomas de Zamora', 'LDZ'),
    ('Pinamar', 'PNM'),
    ('Villa Gesell', 'VG'),
    ('Bahía Blanca', 'BB'),
    ('Tandil', 'TDL'),
    ('Tigre', 'TIG');

INSERT INTO tramitacion.tipos_obra (nombre) VALUES
    ('Obra Nueva'),
    ('Ampliación'),
    ('Refacción'),
    ('Demolición'),
    ('Regularización (Empadronamiento)');

INSERT INTO tramitacion.requisitos (descripcion, categoria) VALUES
    ('Plano de obra (PDF)', 'Documentación'),
    ('Plano de obra (formato AutoCAD 2D)', 'Documentación'),
    ('Copia de la escritura del terreno', 'Documentación'),
    ('Certificado urbanístico', 'Documentación'),
    ('Comprobante de pago de derechos de construcción', 'Documentación'),
    ('Sellos profesionales exigidos', 'Sellos'),
    ('Habilitaciones previas del inmueble', 'Habilitaciones'),
    ('Cumplimiento de restricciones del Código de Urbanismo', 'Código de Urbanismo');

INSERT INTO tramitacion.requisitos_checklist (id_localidad, id_tipo_obra, id_requisito)
SELECT l.id_localidad, t.id_tipo_obra, r.id_requisito
FROM tramitacion.localidades l
CROSS JOIN tramitacion.tipos_obra t
CROSS JOIN tramitacion.requisitos r;

COMMIT;

BEGIN;

INSERT INTO tramitacion.solicitantes (nombre_razon_social, tipo_identificacion, numero_identificacion) VALUES
    ('Diego Martínez', 'DNI', '28554112'),
    ('Carla Ibáñez', 'DNI', '31220987'),
    ('Hugo Beltrán', 'DNI', '19887334'),
    ('Estudio Balda S.A.', 'CUIT', '30712233456'),
    ('Marina Costa', 'DNI', '40115220'),
    ('Jorge Peralta', 'DNI', '22998410');

INSERT INTO tramitacion.inmuebles (nomenclatura_catastral, id_localidad)
SELECT d.nomenclatura, l.id_localidad
FROM (VALUES
    ('11-18-12', 'LP'),
    ('9-76-1', 'SI'),
    ('18-24-18', 'QUI'),
    ('40-171-10', 'VL'),
    ('26-173-12', 'TIG'),
    ('4-29-20', 'LP')
) AS d (nomenclatura, codigo)
JOIN tramitacion.localidades l ON l.codigo = d.codigo;

INSERT INTO tramitacion.expedientes (numero_expediente, id_profesional_externo, id_solicitante, id_inmueble, id_tipo_obra, estado_actual, fecha_presentacion, fecha_vencimiento_permiso)
SELECT d.numero, 'prof-lfernandez', s.id_solicitante, i.id_inmueble, t.id_tipo_obra, d.estado, d.fecha::timestamp, d.vencimiento::date
FROM (VALUES
    ('EXP-LP-2026-000002', '28554112', '11-18-12', 'LP', 'Obra Nueva', 'Aprobado', '2026-08-14 09:00:00', '2028-08-19'),
    ('EXP-SI-2026-000001', '31220987', '9-76-1', 'SI', 'Ampliación', 'Observado', '2026-08-20 10:15:00', NULL),
    ('EXP-QUI-2026-000001', '19887334', '18-24-18', 'QUI', 'Regularización (Empadronamiento)', 'En Revisión', '2026-08-05 08:30:00', NULL),
    ('EXP-VL-2026-000001', '30712233456', '40-171-10', 'VL', 'Demolición', 'Conforme', '2026-08-25 09:00:00', NULL),
    ('EXP-TIG-2026-000001', '40115220', '26-173-12', 'TIG', 'Refacción', 'Presentado', '2026-09-08 16:45:00', NULL),
    ('EXP-LP-2026-000001', '22998410', '4-29-20', 'LP', 'Ampliación', 'Rechazado', '2026-08-01 09:00:00', NULL)
) AS d (numero, documento, nomenclatura, codigo, tipo_obra, estado, fecha, vencimiento)
JOIN tramitacion.solicitantes s ON s.numero_identificacion = d.documento
JOIN tramitacion.localidades l ON l.codigo = d.codigo
JOIN tramitacion.inmuebles i ON i.nomenclatura_catastral = d.nomenclatura AND i.id_localidad = l.id_localidad
JOIN tramitacion.tipos_obra t ON t.nombre = d.tipo_obra
ORDER BY d.fecha;

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id)
SELECT id_expediente, NULL, 'Presentado', fecha_presentacion, id_profesional_externo
FROM tramitacion.expedientes
ORDER BY id_expediente;

INSERT INTO tramitacion.documentos (id_expediente, id_requisito, version, nombre_archivo, formato, hash)
SELECT e.id_expediente, r.id_requisito, 1,
    CASE r.descripcion
        WHEN 'Plano de obra (PDF)' THEN 'plano_obra.pdf'
        WHEN 'Plano de obra (formato AutoCAD 2D)' THEN 'plano_obra.dwg'
        WHEN 'Copia de la escritura del terreno' THEN 'escritura.pdf'
        WHEN 'Certificado urbanístico' THEN 'certificado_urbanistico.pdf'
        WHEN 'Comprobante de pago de derechos de construcción' THEN 'comprobante_pago.pdf'
    END,
    CASE WHEN r.descripcion = 'Plano de obra (formato AutoCAD 2D)' THEN 'AutoCAD 2D' ELSE 'PDF' END,
    encode(sha256(convert_to(e.numero_expediente || ' ' || r.descripcion || ' v1', 'UTF8')), 'hex')
FROM tramitacion.expedientes e
CROSS JOIN tramitacion.requisitos r
WHERE r.categoria = 'Documentación'
ORDER BY e.id_expediente, r.id_requisito;

INSERT INTO tramitacion.historial_documentos (id_documento, accion, fecha_hora, actor_externo_id)
SELECT d.id_documento, 'Carga', e.fecha_presentacion, e.id_profesional_externo
FROM tramitacion.documentos d
JOIN tramitacion.expedientes e ON e.id_expediente = d.id_expediente
ORDER BY d.id_documento;

INSERT INTO tramitacion.checklist_expediente (id_expediente, id_requisito)
SELECT e.id_expediente, rc.id_requisito
FROM tramitacion.expedientes e
JOIN tramitacion.inmuebles i ON i.id_inmueble = e.id_inmueble
JOIN tramitacion.requisitos_checklist rc ON rc.id_localidad = i.id_localidad AND rc.id_tipo_obra = e.id_tipo_obra
WHERE rc.activo
ORDER BY e.id_expediente, rc.id_requisito;

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id, motivo)
SELECT e.id_expediente, 'Presentado', 'Conforme', '2026-08-04 11:00:00', 'rev-msosa',
    'Documentación presentada en término, se eleva a Autoridad con reserva sobre altura declarada.'
FROM tramitacion.expedientes e WHERE e.numero_expediente = 'EXP-LP-2026-000001';

UPDATE tramitacion.checklist_expediente ce
SET cumplido = (r.descripcion <> 'Cumplimiento de restricciones del Código de Urbanismo'),
    observacion = CASE WHEN r.descripcion = 'Cumplimiento de restricciones del Código de Urbanismo'
                       THEN 'La altura declarada excede la máxima permitida para el distrito.' END,
    id_revisor_externo = 'rev-msosa',
    fecha_verificacion = '2026-08-04 11:00:00'
FROM tramitacion.expedientes e, tramitacion.requisitos r
WHERE e.id_expediente = ce.id_expediente AND r.id_requisito = ce.id_requisito
  AND e.numero_expediente = 'EXP-LP-2026-000001';

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id, motivo)
SELECT e.id_expediente, 'Conforme', 'Rechazado', '2026-08-07 10:30:00', 'aut-vprieto',
    'La ampliación excede la altura máxima permitida por el Código de Urbanismo para el distrito. No corresponde aprobar sin variación de zonificación.'
FROM tramitacion.expedientes e WHERE e.numero_expediente = 'EXP-LP-2026-000001';

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id, motivo)
SELECT e.id_expediente, 'Presentado', 'Observado', '2026-08-08 10:00:00', 'rev-msosa',
    'El plano no refleja el estado real de la construcción preexistente relevada in situ.'
FROM tramitacion.expedientes e WHERE e.numero_expediente = 'EXP-QUI-2026-000001';

INSERT INTO tramitacion.historial_documentos (id_documento, accion, detalle, fecha_hora, actor_externo_id)
SELECT d.id_documento, 'Observación', 'El plano no refleja el estado real de la construcción preexistente relevada in situ.', '2026-08-08 10:00:00', 'rev-msosa'
FROM tramitacion.documentos d
JOIN tramitacion.expedientes e ON e.id_expediente = d.id_expediente
JOIN tramitacion.requisitos r ON r.id_requisito = d.id_requisito
WHERE e.numero_expediente = 'EXP-QUI-2026-000001' AND r.descripcion = 'Plano de obra (PDF)';

UPDATE tramitacion.documentos d SET estado_documento = 'Caducado'
FROM tramitacion.expedientes e, tramitacion.requisitos r
WHERE e.id_expediente = d.id_expediente AND r.id_requisito = d.id_requisito
  AND e.numero_expediente = 'EXP-QUI-2026-000001' AND r.descripcion = 'Plano de obra (PDF)' AND d.version = 1;

INSERT INTO tramitacion.historial_documentos (id_documento, accion, detalle, fecha_hora, actor_externo_id)
SELECT d.id_documento, 'Caducidad', 'Reemplazado por la versión 2', '2026-08-12 14:15:00', 'prof-lfernandez'
FROM tramitacion.documentos d
JOIN tramitacion.expedientes e ON e.id_expediente = d.id_expediente
JOIN tramitacion.requisitos r ON r.id_requisito = d.id_requisito
WHERE e.numero_expediente = 'EXP-QUI-2026-000001' AND r.descripcion = 'Plano de obra (PDF)' AND d.version = 1;

INSERT INTO tramitacion.documentos (id_expediente, id_requisito, version, nombre_archivo, formato, hash)
SELECT e.id_expediente, r.id_requisito, 2, 'plano_obra_corregido.pdf', 'PDF',
    encode(sha256(convert_to(e.numero_expediente || ' ' || r.descripcion || ' v2', 'UTF8')), 'hex')
FROM tramitacion.expedientes e, tramitacion.requisitos r
WHERE e.numero_expediente = 'EXP-QUI-2026-000001' AND r.descripcion = 'Plano de obra (PDF)';

INSERT INTO tramitacion.historial_documentos (id_documento, accion, fecha_hora, actor_externo_id)
SELECT d.id_documento, 'Carga', '2026-08-12 14:15:00', 'prof-lfernandez'
FROM tramitacion.documentos d
JOIN tramitacion.expedientes e ON e.id_expediente = d.id_expediente
JOIN tramitacion.requisitos r ON r.id_requisito = d.id_requisito
WHERE e.numero_expediente = 'EXP-QUI-2026-000001' AND r.descripcion = 'Plano de obra (PDF)' AND d.version = 2;

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id, motivo)
SELECT e.id_expediente, 'Observado', 'En Revisión', '2026-08-12 14:15:00', 'prof-lfernandez',
    'Se sube nueva versión del plano en respuesta a la observación.'
FROM tramitacion.expedientes e WHERE e.numero_expediente = 'EXP-QUI-2026-000001';

UPDATE tramitacion.checklist_expediente ce
SET cumplido = true, id_revisor_externo = 'rev-msosa', fecha_verificacion = '2026-08-08 10:00:00'
FROM tramitacion.expedientes e, tramitacion.requisitos r
WHERE e.id_expediente = ce.id_expediente AND r.id_requisito = ce.id_requisito
  AND e.numero_expediente = 'EXP-QUI-2026-000001' AND r.descripcion <> 'Plano de obra (PDF)';

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id, motivo)
SELECT e.id_expediente, 'Presentado', 'Conforme', '2026-08-16 11:20:00', 'rev-msosa',
    'Documentación técnica completa. Cumple restricciones de altura y FOS vigentes para la zona.'
FROM tramitacion.expedientes e WHERE e.numero_expediente = 'EXP-LP-2026-000002';

UPDATE tramitacion.checklist_expediente ce
SET cumplido = true, id_revisor_externo = 'rev-msosa', fecha_verificacion = '2026-08-16 11:20:00'
FROM tramitacion.expedientes e
WHERE e.id_expediente = ce.id_expediente AND e.numero_expediente = 'EXP-LP-2026-000002';

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id, motivo)
SELECT e.id_expediente, 'Conforme', 'Aprobado', '2026-08-19 15:05:00', 'aut-vprieto',
    'Resolución N° 118/2026: se aprueba el proyecto de obra nueva.'
FROM tramitacion.expedientes e WHERE e.numero_expediente = 'EXP-LP-2026-000002';

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id, motivo)
SELECT e.id_expediente, 'Presentado', 'Observado', '2026-08-23 09:40:00', 'rev-msosa',
    'Falta la firma y sello profesional en el plano PDF de la ampliación (folio 3). El plano AutoCAD no coincide con la superficie declarada.'
FROM tramitacion.expedientes e WHERE e.numero_expediente = 'EXP-SI-2026-000001';

INSERT INTO tramitacion.historial_documentos (id_documento, accion, detalle, fecha_hora, actor_externo_id)
SELECT d.id_documento, 'Observación',
    CASE r.descripcion
        WHEN 'Plano de obra (PDF)' THEN 'Falta la firma y sello profesional (folio 3).'
        ELSE 'No coincide con la superficie declarada.'
    END,
    '2026-08-23 09:40:00', 'rev-msosa'
FROM tramitacion.documentos d
JOIN tramitacion.expedientes e ON e.id_expediente = d.id_expediente
JOIN tramitacion.requisitos r ON r.id_requisito = d.id_requisito
WHERE e.numero_expediente = 'EXP-SI-2026-000001'
  AND r.descripcion IN ('Plano de obra (PDF)', 'Plano de obra (formato AutoCAD 2D)')
ORDER BY r.id_requisito;

UPDATE tramitacion.checklist_expediente ce
SET cumplido = r.descripcion NOT IN ('Plano de obra (PDF)', 'Plano de obra (formato AutoCAD 2D)'),
    observacion = CASE r.descripcion
        WHEN 'Plano de obra (PDF)' THEN 'Falta la firma y sello profesional (folio 3).'
        WHEN 'Plano de obra (formato AutoCAD 2D)' THEN 'No coincide con la superficie declarada.'
    END,
    id_revisor_externo = 'rev-msosa',
    fecha_verificacion = '2026-08-23 09:40:00'
FROM tramitacion.expedientes e, tramitacion.requisitos r
WHERE e.id_expediente = ce.id_expediente AND r.id_requisito = ce.id_requisito
  AND e.numero_expediente = 'EXP-SI-2026-000001';

INSERT INTO tramitacion.historial_estados (id_expediente, estado_anterior, estado_nuevo, fecha_hora, actor_externo_id, motivo)
SELECT e.id_expediente, 'Presentado', 'Conforme', '2026-08-28 12:00:00', 'rev-msosa',
    'Documentación en regla. No se detectan afectaciones a construcciones linderas.'
FROM tramitacion.expedientes e WHERE e.numero_expediente = 'EXP-VL-2026-000001';

UPDATE tramitacion.checklist_expediente ce
SET cumplido = true, id_revisor_externo = 'rev-msosa', fecha_verificacion = '2026-08-28 12:00:00'
FROM tramitacion.expedientes e
WHERE e.id_expediente = ce.id_expediente AND e.numero_expediente = 'EXP-VL-2026-000001';

COMMIT;