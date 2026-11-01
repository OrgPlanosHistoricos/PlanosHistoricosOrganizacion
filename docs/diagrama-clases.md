# Diagrama de clases del backend

Basado en `backend/src/models.py`, `backend/src/planos/schemas.py`,
`backend/src/tareas/schemas.py`, `backend/src/tareas/services.py` y
`backend/src/planos/worker.py`.

## Catálogo de planos

Se muestran las clases de dominio y sus atributos principales. `?` indica
un atributo opcional. Las clases SQLModel/Pydantic externas se omiten.
Los atributos heredados no se repiten en las subclases.

```mermaid
classDiagram
    direction TB
    class DatosPlano {
        +str? texto_extraido
        +str? arquitecto
        +int? anio
        +str? titulo
        +str? ubicacion
        +str? escala
        +str? tipo_de_plano
        +str? material_soporte
        +str? notas
    }
    class PlanoBase {
        +str nombre_original
        +str content_type
        +str? hash_sha256
        +int? tamano_bytes
        +str ubicacion_fisica
        +str expediente
        +str direccion_referencia
        +str parcela
        +str circunscripcion
        +str seccion
        +str manzana
        +str parcela_catastral
        +str? nomenclatura
        +EstadoPlano estado
        +EstadoIA ia_estado
        +str? ia_error
        +str? ia_propuesta
        +str? creado_por
        +str? validado_por
        +datetime? validado_en
        +bool activo
    }
    class Plano {
        +int? id
        +str minio_path
        +datetime creado_en
        +datetime actualizado_en
    }
    class EventoAuditoria {
        +int? id
        +int plano_id
        +str usuario_id
        +datetime fecha
        +str accion
        +str motivo
        +str? valores_anteriores
        +str? valores_nuevos
        +str? ip_origen
    }
    class ProcesamientoIA {
        +int? id
        +int plano_id
        +int intento
        +EstadoIA estado
        +str? error
        +str modelo_ia
        +str? version_prompt
        +str? parametros_preprocesamiento
        +str? texto_extraido_raw
        +str? respuesta_json_raw
        +int? duracion_ms
        +datetime fecha
    }
    class EstadoPlano {
        <<enumeration>>
        pendiente
        validado
        sin_ubicacion
    }
    class EstadoIA {
        <<enumeration>>
        procesando
        completado
        error
        no_aplica
    }
    DatosPlano <|-- PlanoBase
    PlanoBase <|-- Plano
    Plano "1" -- "0..*" EventoAuditoria : eventos
    Plano "1" -- "0..*" ProcesamientoIA : procesamientos
    PlanoBase ..> EstadoPlano : estado
    PlanoBase ..> EstadoIA : ia_estado
    ProcesamientoIA ..> EstadoIA : estado
```

Cada evento y procesamiento pertenece a un plano por su clave foránea
obligatoria `plano_id`. Un plano puede tener cero o muchos de cada uno.
`Plano`, `EventoAuditoria` y `ProcesamientoIA` son tablas persistidas;
`DatosPlano` y `PlanoBase` aportan atributos por herencia.
Los identificadores opcionales se asignan al persistir.

## Esquemas de entrada y salida del catálogo

```mermaid
classDiagram
    DatosPlano <|-- PlanoBase
    PlanoBase <|-- PlanoRead
    PlanoRead <|-- PlanoDetalle
    DatosPlano <|-- PlanoValidar
    DatosPlano <|-- PlanoModificar
    NomenclaturaEntrada <|-- PlanoValidar
    NomenclaturaEntrada <|-- PlanoModificar
    class PlanoRead {
        +int id
        +datetime creado_en
        +datetime actualizado_en
    }
    class NomenclaturaEntrada {
        +str circunscripcion
        +str seccion
        +str manzana
        +str parcela_catastral
    }
    class PlanoValidar {
        +str parcela
        +str usuario_id
    }
    class PlanoModificar {
        +str parcela
        +str motivo
        +str usuario_id
    }
    PlanoDetalle "1" --> "0..*" EventoRead : eventos
    PlanoDetalle "1" --> "0..*" ProcesamientoRead : procesamientos
```

`EventoRead` y `ProcesamientoRead` representan la salida de la API;
son clases distintas de las entidades persistidas.

## Extracción y tareas asíncronas

```mermaid
classDiagram
    class PlanoHistorico {
        +str? texto_extraido
        +str? arquitecto
        +int? anio
        +str? titulo
        +str? ubicacion
        +str? escala
        +str? tipo_de_plano
        +str? material_soporte
        +str? notas
    }
    class ArchivoInfo {
        +str nombre_original
        +str supabase_url
    }
    class DocumentoExtraccion {
        +datetime fecha_procesamiento
    }
    class TareaInfo {
        +str task_id
        +TaskStatus status
        +str? filename
        +str created_at
        +str updated_at
        +dict? resultado
        +str? error
        +str? supabase_url
        +to_dict() dict
    }
    class TaskStatus {
        <<enumeration>>
        PENDING
        PROCESSING
        COMPLETED
        ERROR
    }
    class TaskManager {
        +dict tasks
        +Queue queue
        +start_worker()
        +stop_worker()
        +crear_tarea(filename, content_type, image_bytes) TareaInfo
        +obtener_tarea(task_id) TareaInfo
        +listar_tareas() list
    }
    class PlanosWorker {
        +Queue queue
        +start()
        +stop()
        +encolar(plano_id, image_bytes)
    }
    DocumentoExtraccion "1" --> "1" ArchivoInfo : archivo
    DocumentoExtraccion "1" --> "1" PlanoHistorico : extraccion_qwen
    TaskManager "1" --> "0..*" TareaInfo : tasks
    TareaInfo ..> TaskStatus : status
    TaskManager ..> PlanoHistorico : extrae y serializa
    PlanosWorker ..> Plano : procesa por id
    PlanosWorker ..> ProcesamientoIA : registra mediante funciones auxiliares
```

`PlanoHistorico` y `DatosPlano` tienen campos similares, pero no existe
herencia entre ellos. `TareaInfo.resultado` almacena un diccionario,
no una referencia a `PlanoHistorico`. Los controladores y servicios de
planos son funciones de módulo, por eso no se inventan clases para ellos.

Este documento se centra en dominio, esquemas del catálogo y procesamiento;
omite configuración, excepciones y el esquema auxiliar de detección del cajetín.
