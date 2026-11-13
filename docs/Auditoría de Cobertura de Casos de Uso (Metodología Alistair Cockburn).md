# Documento de Auditoría de Cobertura: Casos de Uso y Brechas del Sistema

**Proyecto:** Sistema de Digitalización y Gestión del Patrimonio Cartográfico e Histórico  
**Referencia Metodológica:** Alistair Cockburn (*Writing Effective Use Cases*)  
**Documento auditado:** [`Especificación Formal de Casos de Uso (Metodología Alistair Cockburn).md`](Especificaci%C3%B3n%20Formal%20de%20Casos%20de%20Uso%20(Metodolog%C3%ADa%20Alistair%20Cockburn).md)  
**Fecha de auditoría:** 2026-11-13

---

## Introducción y Criterio Metodológico

Esta auditoría contrasta todas las acciones verificables en el sistema real —interfaz web (`front/`), proxy ([`front/nginx.conf`](../front/nginx.conf)), los 12 endpoints activos de FastAPI (`backend/src/`), el worker de visión artificial ([`worker.py`](../backend/src/planos/worker.py)), los clientes de almacenamiento/visión ([`storage_client.py`](../backend/src/compartido/storage_client.py), [`vision_client.py`](../backend/src/compartido/vision_client.py)), la inicialización de base de datos ([`models.py`](../backend/src/models.py)) y la vinculación con el esquema externo `tramitacion`— frente a la especificación formal vigente.

Siguiendo estrictamente a **Alistair Cockburn (*Writing Effective Use Cases*)**, no toda acción de interfaz es un caso de uso independiente:

* Cambiar de pestaña ([`app.js`](../front/app.js#L12-L41)), cancelar una edición en curso o paginar resultados son **pasos de interacción o subflujos** dentro de su caso de uso contenedor.
* En cambio, toda capacidad con **objetivo discreto de usuario (Nivel Mar 🌊)**, **objetivo estratégico (Nivel Nube ☁️)** o **proceso técnico reutilizable / autónomo con reglas e invariantes propias (Nivel Subfunción 🐟)** sí requiere un Caso de Uso formal en formato *Fully Dressed*.

El análisis detecta **7 casos de uso faltantes (`DH-CU-00` y `DH-CU-07` a `DH-CU-12`)**, además de **brechas funcionales, discrepancias de implementación y defectos de trazabilidad** dentro de los 6 casos existentes (`DH-CU-01` a `DH-CU-06`).

---

## 1. Casos de Uso Faltantes (Formato *Fully Dressed* — Alistair Cockburn)

### DH-CU-00: Preservar, catalogar y consultar el acervo cartográfico histórico en la Plataforma GIUOS

* **Alcance:** Plataforma GIUOS (*Plataforma de Gobernanza Inteligente de Urbanismo, Obras y Servicios*) — Módulo de Planos Históricos  
* **Nivel:** Resumen / Estratégico (Nivel Nube / Cometa ☁️)  
* **Actor Principal:** Dirección de Catastro y Archivo Histórico (mediante Operadores, Validadores y Usuarios)  
* **Interesados e Intereses:**  
  * *Dirección de Catastro y Archivo Histórico:* Garantizar el ciclo integral desde el ingreso digital del plano hasta su publicación indexada e interoperable con el sistema de expedientes de obra.  
  * *Módulo externo de Tramitación (`tramitacion`):* Poder vincular expedientes e inmuebles con planos históricos mediante la clave catastral normalizada y `id_inmueble`.  
  * *Ciudadanos, investigadores y profesionales:* Acceder de forma unificada a los módulos de gobernanza urbana desde un portal común.  
* **Precondición:** La plataforma web se encuentra desplegada y el esquema `tramitacion` está disponible en PostgreSQL junto con el esquema `planos` y el repositorio de objetos en Supabase Storage.  
* **Garantías Mínimas:** Las operaciones de preservación, validación, modificación o baja mantienen consistencia transaccional y trazabilidad auditada; los módulos no habilitados no exponen flujos rotos como operativos.  
* **Garantías de Éxito:** El plano digitalizado recorre el ciclo completo de carga (`DH-CU-01`), extracción asistida (`DH-CU-02`), validación (`DH-CU-03`), eventual rectificación o reanálisis (`DH-CU-04`, `DH-CU-08`), consulta pública (`DH-CU-05`) o baja lógica controlada (`DH-CU-07`).  
* **Disparador:** El actor accede al portal principal **GIUOS** ([`front/index.html`](../front/index.html#L13-L41)).

#### Escenario Principal de Éxito

1. El actor accede a la portada de la Plataforma **GIUOS** ([`front/index.html`](../front/index.html#L15-L39)).  
2. El sistema presenta los módulos de la plataforma: **"Planos Históricos"** (activo) y **"Tramitar Nueva Obra"** (en estado `"Próximamente"`).  
3. El actor selecciona **"Planos Históricos"** (`planos-historicos.html`).  
4. El sistema inicializa las pestañas operativas, dispara la verificación continua de base de datos (**`DH-CU-11`**) y habilita el ciclo de vida del acervo:  
   1. Ingesta digital de planos y datos preliminares (**`DH-CU-01`**).  
   2. Extracción asíncrona de metadatos del cajetín mediante visión artificial (**`DH-CU-02`**).  
   3. Control de calidad, catalogación definitiva y eventual gestión de reintentos (**`DH-CU-03`**, **`DH-CU-06`**).  
   4. Mantenimiento catalográfico, resolución de propuestas de reanálisis IA y auditoría de cambios (**`DH-CU-04`**, **`DH-CU-08`**, **`DH-CU-09`**).  
   5. Consulta del catálogo público, previsualización y descarga de originales (**`DH-CU-05`**, **`DH-CU-10`**).  
   6. Baja lógica de planos descartados o erróneos (**`DH-CU-07`**).  

#### Extensiones

* **3a. El actor selecciona la tarjeta "Tramitar Nueva Obra":**  
  * 3a1. El sistema muestra la etiqueta visual `"Próximamente"` y mantiene un enlace inactivo (`href="#"`), sin derivar a otro entorno hasta que el módulo externo se integre.  

#### Frecuencia

* Flujo marco continuo que engloba la operación diaria del Archivo Histórico y Dirección de Catastro.

---

### DH-CU-07: Dar de baja lógica un plano histórico

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos  
* **Nivel:** Objetivo de Usuario (Nivel Mar 🌊)  
* **Actor Principal:** Operador Documental / Validador Documental  
* **Interesados e Intereses:**  
  * *Operador / Validador:* Retirar del circuito activo planos subidos por error, duplicados físicos, documentos ilegibles o registros que ya no deben figurar en pendientes ni en el catálogo público.  
  * *Área de Auditoría y Legales:* Asegurar que ningún plano eliminado desaparezca sin rastro, conservando el registro histórico, el autor de la baja, la IP y el archivo binario de respaldo.  
  * *Dirección de Catastro:* Liberar inmediatamente la nomenclatura catastral asociada al plano dado de baja para permitir cargar el plano correcto sobre esa parcela sin colisiones.  
* **Precondición:** Existe un plano en base de datos con `activo = true` (puede hallarse en estado `pendiente`, `validado` o `sin_ubicacion`, y con cualquier `ia_estado`).  
* **Garantías Mínimas:** Si el actor cancela la confirmación en interfaz o falla la transacción en base de datos, el plano permanece `activo = true`, conserva su `nomenclatura` y no se escribe evento de baja.  
* **Garantías de Éxito:** El plano queda marcado con `activo = false`, su columna `nomenclatura` pasa a `NULL` (liberando la restricción única `ux_planos_nomenclatura`), se registra un evento inmutable `accion = 'Caducidad'` en `planos.eventos_auditoria`, el registro desaparece de todas las bandejas y consultas activas, y el binario original + `procesamientos_ia` se preservan intactos para trazabilidad.  
* **Disparador:** El actor presiona **"Eliminar"** en la cola de recientes de Carga ([`cu-cargar.js`](../front/js/cu-cargar.js#L137)), o **"Eliminar plano"** en Validar ([`cu-validar.js`](../front/js/cu-validar.js#L171-L205)) o en Modificar ([`cu-modificar.js`](../front/js/cu-modificar.js#L237)).

#### Escenario Principal de Éxito

1. El actor localiza el plano que desea retirar en cualquiera de las tres vistas habilitadas:  
   * Lista de cola de análisis / recientes en **Cargar plano**.  
   * Panel de opciones ante falla de IA o barra de acciones de ficha en **Validar y catalogar**.  
   * Barra de acciones de ficha de plano catalogado en **Modificar catalogación**.  
2. El actor presiona el botón de baja (`"Eliminar"` o `"Eliminar plano"`).  
3. El frontend despliega un cuadro de confirmación modal del navegador: *"¿Eliminar este plano, su archivo y su historial permanentemente?"*.  
4. El actor confirma explícitamente la operación; el frontend deshabilita el botón durante la petición y envía `DELETE /planos/{plano_id}` (ver [`planos/routes.py`](../backend/src/planos/routes.py#L70-L82)).  
5. El backend adquiere un bloqueo pesimista de fila (`SELECT ... WHERE id = plano_id AND activo = true FOR UPDATE` en [`planos/services.py`](../backend/src/planos/services.py#L294-L296)).  
6. El backend toma un snapshot completo del estado previo (`valores_anteriores` con `activo: true`), asigna `activo = false`, `nomenclatura = None`, `actualizado_en = ahora()` y genera el snapshot posterior (`valores_nuevos` con `activo: false`).  
7. El backend inserta un registro en `planos.eventos_auditoria` con `accion = "Caducidad"`, `motivo = "Baja lógica de plano"`, `usuario_id` e `ip_origen` extraída de cabeceras de proxy o socket.  
8. El backend confirma la transacción (`commit`) y retorna HTTP 200 OK (`{"eliminado": true, "id": plano_id}`).  
9. El frontend limpia la selección activa (si correspondía a Validar o Modificar), muestra `"El plano se eliminó correctamente."` y refresca todas las listas de la aplicación (`actualizarListas()`).  

#### Extensiones

* **4a. El actor cancela el diálogo de confirmación:**  
  * 4a1. El frontend aborta la operación sin emitir ninguna petición HTTP; el plano permanece intacto.  
* **5a. El plano ya fue dado de baja previamente o no existe (`activo = false` o inexistente):**  
  * 5a1. El backend retorna HTTP 404 Not Found (`"Plano no encontrado"`).  
  * 5a2. El frontend mapea el error al mensaje seguro de `faltante`: *"El plano solicitado ya no está disponible. Actualizá la lista y elegí otro plano."*  
* **5b. El plano estaba siendo analizado por el Worker (`ia_estado = 'procesando'`) al momento de la baja:**  
  * 5b1. La baja lógica marca `activo = false` y oculta inmediatamente el registro de la interfaz; si el worker finaliza con posterioridad, persiste resultado técnico sobre la fila inactiva sin volver a publicarla. *(Nota técnica observada: actualmente el backend no libera de forma explícita la cola en memoria, pero el plano nunca es devuelto por `GET /planos` al tener `activo = false`).*  

#### Requisitos Especiales

* El mensaje mostrado en UI (`"¿Eliminar este plano, su archivo y su historial permanentemente?"`) comunica eliminación permanente desde la perspectiva operativa, aunque a nivel de datos el sistema implementa **baja lógica auditable** preservando el objeto en Supabase Storage y las tablas de auditoría e IA.
* La interfaz no envía `usuario_id` por querystring en `API.eliminar(id)`, por lo que el backend registra el valor por defecto `"Operador"`.

#### Frecuencia

* Eventual (varias veces por semana ante errores de carga o duplicados detectados).

---

### DH-CU-08: Revisar y resolver propuesta de reanálisis de IA sobre plano catalogado

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos  
* **Nivel:** Objetivo de Usuario (Nivel Mar 🌊)  
* **Actor Principal:** Validador Documental / Operador  
* **Interesados e Intereses:**  
  * *Validador / Operador:* Aprovechar mejoras de modelos de visión artificial o reintentos sobre planos ya validados sin perder jamás el trabajo humano consolidado por una sobrescritura silenciosa.  
  * *Área de Auditoría y Legales:* Garantizar que todo cambio originado por un reanálisis quede igualmente sujeto a confirmación humana explícita y justificada en `eventos_auditoria` (`DH-CU-04`), siendo esta vía además el único mecanismo autorizado para actualizar `texto_extraido`.  
* **Precondición:** Existe un plano catalogado (`estado IN ('validado', 'sin_ubicacion')`) con `ia_propuesta` poblado tras completar un reanálisis asíncrono de IA ([`worker.py`](../backend/src/planos/worker.py#L82-L83)), o bien el usuario acaba de disparar el reanálisis desde la vista de Modificación.  
* **Garantías Mínimas:** Mientras el usuario no aplique la propuesta y confirme mediante `DH-CU-04`, ni los metadatos catalogados ni el catálogo público (`DH-CU-05`) sufren alteración alguna; si el usuario descarta la propuesta, los valores confirmados permanecen intactos.  
* **Garantías de Éxito:** La propuesta pendiente (`ia_propuesta`) queda resuelta (`ia_propuesta = NULL`), ya sea mediante aplicación selectiva de campos confirmada y auditada (`DH-CU-04`), o mediante descarte explícito sin mutar los metadatos vigentes.  
* **Disparador:** El usuario visualiza el banner *"Hay una nueva propuesta de la IA disponible para este plano."* y presiona **"Ver Antes y Después"** o **"Descartar propuesta"** ([`cu-modificar.js`](../front/js/cu-modificar.js#L223-L231)), o bien finaliza el polling de reanálisis IA iniciado desde Modificar ([`cu-modificar.js`](../front/js/cu-modificar.js#L453-L456)).

#### Escenario Principal de Éxito (Comparación y Aplicación Selectiva)

1. El usuario selecciona un plano catalogado en **Modificar catalogación** que posee `ia_propuesta` no nulo (o concluye con éxito un reanálisis disparado desde esa ficha).  
2. El sistema muestra el banner informativo de propuesta pendiente (y en caso de reanálisis recién concluido por polling cada `1.5s`, abre el modal automáticamente).  
3. El actor pulsa **"Ver Antes y Después"**.  
4. El sistema despliega el modal `"Comparación: Antes y Después del análisis IA"` ([`cu-modificar.js`](../front/js/cu-modificar.js#L273-L321)) mostrando los 9 atributos documentales (`texto_extraido`, `titulo`, `arquitecto`, `ubicacion`, `anio`, `escala`, `tipo_de_plano`, `material_soporte`, `notas`) en columnas: *Campo*, *Valor anterior (guardado)*, *Nuevo valor sugerido por la IA*, *Estado* (`Modificado` / `Sin cambios`) y *Aplicar* (checkbox premarcado para todo campo modificado).  
5. El actor revisa las diferencias y marca o desmarca los checkboxes campo por campo según criterio técnico (pudiendo incluir `texto_extraido`, que en el formulario normal es de solo lectura).  
6. El actor pulsa **"Aplicar cambios"**.  
7. El sistema traslada únicamente los valores marcados al formulario de edición (normalizando la `escala`), conserva el valor anterior en los desmarcados, completa automáticamente el campo obligatorio *"Motivo de la modificación"* con `"Actualización por análisis de IA"` si estaba vacío (actualizando el contador `N / 180 caracteres`), cierra el modal y muestra aviso para revisar y confirmar.  
8. El actor revisa el formulario, ajusta manualmente si lo considera necesario y confirma definitivamente guardando mediante **`DH-CU-04`** (`PUT /planos/{id}/modificar`).  
9. El backend, al detectar coincidencia entre `texto_extraido` recibido y `propuesta["texto_extraido"]`, autoriza excepcionalmente actualizar `texto_extraido` ([`planos/services.py`](../backend/src/planos/services.py#L393-L401)), limpia `ia_propuesta = None` y registra el evento `Modificación` en auditoría.  

#### Extensiones

* **3a. El actor decide rechazar directamente la propuesta sugerida desde el banner:**  
  * 3a1. El actor presiona **"Descartar propuesta"**.  
  * 3a2. El frontend envía `POST /planos/{id}/descartar_propuesta` ([`planos/routes.py`](../backend/src/planos/routes.py#L125-L127)).  
  * 3a3. El backend asigna `ia_propuesta = None` y persiste sin modificar ningún dato catalogado ni generar evento de modificación.  
  * 3a4. El frontend refresca la ficha, oculta el banner y notifica: *"Se descartó la propuesta de la IA y se conservaron los valores actuales."*  
* **5a. El actor decide cerrar el modal sin volcar cambios al formulario:**  
  * 5a1. El actor pulsa **"Cancelar"** o el botón de cierre (`×`).  
  * 5a2. El frontend cierra el modal manteniendo `ia_propuesta` vigente en el plano para posterior revisión.  
* **6a. Todos los checkboxes fueron desmarcados antes de pulsar "Aplicar cambios":**  
  * 6a1. El sistema restaura los valores actuales en el formulario sin sobrescribir ni precargar motivo, notificando que no se seleccionaron cambios de la IA.  
* **1a. El polling de 60 segundos (`40` ciclos de `1.5s`) expira mientras la IA continúa procesando:**  
  * 1a1. El frontend detiene el polling local y recarga el detalle mostrando el estado `Analizando con IA...`; cuando el worker concluya posteriormente, la propuesta quedará disponible en `ia_propuesta` para cuando se reabra la ficha.  

#### Requisitos Especiales

* **Protección de transcripción OCR/VLM:** Para evitar alteraciones arbitrarias de la transcripción original desde el cliente, el backend solo acepta modificar `texto_extraido` dentro de `PUT /planos/{id}/modificar` si existe un `ia_propuesta` activo y el texto enviado coincide exactamente con `propuesta["texto_extraido"]`.

#### Frecuencia

* Ocasional (cuando se reanalizan planos catalogados por mejora del modelo o reintento técnico).

---

### DH-CU-09: Consultar historial de auditoría y trazabilidad de cambios de un plano

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos  
* **Nivel:** Objetivo de Usuario / Subfunción con valor de Auditoría (Nivel Mar secundario / Pez 🌊/🐟)  
* **Actor Principal:** Validador Documental / Operador / Área de Auditoría  
* **Interesados e Intereses:**  
  * *Área de Auditoría y Legales:* Inspeccionar la secuencia completa de eventos del ciclo de vida (`Carga`, `Validación`, `Modificación`, `Observación`, `Caducidad`) con fecha, hora, responsable y detalle campo por campo de cada mutación.  
  * *Validador / Operador:* Verificar qué se cambió anteriormente antes de introducir nuevas correcciones en la catalogación.  
* **Precondición:** El plano seleccionado existe (`activo = true`) y posee registros asociados en `planos.eventos_auditoria` (al menos el evento inicial `Carga` generado en `DH-CU-01`).  
* **Garantías Mínimas:** Operación de estricta lectura; no altera estados, metadatos ni registros de auditoría.  
* **Garantías de Éxito:** El usuario visualiza el listado cronológico inverso de eventos, navega por páginas y puede inspeccionar las diferencias exactas (*Valor anterior* vs. *Valor nuevo*) de los campos que cambiaron en cada evento.  
* **Disparador:** El usuario selecciona un plano en **Modificar catalogación** ([`cu-modificar.js`](../front/js/cu-modificar.js#L139-L172)) o abre un plano en **Consultar** ([`cu-consultar.js`](../front/js/cu-consultar.js#L150-L156)).

#### Escenario Principal de Éxito (Vista Detallada en Modificar)

1. Al abrir el detalle de un plano catalogado (`GET /planos/{id}` retorna `PlanoDetalle` con su lista `eventos`), el sistema ordena los eventos de forma descendente por `fecha` (y `id` como desempate).  
2. El sistema renderiza la sección **"Historial de cambios"** en bloques de hasta **10 eventos por página** con columnas: *Fecha*, *Hora* (formato `es-AR` 24h), *Usuario*, *Motivo* (truncado a 180 caracteres en resumen) y acción **"Ver detalle"**.  
3. El actor selecciona **"Ver detalle"** en una fila de evento.  
4. El sistema parsea los JSON `valores_anteriores` y `valores_nuevos`, compara clave por clave (normalizando valores de `escala` para evitar falsos positivos entre vacíos/nulos) y despliega únicamente los campos que presentaron variación real mostrando *Valor anterior* y *Valor nuevo* (el botón cambia a **"Ocultar detalle"**).  
5. Si el historial supera 10 eventos, el actor utiliza los controles **"Anterior"** y **"Siguiente"** para recorrer el resto de las páginas.  

#### Extensiones

* **4a. El evento es de tipo observación o reintento (`accion = "Observación"`, p. ej. `"Reintento de análisis IA"`) sin snapshots de campos:**  
  * 4a1. El sistema despliega: *"No hay cambios de campos registrados para este evento."*  
* **1a. Inspección desde la pestaña pública "Consultar":**  
  * 1a1. La vista de consulta está diseñada para mostrar una lista cronológica inversa simplificada (`fecha — motivo`).  
  * *(Brecha técnica detectada en el código actual)*: [`cu-consultar.js`](../front/js/cu-consultar.js#L150) intenta leer `d.historial`, propiedad inexistente en `PlanoDetalle` de [`planos/schemas.py`](../backend/src/planos/schemas.py#L181-L183) (que serializa `eventos`), por lo que en **Consultar** el historial nunca llega a renderizarse en la UI actual.  

#### Requisitos Especiales

* El esquema `EventoRead` también incluye `accion` e `ip_origen`, aunque la tabla actual en UI muestra `Fecha`, `Hora`, `Usuario`, `Motivo` y `Detalle`.

#### Frecuencia

* Frecuente durante revisiones de catalogación y auditorías de cambios.

---

### DH-CU-10: Obtener previsualización optimizada y descargar archivo binario original del plano

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos (Backend API + Supabase Storage + Rasterizador PDF)  
* **Nivel:** Subfunción (Nivel Pez 🐟)  
* **Actor Principal:** Usuario del Sistema / Validador / Operador  
* **Interesados e Intereses:**  
  * *Usuario / Validador:* Visualizar rápidamente documentos PDF o imágenes pesadas dentro de la ficha sin esperar descargas completas, y acceder al archivo fuente original en máxima fidelidad cuando necesite hacer zoom externo o archivarlo.  
  * *Equipo de TI:* Evitar rasterizar repetidamente páginas de PDF mediante cacheo persistente en Supabase Storage y cabeceras HTTP de caché.  
* **Precondición:** El plano existe en base de datos con `activo = true` y su objeto binario (`minio_path`) está almacenado en el bucket de Supabase Storage.  
* **Garantías Mínimas:** Si el plano no existe o fue dado de baja, no se entrega ningún recurso; si el binario falla en Storage se notifica error HTTP sin exponer rutas ni claves de Supabase.  
* **Garantías de Éxito:** Se entrega el JPEG de previsualización (generándolo y cacheándolo en Storage si es un PDF sin preview previo) o el binario original con su `Content-Type` y nombre original UTF-8.  
* **Disparador:** Renderizado de ficha de detalle en `DH-CU-03`, `DH-CU-04` o `DH-CU-05` (`GET /planos/{id}/preview`), o clic del actor en el enlace *"Ver / Descargar imagen original"* / *"Abrir / Descargar PDF original"* (`GET /planos/{id}/archivo`).

#### Escenario Principal de Éxito (Subflujo Previsualización `/preview`)

1. Al cargar el detalle de un plano, el navegador solicita `GET /api/planos/{id}/preview` mediante el elemento `<img class="thumb">`.  
2. El backend verifica que el plano exista y esté activo (`_obtener_plano`).  
3. Si el `content_type` pertenece a `FORMATOS_IMAGEN` (`image/jpeg`, `image/png`, `image/webp`, `image/tiff`), descarga los bytes desde Supabase Storage y los retorna directamente con su `media_type` y cabecera `Cache-Control: public, max-age=86400`.  
4. Si el archivo es PDF (`application/pdf`):  
   1. Calcula la clave derivada `{minio_path}.preview.jpg` (`obtener_preview_key`).  
   2. Verifica existencia en el bucket (`existe_archivo(preview_key)` en [`planos/services.py`](../backend/src/planos/services.py#L335-L343)).  
   3. Si existe en caché de Storage, la descarga y responde como `image/jpeg`.  

#### Extensiones

* **4.3a. El archivo es PDF pero no existe `{minio_path}.preview.jpg` en Storage (p. ej. registros antiguos o subida parcial):**  
  * 4.3a1. El backend descarga el PDF original desde Supabase Storage.  
  * 4.3a2. Rasteriza de forma perezosa (*lazy*) la página `0` en alta resolución a JPEG (`pdf_page_to_jpeg_bytes` usando `pypdfium2` con escala adaptativa `1.5x..4.0x`).  
  * 4.3a3. Sube y persiste `{minio_path}.preview.jpg` en Supabase Storage (`subir_archivo_con_key`) para futuras solicitudes y retorna el JPEG con `Cache-Control: public, max-age=86400`.  
* **1a. El actor solicita el archivo binario original (`GET /api/planos/{id}/archivo`):**  
  * 1a1. El actor hace clic en el enlace de archivo original en Validar, Modificar o Consultar (en Consultar lleva además atributo HTML `download`).  
  * 1a2. El backend verifica plano activo, descarga los bytes íntegros desde `minio_path` en Supabase Storage y los retorna con su `content_type` original y cabecera `Content-Disposition: inline; filename*=UTF-8''{nombre_original}` ([`planos/controllers.py`](../backend/src/planos/controllers.py#L67-L75)).  
* **2a. El plano fue dado de baja o no existe:**  
  * 2a1. El backend responde HTTP 404 Not Found.  

#### Frecuencia

* En cada apertura de ficha en Validar, Modificar y Consultar.

---

### DH-CU-11: Monitorear disponibilidad de base de datos, estado del servicio y sincronización de bandejas

* **Alcance:** Interfaz Web SPA + Gateway Nginx + API FastAPI  
* **Nivel:** Subfunción (Nivel Pez 🐟)  
* **Actor Principal:** Sistema (Temporizadores de Frontend / Operador / Monitoreo Técnico)  
* **Interesados e Intereses:**  
  * *Operador / Validador:* Saber en todo momento si la base de datos PostgreSQL se encuentra operativa antes de intentar digitalizar o validar, y ver reflejado automáticamente cuándo finaliza el procesamiento de IA en segundo plano sin recargar la página.  
  * *Equipo de Operaciones / TI:* Contar con endpoints livianos de *healthcheck* para verificar latido del servicio API, tamaño de cola IA y conectividad SQL sin exponer credenciales ni detalles internos de excepción.  
* **Precondición:** La aplicación web está abierta en el navegador o un cliente técnico consulta los endpoints de salud del backend.  
* **Garantías Mínimas:** Ninguna falla de red o caída de base de datos cuelga la interfaz ni filtra cadenas de conexión o errores de SQL; las comprobaciones periódicas evitan peticiones superpuestas (`running` lock).  
* **Garantías de Éxito:** El indicador de barra lateral `#database-status` refleja exactamente el estado de conectividad actual, y las bandejas operativas muestran los cambios recientes de estado de los planos.  
* **Disparador:** Carga inicial de `planos-historicos.html` (`DOMContentLoaded`), disparo periódico del intervalo de base de datos (cada `15s`), evento de red del navegador `'online'`, intervalo periódico de refresco de listas (cada `5s`) o petición HTTP a `/health` / `/health/database`.

#### Escenario Principal de Éxito

1. **Verificación de conectividad SQL ([`database-status.js`](../front/js/database-status.js)):**  
   1. Al iniciar la vista, cada `15000 ms` y al recuperarse la conectividad (`online`), el módulo dispara `GET /api/health/database` con `cache: 'no-store'` y un `AbortController` de `8000 ms`.  
   2. El backend ejecuta `SELECT 1` contra PostgreSQL ([`src/services.py`](../backend/src/services.py#L16-L22)).  
   3. Si la consulta responde exitosamente, el backend retorna HTTP 200 OK `{"database": "connected"}` con `Cache-Control: no-store`.  
   4. El frontend actualiza el indicador visual a `data-state="connected"` con el texto `"Base de datos conectada"`.  
2. **Sincronización periódica de bandejas ([`app.js`](../front/app.js#L43-L60)):**  
   1. Cada `5000 ms`, el orquestador invoca `actualizarListas()`, refrescando la cola de Carga (`renderRecientes`), la bandeja de pendientes de Validar (`renderLista`) y la lista de catalogados de Modificar (`renderLista`).  

#### Extensiones

* **1.2a. Falla la consulta `SELECT 1` en PostgreSQL (`SQLAlchemyError`):**  
  * 1.2a1. El backend captura la excepción internamente y retorna HTTP 503 Service Unavailable `{"database": "disconnected"}` (`Cache-Control: no-store`).  
  * 1.2a2. El frontend cambia el indicador a `data-state="disconnected"` con texto `"Base de datos sin conexión"`.  
* **1.1a. Error de red, error del proxy (502/504) o expiración del timeout de 8 segundos:**  
  * 1.1a1. El frontend aborta/captura el error y renderiza estado `data-state="unknown"` con texto `"No se pudo verificar la base de datos"`.  
* **1a. Petición de salud operativa de la API (`GET /health`):**  
  * 1a1. Un servicio de monitoreo o prueba automatizada invoca `GET /health` ([`src/routes.py`](../backend/src/routes.py#L9-L11)).  
  * 1a2. El backend retorna HTTP 200 OK con `{"status": "ok", "tareas_en_cola": <qsize>}` reportando la cantidad de planos pendientes en la `asyncio.Queue` del worker.  

#### Requisitos Especiales

* El refresco periódico de `app.js` cada 5 segundos actualiza Cargar, Validar y Modificar, mientras que la lista de **Consultar** (`CUConsultar.renderLista()`) solo se recarga al iniciar la app o al hacer clic explícito en la pestaña `"Consultar"`.

#### Frecuencia

* Continua mientras la aplicación permanezca abierta (cada 5s y 15s por sesión activa).

---

### DH-CU-12: Inicializar sistema, verificar esquema externo y recuperar análisis interrumpidos

* **Alcance:** API FastAPI y Worker Asíncrono (Ciclo de vida `lifespan`)  
* **Nivel:** Subfunción (Nivel Pez 🐟)  
* **Actor Principal:** Sistema (Arranque del servidor FastAPI / `lifespan`)  
* **Interesados e Intereses:**  
  * *Equipo de Operaciones / TI:* Garantizar que el servicio no levante en un estado inconsistente sin la base territorial externa requerida, y que las migraciones del esquema `planos` se apliquen de forma idempotente.  
  * *Operador / Validador Documental:* Evitar que un reinicio de contenedor o corte eléctrico deje planos perpetuamente atascados en estado `"Analizando…"` (`ia_estado = 'procesando'`) al perderse la cola en memoria RAM.  
* **Precondición:** Se inicia el proceso ASGI (`uvicorn src.main:app`) con acceso configurado a PostgreSQL (`DATABASE_URL`) y al almacenamiento Supabase.  
* **Garantías Mínimas:** Si el esquema externo obligatorio `tramitacion.inmuebles` no existe en la base de datos, el servidor aborta el arranque de inmediato impidiendo operaciones corruptas.  
* **Garantías de Éxito:** El esquema `planos` y sus tablas/índices están actualizados, el worker asíncrono está activo y todo plano activo que había quedado en `ia_estado = 'procesando'` vuelve a ingresar a la cola para ser procesado.  
* **Disparador:** Evento de inicio `lifespan` en [`main.py`](../backend/src/main.py#L14-L19).

#### Escenario Principal de Éxito

1. Al arrancar la API, el manejador `lifespan` invoca `init_db()` ([`models.py`](../backend/src/models.py#L583-L633)).  
2. El sistema verifica en PostgreSQL que exista la tabla externa `tramitacion.inmuebles` (`SELECT to_regclass('tramitacion.inmuebles')`).  
3. El sistema ejecuta `CREATE SCHEMA IF NOT EXISTS planos`, migra tablas heredadas desde `public` si existían, crea las tablas faltantes (`planos`, `eventos_auditoria`, `procesamientos_ia`) y aplica sentencias `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` e índices (`ux_planos_nomenclatura`, `ix_planos_planos_id_inmueble`, clave foránea a `tramitacion.inmuebles`).  
4. El manejador `lifespan` inicia la tarea asíncrona de fondo `planos_worker.start()`.  
5. Antes de procesar nuevas tareas, el loop del worker ejecuta `_planos_sin_terminar()` ([`worker.py`](../backend/src/planos/worker.py#L125-L145)), consultando todos los planos con `activo = true` e `ia_estado = 'procesando'`.  
6. Por cada plano inconcluso, recupera los bytes desde Supabase Storage (si es imagen, el binario original; si es PDF, descarga `{key}.preview.jpg` o rasteriza nuevamente la página 0) y lo reencola en `asyncio.Queue` para ejecutar `DH-CU-02`.  
7. Al apagarse el servidor, `lifespan` invoca `await planos_worker.stop()`, cancelando ordenadamente la tarea del worker.  

#### Extensiones

* **2a. No existe `tramitacion.inmuebles` en PostgreSQL:**  
  * 2a1. `init_db()` lanza `RuntimeError("Falta el esquema 'tramitacion': hay que cargar db/tramitacion en Postgres antes de iniciar la API.")` e impide que la API quede escuchando peticiones.  
* **6a. Falla la recuperación desde Storage para alguno de los planos inconclusos:**  
  * 6a1. El worker captura la excepción individual, registra el error en logs (`logger.error`) y continúa recuperando e iniciando la cola para el resto de los planos. *(Nota: ese plano específico permanecería en `procesando` hasta intervención técnica o reinicio exitoso).*  

#### Frecuencia

* En cada arranque o reinicio del servicio backend (`api`).

---

## 2. Brechas, Discrepancias y Acciones Faltantes en `DH-CU-01` a `DH-CU-06`

A continuación se detallan las divergencias detectadas entre [`Especificación Formal de Casos de Uso (Metodología Alistair Cockburn).md`](Especificaci%C3%B3n%20Formal%20de%20Casos%20de%20Uso%20(Metodolog%C3%ADa%20Alistair%20Cockburn).md) y el sistema implementado:

### En la estructura general del documento

* **Salto de sección:** El documento pasa directamente de `## 2. Identificación de Actores e Interesados` ([línea 26](Especificaci%C3%B3n%20Formal%20de%20Casos%20de%20Uso%20(Metodolog%C3%ADa%20Alistair%20Cockburn).md#L26)) a `## 4. Modelo de Estados Ortogonal del Sistema` ([línea 44](Especificaci%C3%B3n%20Formal%20de%20Casos%20de%20Uso%20(Metodolog%C3%ADa%20Alistair%20Cockburn).md#L44)). Falta la Sección 3.
* **Campo inexistente `ia_intentos`:** `DH-CU-01`, `DH-CU-02` y `DH-CU-06` refieren a una columna `ia_intentos`, pero en [`models.py`](../backend/src/models.py) esa columna no existe: el conteo de intentos se calcula en base a las filas de la tabla `procesamientos_ia` (`intento = 1..3`) y el `ia_estado` actual del plano.
* **Subsistema de almacenamiento desactualizado:** Se menciona "almacenamiento local / disco", cuando la implementación real utiliza **Supabase Storage** ([`storage_client.py`](../backend/src/compartido/storage_client.py)).

### `DH-CU-01`: Cargar plano histórico

1. **Nombre real de acción y mensaje:** El botón dice **"Guardar y analizar"** ([`planos-historicos.html`](../front/planos-historicos.html#L44)), no *"Cargar plano"*; la validación de archivo vacío muestra *"El archivo digital del plano es obligatorio para continuar."* y también bloquea selección múltiple (*"Solo podés subir un plano a analizar a la vez."*).
2. **Desajuste de formato `TIFF`:** El paso 5 documenta `JPG, JPEG, PNG, TIFF, PDF o WEBP` y [`config.py`](../backend/src/config.py#L15) incluye `image/tiff` en backend, pero tanto el `<input accept>` ([`planos-historicos.html`](../front/planos-historicos.html#L35)) como la regex de [`cu-cargar.js`](../front/js/cu-cargar.js#L76) **rechazan archivos `.tiff`**.
3. **Regla de exclusividad / bloqueo de análisis concurrente (omitida):** Solo puede haber un plano activo en `ia_estado = 'procesando'` a la vez. Tanto el frontend (`#btn-cargar` cambia a `"Analizando plano en curso…"`) como el backend (`_comprobar_sin_analisis_en_curso` devuelve HTTP 409 `codigo: "procesando_ia"`) bloquean cargas simultáneas.
4. **Límite de 20 MB en Proxy Nginx (omitido en extensiones):** [`front/nginx.conf`](../front/nginx.conf#L27) fija `client_max_body_size 20M;`; si se excede, Nginx devuelve HTTP 413 y [`state.js`](../front/js/state.js#L13) muestra el error de tamaño máximo (20 MB).
5. **Nomenclatura preliminar opcional + validaciones y duplicados (omitidas):** Si los 4 campos están completos, valida formato (HTTP 422 `nomenclatura`) y unicidad contra planos activos (HTTP 409 `duplicado`); si es parcial o vacía, `nomenclatura` queda `NULL`. Además realiza vinculación automática con `tramitacion.inmuebles` (`id_inmueble`).
6. **Rasterización síncrona de PDF y cálculo de hash (omitidos):** En el `POST /planos`, calcula `hash_sha256` y `tamano_bytes`, y si es PDF renderiza la página 0 a JPEG y la sube a Supabase Storage (`{key}.preview.jpg`); un PDF corrupto aborta con HTTP 400.
7. **Cola de recientes y baja directa desde Carga (omitidas):** `#cargar-recientes` lista planos en análisis/pendientes con badges de estado e incluye botón **"Eliminar"** (`DH-CU-07`), ausente en `DH-CU-01`.
8. **Auditoría inicial y creación de `ProcesamientoIA` (omitidas):** Crea `EventoAuditoria(accion="Carga", motivo="Creación de plano")` con `ip_origen` y la fila inicial en `procesamientos_ia(intento=1, estado="procesando", version_prompt, parametros_preprocesamiento)`.

### `DH-CU-02`: Procesar plano histórico mediante visión artificial

1. **Pipeline real en 2 pasos + fallback IRAM + fallback plano completo:** Primero preprocesa copia ligera (máx. 1600px, autocontrast, nitidez) y pide bounding box del cajetín (`PROMPT_DETECCION_CAJETIN`); si falla usa coordenadas IRAM `[600, 500, 1000, 1000]`. Luego recorta en alta resolución con padding del 2%, optimiza (`preprocess_cajetin`, máx. 1800px) y extrae JSON (`PROMPT_EXTRACCION_CAJETIN`); si falla el recorte reintenta sobre la imagen completa, y `_extraer()` ejecuta hasta 2 pasadas internas antes de marcar error ([`worker.py`](../backend/src/planos/worker.py#L44-L52), [`vision_client.py`](../backend/src/compartido/vision_client.py#L468-L499)).
2. **Resolución dinámica de modelo y `.env`:** Consulta `/api/tags` en Ollama/Ngrok (Google Colab) resolviendo el alias `colab-activo` o el modelo más reciente disponible, recargando `.env` en caliente sin reiniciar contenedor.
3. **Bifurcación crítica cuando el plano ya fue validado (omitida):** El documento asume que siempre escribe directamente sobre las columnas de `Plano`. En [`worker.py`](../backend/src/planos/worker.py#L82-L90), si `plano.estado != 'pendiente'`, **no sobrescribe la catalogación**: guarda el JSON en `plano.ia_propuesta` para ser resuelto en **`DH-CU-08`**.
4. **Trazabilidad en `procesamientos_ia`:** Persiste `modelo_ia`, `version_prompt`, `parametros_preprocesamiento`, `texto_extraido_raw`, `respuesta_json_raw` (incluso ante JSON inválido), `duracion_ms` y `error`.

### `DH-CU-03`: Validar plano histórico

1. **Visor interactivo inexistente:** El paso 2 promete *"Visor gráfico interactivo (zoom digital, paneo y rotación)"* y Requisitos Especiales exige manejo en memoria de zoom sobre alta resolución. En [`cu-validar.js`](../front/js/cu-validar.js#L202-L203) solo existe una etiqueta `<img class="thumb">` estática y el enlace para abrir/descargar el original (`DH-CU-10`).
2. **Casilla `"Sin ubicación catastral asignada"` y estado `sin_ubicacion` inexistentes en carga/validación:** Aunque el modelo de estados (Sección 4) y las listas de Modificar/Consultar contemplan `sin_ubicacion`, la extensión 5a de `DH-CU-03` **no está implementada**: no existe dicha casilla en UI y `validar_plano()` asigna incondicionalmente `EstadoPlano.validado` ([`planos/services.py`](../backend/src/planos/services.py#L167)).
3. **Carga manual no cambia `ia_estado` a `no_aplica`:** Contrariamente a la extensión 4a3 del documento, `validar_plano()` nunca modifica `ia_estado`; únicamente vacía los inputs editables en UI al pulsar **"Cargar datos a mano"** (conservando `texto_extraido` como solo lectura).
4. **Etiqueta real del botón:** Se llama **"Confirmar e indexar"** (no *"Guardar validación y catalogar"*).
5. **Reintento también desde estado `completado` y botón de falla:** La barra `#v-acciones-plano` expone **"Reintentar análisis (k/3)"** incluso cuando la IA tuvo éxito (`ia_estado === 'completado'`).
6. **`texto_extraido` inmutable:** Es `readonly` en UI y explícitamente ignorado por `_aplicar_datos()` en backend ([`planos/services.py`](../backend/src/planos/services.py#L163-L165)).
7. **Campos omitidos en formulario de validación:** `ubicacion_fisica`, `expediente` y `direccion_referencia` ingresados en `DH-CU-01` no aparecen en el formulario de Validar (ni de Modificar), aunque el backend sigue auditándolos en `CAMPOS_AUDITORIA`.
8. **Brecha de validación en backend vs. frontend:** La UI valida `anio` (`1..2100` entero), `escala` (`Sin escala`, `Escalas varias`, o ratio `N:M`), longitudes máximas y nomenclatura; en backend (`PlanoValidar`), `anio` y `escala` **no tienen validadores Pydantic** (a diferencia de lo que asume [`test_validacion_campos.py`](../backend/tests/test_validacion_campos.py), que falla si no están en `PlanoValidar`/`PlanoModificar`).
9. **Extensiones faltantes:** Rechazos HTTP 409 (`El plano ya fue validado...`), HTTP 409 (`duplicado`), HTTP 422 (`nomenclatura`) y revinculación automática de `id_inmueble` + `EventoAuditoria(accion="Validación", motivo="Validación inicial")`.

### `DH-CU-04`: Modificar catalogación de plano histórico

1. **Acciones y capacidades completamente omitidas en el documento:**
   * Gestión de propuestas de reanálisis IA (**`DH-CU-08`**).
   * Reanálisis IA desde ficha catalogada + polling cada `1.5s` hasta `60s`.
   * Consulta del historial de auditoría paginado y diff de cambios (**`DH-CU-09`**).
   * Baja lógica desde ficha catalogada (**`DH-CU-07`**).
   * Enlace al archivo original y previsualización (**`DH-CU-10`**).
2. **Restricciones y etiquetas reales del motivo y botón:** El campo *"Motivo de la modificación"* tiene límite de **180 caracteres** en UI con contador en vivo (`0 / 180 caracteres`), aunque en backend solo verifica que no sea vacío. El botón se llama **"Guardar cambios"** (no *"Guardar modificaciones"*).
3. **Brecha en Precondición en backend:** `modificar_plano()` en [`planos/services.py`](../backend/src/planos/services.py#L380-L419) **no comprueba** que `plano.estado` sea `validado` o `sin_ubicacion` y `_aplicar_datos()` lo fuerza siempre a `validado` (un plano `sin_ubicacion` modificado pasaría automáticamente a `validado`, y un `pendiente` invocado por API directa también).
4. **Brecha en estructura del snapshot JSON:** El documento formaliza `Δ = {campo: (valor_anterior, valor_nuevo)}`, mientras que la implementación guarda dos columnas JSON completas separadas en `eventos_auditoria`: `valores_anteriores` y `valores_nuevos` con los 19 campos de `CAMPOS_AUDITORIA`, calculando el diff en tiempo de renderizado en [`cu-modificar.js`](../front/js/cu-modificar.js#L69-L89).

### `DH-CU-05`: Consultar catálogo de planos históricos

1. **Arquitectura real del buscador vs. especificación:** El documento describe botón *"Buscar"*, envío de parámetros por querystring a `GET /planos` y paginación desde backend. En realidad ([`cu-consultar.js`](../front/js/cu-consultar.js#L48-L140)):
   * No existe botón *"Buscar"*: el filtrado es **reactivo en vivo (`oninput`) en memoria del navegador**.
   * El frontend descarga todo vía `GET /planos` **sin filtros**, filtra localmente `validado`/`sin_ubicacion`, y pagina de a **5 resultados** (`Anterior` / `Siguiente`).
   * Por su parte, el endpoint `GET /planos` solo admite `?estado=...` y `?q=...` (**búsqueda exacta por nomenclatura completa de 4 partes**), y si se llama directamente sin `estado`, también retorna planos `pendiente` (violando la Garantía Mínima si se consume la API sin filtro).
2. **Filtros prometidos inexistentes vs. filtros reales:** El paso 2 afirma que se puede buscar por *"profesional actuante o texto libre"*, pero la UI real únicamente ofrece **Calle** (substring sin tildes sobre `direccion_referencia || ubicacion`), **Número** (coincidencia exacta de altura), **Expediente** (substring), **Año** (prefijo de hasta 4 dígitos) y prefijos de **Circunscripción, Sección, Manzana, Parcela**.
3. **Mensaje vacío y descarga:** El mensaje real es *"No se encontraron planos catalogados con esos criterios de búsqueda."* o *"Todavía no hay planos catalogados."* El botón de descarga siempre entrega el **archivo original** vía `/archivo` (no da a elegir JPEG optimizado vs. original), ni abre modal interactivo con zoom/rotación.
4. **Defecto en visualización del historial:** Como se detalló en `DH-CU-09`, `cu-consultar.js` busca `d.historial` en lugar de `d.eventos`, dejando el historial oculto en esta pestaña.

### `DH-CU-06`: Gestionar reintento de análisis fallido

1. **Endpoint erróneo en doc:** Se documenta `POST /planos/{id}/reintentar`, pero la ruta real es `POST /planos/{plano_id}/reintentar_ia?usuario_id=...` ([`planos/routes.py`](../backend/src/planos/routes.py#L130-L142)).
2. **Precondición real mucho más amplia:** No requiere `ia_estado = 'error'`. Funciona también cuando `ia_estado = 'completado'` tanto desde **Validar** (`usuario_id="Validador"`) como desde **Modificar** sobre planos ya catalogados (`usuario_id="Operador"`). Solo rechaza `no_aplica` y `procesando`.
3. **Auditoría y UI:** Registra `EventoAuditoria(accion="Observación", motivo="Reintento de análisis IA")` y crea una nueva fila `ProcesamientoIA`. Cuando el límite de 3 intentos se alcanza, la UI reemplaza el botón por el indicador inhabilitado `"Límite de 3 intentos alcanzado"` (no muestra el texto exacto citado en 5a3 del doc, salvo cuando falla la API al intentar dispararlo). Además, desde Modificar inicia el polling de 60s y encadena con **`DH-CU-08`**.

---

## 3. Verificación Exhaustiva 1-a-1: Todas las Acciones del Sistema

| Componente / Ubicación | Acción / Proceso verificable en el sistema | Caso de Uso asociado (Actual / Nuevo) |
| :--- | :--- | :--- |
| [`front/index.html`](../front/index.html) | Ingresar al módulo *Planos Históricos* / Ver módulo pendiente *Tramitar Nueva Obra* | **`DH-CU-00`** *(Nuevo)* |
| [`front/app.js`](../front/app.js#L12-L41) | Cambiar entre pestañas (`Cargar`, `Validar`, `Modificar`, `Consultar`) | Paso de navegación SPA en **`DH-CU-00` / `01` / `03` / `04` / `05`** |
| [`front/app.js`](../front/app.js#L43-L60) | Polling automático cada 5s para refrescar colas y bandejas | **`DH-CU-11`** *(Nuevo)* |
| [`database-status.js`](../front/js/database-status.js) + `GET /health/database` | Verificar salud de PostgreSQL al cargar, cada 15s y al evento `online` | **`DH-CU-11`** *(Nuevo)* |
| [`routes.py`](../backend/src/routes.py#L9-L11) (`GET /health`) | Consultar disponibilidad del servicio API y tamaño de cola de tareas | **`DH-CU-11`** *(Nuevo)* |
| [`cu-cargar.js`](../front/js/cu-cargar.js) + `POST /planos` | Adjuntar plano, ingresar nomenclatura/guarda/expediente/dirección y pulsar *Guardar y analizar* | `DH-CU-01` *(Requiere actualizar)* |
| [`cu-cargar.js`](../front/js/cu-cargar.js#L137) | Eliminar plano desde la cola de recientes en Cargar | **`DH-CU-07`** *(Nuevo)* |
| [`worker.py`](../backend/src/planos/worker.py#L44-L241) + [`vision_client.py`](../backend/src/compartido/vision_client.py) | Detectar cajetín, recortar en alta resolución, inferir JSON, escribir campos o `ia_propuesta` | `DH-CU-02` *(Requiere actualizar)* |
| [`main.py`](../backend/src/main.py#L15-L19) + `init_db()` + `_planos_sin_terminar()` | Verificar `tramitacion.inmuebles`, migrar esquema `planos` y reencolar análisis inconclusos | **`DH-CU-12`** *(Nuevo)* |
| [`cu-validar.js`](../front/js/cu-validar.js) + `PUT /planos/{id}/validar` | Seleccionar pendiente, cotejar datos, corregir y pulsar *Confirmar e indexar* | `DH-CU-03` *(Requiere actualizar)* |
| [`cu-validar.js`](../front/js/cu-validar.js#L80-L94) | Pulsar *Cargar datos a mano* ante fallo de IA y transcribir manualmente | `DH-CU-03` (Ext. 4a, *corregir regla `no_aplica`*) |
| [`cu-validar.js`](../front/js/cu-validar.js#L146) + `POST /planos/{id}/reintentar_ia` | Pulsar *Reintentar análisis (k/3)* desde Validar (con IA en error o completada) | `DH-CU-06` *(Requiere actualizar)* |
| [`cu-validar.js`](../front/js/cu-validar.js#L171) | Pulsar *Eliminar plano* desde Validar (en opciones de falla o ficha normal) | **`DH-CU-07`** *(Nuevo)* |
| [`cu-modificar.js`](../front/js/cu-modificar.js) + `PUT /planos/{id}/modificar` | Seleccionar catalogado, editar campos, ingresar motivo (≤180) y pulsar *Guardar cambios* | `DH-CU-04` *(Requiere actualizar)* |
| [`cu-modificar.js`](../front/js/cu-modificar.js#L426-L478) | Pulsar *Reintentar análisis IA (k/3)* en plano catalogado + polling 60s | `DH-CU-06` + **`DH-CU-08`** |
| [`cu-modificar.js`](../front/js/cu-modificar.js#L223-L376) + `POST .../descartar_propuesta` | Abrir *Ver Antes y Después*, elegir campos, *Aplicar cambios* o *Descartar propuesta* | **`DH-CU-08`** *(Nuevo)* |
| [`cu-modificar.js`](../front/js/cu-modificar.js#L139-L172) | Consultar tabla paginada de historial (10/pág.), paginar y desplegar *Ver detalle* diff | **`DH-CU-09`** *(Nuevo)* |
| [`cu-modificar.js`](../front/js/cu-modificar.js#L480-L496) | Pulsar *Eliminar plano* desde Modificar catalogación | **`DH-CU-07`** *(Nuevo)* |
| [`cu-consultar.js`](../front/js/cu-consultar.js) + `GET /planos` + `GET /planos/{id}` | Filtrar en tiempo real por calle/altura/expediente/año/nomenclatura, paginar (5/pág.) y ver ficha | `DH-CU-05` *(Requiere actualizar)* |
| `GET /planos/{id}/preview` y `GET /planos/{id}/archivo` | Ver miniatura (con rasterización perezosa de PDF en Storage) y abrir/descargar binario original | **`DH-CU-10`** *(Nuevo, incluido desde Validar, Modificar y Consultar)* |

---

## 4. Matriz de Cobertura y Trazabilidad Actualizada (Propuesta para Sección 6)

| Caso de Uso | Nivel de Cockburn | Actor Principal | Disparador | Implementación Real en Código |
| :--- | :---: | :--- | :--- | :--- |
| **DH-CU-00:** Gestionar ciclo integral del acervo en Portal GIUOS *(Nuevo)* | Nivel Nube ☁️ | Dirección de Catastro / Usuario | Acceso al portal GIUOS | [`front/index.html`](../front/index.html), [`front/planos-historicos.html`](../front/planos-historicos.html) |
| **DH-CU-01:** Cargar plano histórico | Nivel Mar 🌊 | Operador Documental | Envío en pestaña *Cargar plano* | [`cu-cargar.js`](../front/js/cu-cargar.js), `POST /planos` ([`planos/services.py`](../backend/src/planos/services.py#L179-L265)) |
| **DH-CU-02:** Procesar plano histórico mediante visión artificial | Subfunción 🐟 | Motor de Procesamiento (Worker) | Tarea encolada en `asyncio.Queue` | [`worker.py`](../backend/src/planos/worker.py), [`vision_client.py`](../backend/src/compartido/vision_client.py), [`preprocessing.py`](../backend/src/compartido/preprocessing.py) |
| **DH-CU-03:** Validar plano histórico | Nivel Mar 🌊 | Validador Documental | Selección en *Validar y catalogar* | [`cu-validar.js`](../front/js/cu-validar.js), `PUT /planos/{id}/validar` |
| **DH-CU-04:** Modificar catalogación de plano histórico | Nivel Mar 🌊 | Validador / Operador | Selección en *Modificar catalogación* | [`cu-modificar.js`](../front/js/cu-modificar.js), `PUT /planos/{id}/modificar` |
| **DH-CU-05:** Consultar catálogo de planos históricos | Nivel Mar 🌊 | Usuario del Sistema | Acceso/escritura en *Consultar* | [`cu-consultar.js`](../front/js/cu-consultar.js), `GET /planos`, `GET /planos/{id}` |
| **DH-CU-06:** Gestionar reintento / reanálisis de IA | Subfunción / Mar secundario 🐟/🌊 | Validador / Operador | Clic en *Reintentar análisis* (Validar o Modificar) | [`cu-validar.js`](../front/js/cu-validar.js#L253-L273), [`cu-modificar.js`](../front/js/cu-modificar.js#L426-L478), `POST /planos/{id}/reintentar_ia` |
| **DH-CU-07:** Dar de baja lógica un plano histórico *(Nuevo)* | Nivel Mar 🌊 | Operador / Validador | Clic en *Eliminar* / *Eliminar plano* | `cu-cargar.js`, `cu-validar.js`, `cu-modificar.js`, `DELETE /planos/{id}` |
| **DH-CU-08:** Revisar y resolver propuesta de reanálisis IA *(Nuevo)* | Nivel Mar 🌊 | Validador / Operador | Banner de propuesta o fin de reanálisis en Modificar | [`cu-modificar.js`](../front/js/cu-modificar.js#L223-L376), `POST /planos/{id}/descartar_propuesta`, `PUT /planos/{id}/modificar` |
| **DH-CU-09:** Consultar historial de auditoría de un plano *(Nuevo)* | Mar secundario / Subfunción 🌊/🐟 | Validador / Operador / Auditor | Apertura de ficha con eventos | [`cu-modificar.js`](../front/js/cu-modificar.js#L139-L172), [`cu-consultar.js`](../front/js/cu-consultar.js#L150-L156), `GET /planos/{id}` |
| **DH-CU-10:** Previsualizar y descargar binario original *(Nuevo)* | Subfunción 🐟 | Usuario / Validador / Operador | Renderizado de detalle o clic en enlace de archivo | `GET /planos/{id}/preview`, `GET /planos/{id}/archivo`, [`storage_client.py`](../backend/src/compartido/storage_client.py) |
| **DH-CU-11:** Monitorear BD, salud del servicio y refresco periódico *(Nuevo)* | Subfunción 🐟 | Sistema (Timers SPA) / Operaciones | Carga de vista, cada 5s/15s, evento `online`, `/health*` | [`database-status.js`](../front/js/database-status.js), [`app.js`](../front/app.js#L43-L60), `GET /health`, `GET /health/database` |
| **DH-CU-12:** Inicializar esquema, validar catastro externo y recuperar cola *(Nuevo)* | Subfunción 🐟 | Sistema (`lifespan` al arranque) | Inicio de contenedor/proceso API | [`main.py`](../backend/src/main.py#L14-L19), [`models.py`](../backend/src/models.py#L583-L633), [`worker.py`](../backend/src/planos/worker.py#L125-L145) |
