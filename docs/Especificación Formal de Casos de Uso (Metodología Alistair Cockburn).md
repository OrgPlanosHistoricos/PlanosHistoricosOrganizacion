# Documento de Especificación de Requisitos de Software: Casos de Uso

**Proyecto:** Sistema de Digitalización y Gestión del Patrimonio Cartográfico e Histórico  
**Referencia Metodológica:** Alistair Cockburn (*Writing Effective Use Cases*)  
**Versión:** 3.0 (Definitiva \- Alineada con código fuente e implementación real)  
**Estado:** Formal / Aprobado

---

## 1\. Marco Metodológico y Alcance del Sistema

Este documento define los requisitos funcionales del sistema basándose en el estándar metodológico propuesto por Alistair Cockburn en *Writing Effective Use Cases*. El modelado se enfoca estrictamente en los **objetivos de los actores** (lo que el usuario busca lograr con valor de negocio medible), controlando los niveles de abstracción para evitar la proliferación de microcasos técnicos o la simplificación ingenua en meros mantenimientos CRUD.

### 1.1. Alcance

El sistema abarca el ciclo de vida completo de incorporación, procesamiento automatizado por visión artificial, control de calidad humano, catalogación territorial/archivística y consulta pública del acervo cartográfico histórico municipal.

### 1.2. Clasificación de Niveles de Casos de Uso

Se adopta la iconografía y categorización de Cockburn:

* **Nivel Resumen (Nivel Nube / Cometa ☁️):** Objetivos estratégicos de negocio de largo aliento que agrupan múltiples sesiones de trabajo (ej. *Preservar y hacer accesible el patrimonio cartográfico histórico*).  
* **Nivel Objetivo de Usuario (Nivel Mar 🌊):** Representa una tarea discreta y completa realizada por un actor en una sesión ininterrumpida (típicamente de 2 a 20 minutos), que deja los datos en un estado consistente y genera valor directo al negocio.  
* **Nivel Subfunción (Nivel Pez / Submarino 🐟):** Tareas técnicas, procesos en segundo plano o pasos subordinados requeridos para satisfacer un objetivo de usuario, pero que carecen de valor de negocio completo de forma aislada.

---

## 2\. Identificación de Actores e Interesados

### 2.1. Actores Principales

* **Operador Documental:** Personal técnico responsable de la digitalización física, escaneo e ingesta inicial de los planos históricos al entorno informático.  
* **Validador Documental:** Especialista técnico o archivero encargado del control de calidad, cotejo visual, transcripción correctiva, asignación de nomenclatura catastral definitiva y resolución de incidencias.  
* **Usuario del Sistema:** Ciudadano, investigador o agente de la administración pública que interactúa con el catálogo para localizar, inspeccionar y descargar documentación técnica histórica.  
* **Motor de Procesamiento (Worker Asíncrono):** Actor de sistema automatizado (componente `worker.py` con Qwen2.5-VL y Pillow) que procesa las tareas encoladas en segundo plano.

### 2.2. Interesados y sus Intereses (Stakeholders)

* **Dirección de Catastro y Archivo Histórico:** Requiere que cada plano digitalizado cuente con fidelidad respecto del original físico, ubicación topográfica trazable y georreferenciación confiable.  
* **Área de Auditoría y Legales:** Exige trazabilidad inmutable de todas las modificaciones introducidas sobre planos ya validados, con registro de autor, fecha, dirección IP y justificación administrativa explícita.  
* **Equipo de Operaciones / TI:** Necesita que los procesos intensivos de inteligencia artificial y visión artificial no bloqueen la interfaz web ni degraden la experiencia de usuario.

---

## 3\. Análisis de Alternativas y Decisiones de Estructuración

En estricta observancia de los lineamientos de Cockburn sobre cohesión, independencia y tratamiento de operaciones CRUD, se analizaron y resolvieron las siguientes disyuntivas de diseño:

### Decisión A: Unificación de Validación y Catalogación (DH-CU-03)

* **Alternativa 1 (Separada en dos CU):** Modelar *DH-CU-03: Validar datos documentales* y *DH-CU-04: Catalogar plano territorialmente* por separado.  
  * *Ventaja aparente:* Menor cantidad de campos por pantalla.  
  * *Desventaja metodológica:* Fragmentación artificial. Para el Validador, dejar un plano validado a nivel de texto pero sin parcela o con catalogación trunca no constituye un objetivo de negocio autosuficiente. Dejaba un estado intermedio ambiguo y generaba fricción innecesaria.  
* **Alternativa 2 (Unificada \- Seleccionada):** Modelar un único caso de uso a nivel del mar: **Validar y catalogar plano histórico**.  
  * *Justificación Cockburn:* Representa la meta indivisible del actor: *"Tomar un documento extraído y dejarlo formalmente incorporado al catálogo oficial"*. Coincide con la implementación de pantalla dividida en `cu-validar.js` y el endpoint atómico `PUT /planos/{id}/validar`.

### Decisión B: Tratamiento de "Modificar" vs. CRUD Genérico (DH-CU-04)

* **Análisis de CRUD:** Cockburn desaconseja crear casos aislados para "Modificar X" salvo que posean disparadores propios, reglas estrictas y valor diferenciado.  
* **Justificación de Independencia:** Modificar un plano previamente catalogado **no** es una simple edición de formulario. Implica un cambio sobre un documento ya publicado, exigiendo obligatoriamente un **motivo de justificación**, captura de IP, generación de snapshots diferenciales en JSON y persistencia inmutable en la tabla `eventos_auditoria`. Posee disparador diferenciado, actor con responsabilidad de auditoría y reglas de negocio propias.

### Decisión C: Tratamiento de la Extracción por IA / Visión (DH-CU-02)

* Se clasifica formalmente como un **Caso de Uso de Nivel Subfunción / Tarea de Sistema Asíncrona (🐟)**. No es ejecutado directamente por un humano en sesión interactiva; es orquestado por el Worker en segundo plano a partir del evento emitido por la carga.

---

## 4\. Modelo de Estados Ortogonal del Sistema

El sistema implementa dos máquinas de estados desacopladas e independientes (`models.py`), garantizando robustez ante fallas técnicas:

$$\text{Estado Integral} = \big( \text{EstadoPlano}, \, \text{EstadoIA} \big)$$

```
  [EstadoPlano (Gestión Humana)]
        |
        +---> 'pendiente'       (Cargado, a la espera de validación)
        |
        +---> 'validado'        (Aprobado territorialmente; forma parte del catálogo)
        |
        +---> 'sin_ubicacion'   (Validado documentalmente; sin parcela actual identificable)

  [EstadoIA (Proceso Técnico de Visión)]
        |
        +---> 'procesando'      (Worker ejecutando recorte e inferencia)
        |
        +---> 'completado'      (Texto y carátula extraídos con éxito)
        |
        +---> 'error'           (Falla en modelo/timeout; habilita reintentos)
        |
        +---> 'no_aplica'       (Resuelto vía transcripción manual humana)
```

---

## 5\. Especificación Completa de Casos de Uso (Formato Fully Dressed)

### DH-CU-01: Cargar plano histórico

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos  
* **Nivel:** Objetivo de Usuario (Nivel Mar 🌊)  
* **Actor Principal:** Operador Documental  
* **Interesados e Intereses:**  
  * *Operador:* Desea registrar el archivo digital rápidamente sin bloqueos mientras se analiza.  
  * *Validador:* Requiere que la imagen cuente con la integridad requerida y metadatos iniciales de contexto.  
  * *Administrador:* Desea optimizar el almacenamiento y asegurar formatos estandarizados.  
* **Precondición:** El operador tiene acceso al entorno web y posee el archivo digitalizado.  
* **Garantías Mínimas:** Si el proceso falla o se aborta, el archivo físico temporal se elimina y no se crea ningún registro huérfano en la base de datos.  
* **Garantías de Éxito:** El archivo se almacena en el repositorio de archivos, se crea el registro con `estado = 'pendiente'` y `ia_estado = 'procesando'`, y se despacha la tarea de análisis en segundo plano.  
* **Disparador:** El operador selecciona "Cargar plano histórico" en la interfaz.

#### Escenario Principal de Éxito

1. El operador accede a la vista de carga de planos.  
2. El sistema despliega el formulario requiriendo el archivo gráfico e indicando los campos opcionales de guarda física (caja, estantería, legajo) y nomenclatura preliminar.  
3. El operador adjunta el archivo digital y completa los datos de contexto disponibles.  
4. El operador presiona "Cargar plano".  
5. El sistema valida el formato binario y la extensión del archivo (JPG, JPEG, PNG, TIFF, PDF o WEBP).  
6. El sistema sanitiza y normaliza la nomenclatura catastral si fue ingresada.  
7. El sistema almacena el archivo binario en el disco/almacenamiento bajo un identificador único seguro.  
8. El sistema persiste el registro en la base de datos con `estado = 'pendiente'`, `ia_estado = 'procesando'` e `ia_intentos = 0`.  
9. El sistema despacha el evento asíncrono para el procesamiento por IA (DH-CU-02).  
10. El sistema retorna confirmación de carga exitosa (HTTP 201 Created) y notifica al operador que el plano quedó en cola de análisis.

#### Extensiones

* **3a. El operador no selecciona ningún archivo:**  
  * 3a1. El frontend cancela el envío, resalta el campo en rojo y muestra el mensaje: *"Debe seleccionar un archivo digital para continuar"*.  
* **5a. El archivo no corresponde a un formato admisible o supera el peso máximo:**  
  * 5a1. El backend rechaza la petición con error HTTP 400 Bad Request.  
  * 5a2. El frontend informa: *"Formato de archivo no soportado o archivo corrupto"*. El operador selecciona otro archivo.  
* **7a. Falla de escritura en el subsistema de almacenamiento (disco lleno/permisos):**  
  * 7a1. El sistema aborta la transacción, registra el incidente técnico y responde HTTP 500\.  
  * 7a2. El sistema garantiza que no se persiste ningún registro parcial en la base de datos.

#### Requisitos Especiales

* Tiempo de respuesta de la API para completar la carga y responder al frontend menor a 2.5 segundos (el procesamiento de IA no debe computar en este lapso).

#### Frecuencia

* Continua durante jornadas de digitalización (decenas a cientos de veces por día).

---

### DH-CU-02: Procesar plano histórico mediante visión artificial

* **Alcance:** Worker de Procesamiento / Pipeline de IA  
* **Nivel:** Subfunción (Nivel Pez 🐟)  
* **Actor Principal:** Motor de Procesamiento (Worker en segundo plano)  
* **Interesados e Intereses:**  
  * *Validador Documental:* Desea contar con campos precargados para reducir la carga de tipeo.  
  * *Equipo de TI:* Exige aislamiento de fallas para que la indisponibilidad de la GPU/Ollama no voltee el servidor web.  
* **Precondición:** Existe un plano persistido con `ia_estado = 'procesando'`.  
* **Garantías Mínimas:** Ante cualquier fallo técnico, la excepción se captura, el plano pasa a `ia_estado = 'error'` con el log técnico persistido, y el worker queda libre para la siguiente tarea.  
* **Garantías de Éxito:** Se extraen los datos de la carátula, se actualizan las columnas del registro del plano y se marca `ia_estado = 'completado'`.  
* **Disparador:** Recepción del mensaje encolado generado por DH-CU-01 o DH-CU-06.

#### Escenario Principal de Éxito

1. El worker asíncrono (`worker.py`) toma la tarea de procesamiento del plano desde la cola.  
2. El sistema recupera el archivo binario desde el almacenamiento local.  
3. **Fase de Recorte (Pillow):** El sistema analiza y recorta el área inferior/derecha correspondiente al cajetín o carátula del plano para aislar el texto crítico y reducir el costo computacional.  
4. **Fase de Inferencia Multimodal (Qwen2.5-VL vía Ollama):** El sistema despacha la imagen procesada al modelo con el prompt de extracción documental estructurada.  
5. El modelo reconoce los atributos: título, profesional actuante, fecha de confección, expediente, nomenclatura y notas marginales.  
6. El sistema formatea y mapea el texto crudo extraído a las columnas de la entidad plano.  
7. El sistema persiste los datos en la base de datos y actualiza `ia_estado = 'completado'`.  
8. El worker finaliza la tarea y queda a la espera del próximo evento.

#### Extensiones

* **3a/4a. El modelo falla, se pierde la conexión con Ollama o se agota el tiempo de espera (timeout):**  
  * 4a1. El worker intercepta el error técnico y genera la traza en los logs.  
  * 4a2. El sistema incrementa el contador `ia_intentos = ia_intentos + 1`.  
  * 4a3. El sistema actualiza el registro a `ia_estado = 'error'` con el detalle de la falla.  
  * 4a4. La tarea finaliza (el plano queda listo para resolución en DH-CU-06).

#### Variaciones Tecnológicas

* Modelos multimodales locales servidos a través del motor Ollama.

---

### DH-CU-03: Validar y catalogar plano histórico

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos  
* **Nivel:** Objetivo de Usuario (Nivel Mar 🌊)  
* **Actor Principal:** Validador Documental  
* **Interesados e Intereses:**  
  * *Validador Documental:* Desea una interfaz fluida para contrastar imagen vs. texto y catalogar de una sola vez.  
  * *Dirección de Catastro:* Requiere que la nomenclatura esté normalizada y validada.  
  * *Público General:* Necesita que los planos publicados sean fidedignos y legibles.  
* **Precondición:** El plano se encuentra en estado `pendiente`.  
* **Garantías Mínimas:** Si el validador abandona la pantalla sin guardar, los datos preliminares del plano no sufren alteraciones.  
* **Garantías de Éxito:** El plano pasa a estado `validado` (o `sin_ubicacion`), se normaliza su nomenclatura catastral definitiva, se guardan los datos de archivo físico y queda **inmediatamente disponible en el catálogo de consultas**.  
* **Disparador:** El validador selecciona un plano de la bandeja de pendientes en `cu-validar.js`.

#### Escenario Principal de Éxito

1. El validador ingresa a la bandeja de validación y selecciona un plano.  
2. El sistema solicita los datos (`GET /planos/{id}`) y despliega la vista dividida:  
   * Panel izquierdo/superior: Visor gráfico interactivo (zoom digital, paneo y rotación).  
   * Panel derecho/inferior: Formulario unificado con los metadatos documentales sugeridos por la IA y los campos de catalogación territorial y guarda física.  
3. El validador examina la imagen en el visor y coteja la información extraída (título, autor, fechas, expediente).  
4. El validador corrige los datos mal interpretados o completa los casilleros vacíos.  
5. El validador ingresa o ratifica la **catalogación territorial** (circunscripción, sección, manzana, parcela, calle y altura).  
6. El validador confirma la **ubicación de guarda física** (caja, legajo, estantería).  
7. El validador presiona "Guardar validación y catalogar".  
8. El frontend envía la solicitud `PUT /planos/{id}/validar` con el payload unificado.  
9. El backend valida la estructura de los campos y normaliza la nomenclatura catastral conformando la clave unificada de indexación.  
10. El backend actualiza la entidad asignando `estado = 'validado'`.  
11. El backend responde HTTP 200 OK.  
12. El frontend muestra notificación de confirmación, retira el plano de la bandeja de pendientes y lo habilita en el catálogo general.

#### Extensiones

* **3a. El documento es ilegible, es un duplicado inservible o no corresponde al archivo:**  
  * 3a1. El validador selecciona la opción "Dar de baja plano".  
  * 3a2. El sistema solicita confirmación explícita para evitar eliminaciones accidentales.  
  * 3a3. El frontend despacha la solicitud `DELETE /planos/{id}`.  
  * 3a4. El backend aplica la baja lógica del plano en la base de datos y retira el binario del circuito.  
  * 3a5. El caso de uso finaliza.  
* **4a. El plano proviene de una falla de análisis (`ia_estado = 'error'`):**  
  * 4a1. El formulario se presenta con los campos textuales vacíos.  
  * 4a2. El validador transcribe manualmente todos los datos observados en el visor.  
  * 4a3. El backend, al recibir la validación, establece además `ia_estado = 'no_aplica'`. El flujo continúa en el paso 7\.  
* **5a. La parcela no existe en el trazado moderno o no se localizan datos territoriales precisos:**  
  * 5a1. El validador marca la casilla "Sin ubicación catastral asignada".  
  * 5a2. El sistema ajusta el destino del estado a `estado = 'sin_ubicacion'`.  
  * 5a3. El plano se incorpora al catálogo público permitiendo su hallazgo por expediente, autor o fecha, prescindiendo del filtro de parcela. El flujo continúa en el paso 6\.

#### Requisitos Especiales

* El visor gráfico debe procesar imágenes de alta resolución sin degradar la memoria del navegador.

---

### DH-CU-04: Modificar catalogación de plano histórico

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos  
* **Nivel:** Objetivo de Usuario (Nivel Mar 🌊)  
* **Actor Principal:** Validador Documental / Operador  
* **Interesados e Intereses:**  
  * *Área de Auditoría y Legales:* Exige conocer con precisión quién, cuándo, por qué y qué valores específicos cambiaron en un documento público.  
  * *Validador:* Necesita corregir fe de erratas o incorporar datos territoriales hallados con posterioridad.  
* **Precondición:** El plano se encuentra en estado `validado` o `sin_ubicacion`.  
* **Garantías Mínimas:** Si el usuario no fundamenta el motivo del cambio, ninguna modificación es aplicada y no se registra alteración en auditoría.  
* **Garantías de Éxito:** Se actualizan los atributos modificados en la tabla del plano y se crea un registro histórico inmutable en `eventos_auditoria` con el motivo, la IP y el snapshot JSON comparativo.  
* **Disparador:** El usuario localiza un plano catalogado y selecciona la acción "Modificar" en `cu-modificar.js`.

#### Escenario Principal de Éxito

1. El usuario busca y selecciona el plano catalogado que requiere corrección.  
2. El sistema presenta el formulario editable cargado con la totalidad de los datos vigentes del plano.  
3. El usuario altera los valores necesarios (fechas, profesional, nomenclatura, calle, guarda física).  
4. El sistema presenta de forma destacada el campo obligatorio **"Motivo de la modificación"**.  
5. El usuario redacta la fundamentación administrativa del cambio.  
6. El usuario pulsa "Guardar modificaciones".  
7. El frontend envía la solicitud `PUT /planos/{id}/modificar` conteniendo los campos actualizados y el motivo.  
8. El backend valida que la cadena del motivo contenga texto significativo (no vacía ni solo espacios).  
9. El backend captura la dirección IP del cliente y el identificador de usuario.  
10. El backend calcula el delta de diferencias y construye un snapshot JSON: $$\Delta = \{ \text{campo}: (\text{valor\_anterior}, \, \text{valor\_nuevo}) \}$$  
11. El backend persiste el evento en la tabla `eventos_auditoria` (registrando `plano_id`, `fecha_hora`, `usuario`, `ip`, `motivo`, `snapshot`).  
12. El backend actualiza la entidad `plano`, reindexando la nomenclatura catastral si fue modificada.  
13. El backend responde HTTP 200 OK.  
14. El frontend notifica el éxito de la modificación y refresca la ficha.

#### Extensiones

* **5a. El usuario omite ingresar el motivo de modificación:**  
  * 5a1. El frontend valida localmente, marca el campo en rojo y bloquea el botón de envío impidiendo la llamada HTTP.  
* **8a. La petición arriba al backend sin motivo o con espacios en blanco:**  
  * 8a1. El backend rechaza la transacción con HTTP 400 Bad Request (`{"error": "El motivo de la modificación es obligatorio"}`).  
  * 8a2. No se aplica ninguna modificación en base de datos.  
* **6a. El usuario decide descartar los cambios:**  
  * 6a1. El usuario presiona "Cancelar".  
  * 6a2. El frontend recarga los datos originales en pantalla sin realizar peticiones de mutación al servidor.

---

### DH-CU-05: Consultar catálogo de planos históricos

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos  
* **Nivel:** Objetivo de Usuario (Nivel Mar 🌊)  
* **Actor Principal:** Usuario del Sistema  
* **Interesados e Intereses:**  
  * *Investigador / Ciudadano:* Desea localizar planos por diversas vías (calle, parcela, año, profesional) con previsualización rápida.  
  * *Municipio:* Busca transparentar y facilitar el acceso a la información pública cartográfica.  
* **Precondición:** Existen planos en estado `validado` o `sin_ubicacion`.  
* **Garantías Mínimas:** El sistema no divulga planos en estado `pendiente` ni binarios marcados con baja lógica.  
* **Garantías de Éxito:** El sistema entrega la lista de resultados paginada según los filtros y provee acceso al visor detallado y a la descarga directa del archivo.  
* **Disparador:** El usuario accede a la pestaña "Consultar" (`cu-consultar.js`).

#### Escenario Principal de Éxito

1. El usuario accede al módulo de consultas.  
2. El usuario introduce uno o varios parámetros en el panel de búsqueda:  
   * Parámetros territoriales: Calle, número, circunscripción, sección, manzana, parcela.  
   * Parámetros documentales: Año, expediente, profesional actuante o texto libre.  
3. El usuario presiona "Buscar".  
4. El frontend despacha la consulta `GET /planos` con la querystring de filtros.  
5. El backend ejecuta la consulta en la base de datos restringiendo estrictamente los resultados a `estado IN ('validado', 'sin_ubicacion')`.  
6. El backend retorna la colección paginada de planos coincidentes junto con sus URLs de previsualización.  
7. El frontend renderiza la lista de resultados con tarjetas informativas y miniaturas optimizadas.  
8. El usuario hace clic sobre un plano para examinarlo en detalle.  
9. El sistema abre el modal/pantalla de inspección solicitando la imagen en alta definición vía `/planos/{id}/preview` o `/planos/{id}/archivo`.  
10. El usuario presiona "Descargar archivo".  
11. El sistema transfiere el binario directamente al navegador del usuario (formato original o JPEG optimizado según su elección).

#### Extensiones

* **5a. Ningún documento coincide con los criterios de búsqueda provistos:**  
  * 5a1. El frontend muestra el mensaje: *"No se encontraron planos que coincidan con los filtros ingresados"*.  
  * 5a2. El sistema sugiere limpiar filtros y el usuario reintenta la búsqueda.

---

### DH-CU-06: Gestionar reintento de análisis fallido

* **Alcance:** Sistema de Digitalización y Gestión de Planos Históricos  
* **Nivel:** Subfunción con valor de Usuario (Nivel Pez / Mar secundario 🐟/🌊)  
* **Actor Principal:** Validador Documental  
* **Interesados e Intereses:**  
  * *Validador:* Necesita recuperar planos que fallaron por indisponibilidad transitoria del servicio de IA sin tener que transcribir todo a mano.  
  * *Administrador:* Requiere un freno estricto para que un plano no procesable no sature la cola de inferencia infinitamente.  
* **Precondición:** El plano posee `ia_estado = 'error'`.  
* **Garantías Mínimas:** El sistema nunca supera el umbral máximo de 3 reintentos.  
* **Garantías de Éxito:** El plano se reencola para una nueva pasada del pipeline o se fuerza su resolución por carga manual directa.  
* **Disparador:** El validador pulsa "Reintentar análisis" en la vista de validación (`cu-validar.js`).

#### Escenario Principal de Éxito (Reintento Asíncrono)

1. El validador visualiza un plano marcado con la insignia de error técnico en la lista de revisión.  
2. El validador selecciona el plano y examina la traza simplificada de la falla reportada.  
3. El validador presiona el botón "Reintentar análisis".  
4. El frontend envía la solicitud `POST /planos/{id}/reintentar`.  
5. El backend constata que `ia_intentos < 3`.  
6. El backend incrementa el valor de `ia_intentos`.  
7. El backend actualiza `ia_estado = 'procesando'`.  
8. El backend encola nuevamente la tarea para el worker (DH-CU-02).  
9. El backend responde HTTP 200 OK.  
10. El frontend notifica que el documento ha vuelto a la cola de procesamiento y deshabilita temporalmente el reintento.

#### Extensiones

* **5a. El contador `ia_intentos` alcanzó o superó el límite de 3 ejecuciones:**  
  * 5a1. El backend rechaza la operación respondiendo HTTP 400 Bad Request (`{"error": "Límite máximo de 3 reintentos alcanzado"}`).  
  * 5a2. El frontend inhabilita permanentemente el botón "Reintentar análisis" para dicho registro.  
  * 5a3. El sistema muestra la notificación: *"El análisis automático ha agotado sus intentos. Debe proceder con la carga manual de datos"*.  
  * 5a4. El validador resuelve el plano mediante la alternativa de transcripción manual directa contemplada en el paso 4a de DH-CU-03.

---

## 6\. Matriz de Cobertura y Trazabilidad

| Caso de Uso | Nivel de Cockburn | Actor Principal | Disparador | Implementación en Código |
| :---- | :---: | :---- | :---- | :---- |
| **DH-CU-01:** Cargar plano histórico | Nivel Mar 🌊 | Operador Documental | Interacción en pestaña Cargar | `routes.py` (`POST /planos`) |
| **DH-CU-02:** Procesar plano histórico | Subfunción 🐟 | Motor de Procesamiento (Worker) | Evento asíncrono encolado | `worker.py` (Qwen2.5-VL / Pillow) |
| **DH-CU-03:** Validar y catalogar plano | Nivel Mar 🌊 | Validador Documental | Selección en bandeja de revisión | `cu-validar.js` (`PUT /planos/{id}/validar`, `DELETE /planos/{id}`) |
| **DH-CU-04:** Modificar catalogación | Nivel Mar 🌊 | Validador / Operador | Acción Modificar en catálogo | `cu-modificar.js` (`PUT /planos/{id}/modificar`, `eventos_auditoria`) |
| **DH-CU-05:** Consultar catálogo | Nivel Mar 🌊 | Usuario del Sistema | Ingreso de filtros en buscador | `cu-consultar.js` (`GET /planos`, `/preview`, `/archivo`) |
| **DH-CU-06:** Gestionar reintento de análisis | Subfunción 🐟 | Validador Documental | Clic en Reintentar análisis | `services.py` (`POST /planos/{id}/reintentar`) |

&nbsp;