# Lineamientos de trabajo con Git y GitHub

## Ingeniería de Software II — 2026

Este documento establece las pautas de trabajo para los repositorios de la cátedra.

---

## 1. Rama principal

La rama `main` representa la versión oficial y estable del proyecto.

**No realizar `push` directo a `main`.**

Todo cambio debe desarrollarse en una rama independiente y luego incorporarse mediante un Pull Request.

Flujo recomendado:

```text
rama de trabajo
      ↓
   commits
      ↓
     push
      ↓
Pull Request
      ↓
  revisión
      ↓
    main
```

---

## 2. Crear una rama para cada tarea o funcionalidad

Cada nueva funcionalidad, corrección, cambio de documentación o refactorización debe realizarse en una rama propia.

Convenciones recomendadas:

```text
feature/login
feature/alta-expediente
feature/catalogacion-obra

fix/validacion-email
fix/error-login

docs/manual-instalacion

refactor/autenticacion

test/pruebas-login
```

El prefijo permite identificar rápidamente el propósito de la rama.

La barra `/` forma parte del nombre de la rama. No crea una carpeta ni una rama jerárquica.

Ejemplo:

```bash
git switch -c feature/login
```

Este comando crea la rama `feature/login` y cambia el entorno de trabajo a ella.

---

## 3. Actualizar `main` antes de comenzar

Antes de crear una nueva rama de trabajo:

```bash
git switch main
git pull origin main
```

Luego crear la rama:

```bash
git switch -c feature/nombre-funcionalidad
```

---

## 4. Realizar commits pequeños y coherentes

Cada commit debe representar un cambio concreto y comprensible.

Ejemplos recomendados:

```text
Agregar formulario de inicio de sesión
Implementar validación de correo electrónico
Corregir consulta de expedientes
Actualizar documentación de instalación
```

Evitar mensajes poco descriptivos:

```text
cambios
prueba
final
ahora si
modificaciones
```

---

## 5. Hacer `push` sobre la rama de trabajo

No subir cambios directamente a `main`.

Ejemplo:

```bash
git push -u origin feature/login
```

Luego de la primera publicación de la rama, normalmente alcanza con:

```bash
git push
```

---

## 6. Crear un Pull Request

Una vez terminada la tarea, debe crearse un Pull Request hacia `main`.

Ejemplo:

```text
feature/login
      ↓
Pull Request
      ↓
    main
```

El Pull Request debe indicar brevemente:

- qué se implementó;
- qué componentes o archivos se modificaron;
- cómo se probó;
- si existen tareas o consideraciones pendientes.

---

## 7. No hacer merge sin revisión

Los estudiantes no deben incorporar directamente sus cambios a `main` sin seguir el procedimiento de revisión definido por la cátedra.

El Pull Request debe quedar disponible para revisión antes de realizar el merge.

---

## 8. Mantener la rama actualizada

Si `main` cambia mientras se desarrolla una funcionalidad:

```bash
git switch main
git pull origin main

git switch feature/nombre-funcionalidad
git merge main
```

Los conflictos deben resolverse localmente antes de actualizar el Pull Request.

---

## 9. No utilizar `push --force`

Evitar:

```bash
git push --force
```

especialmente sobre:

```text
main
```

o sobre ramas compartidas por varios integrantes.

---

## 10. Coordinación entre integrantes

No modificar el trabajo de otro integrante sin coordinación previa.

Si dos estudiantes necesitan trabajar sobre los mismos archivos o componentes, deben acordar previamente cómo dividir o integrar las tareas para reducir conflictos.

---

## 11. No subir información sensible

Nunca versionar:

- contraseñas;
- tokens;
- claves API;
- claves privadas SSH;
- certificados privados;
- archivos `.env` con credenciales;
- datos sensibles de usuarios.

En su lugar, puede incluirse un archivo de ejemplo:

```text
.env.example
```

sin valores reales.

---

## 12. Utilizar `.gitignore`

El repositorio debe excluir archivos generados o propios del entorno local.

Ejemplos habituales:

```gitignore
.env
__pycache__/
node_modules/
.vscode/
.idea/
dist/
build/
*.log
```

El contenido de `.gitignore` debe adaptarse a las tecnologías utilizadas por cada proyecto.

---

## 13. Mantener el proyecto ejecutable

Antes de abrir un Pull Request se debe verificar que:

- el proyecto inicia correctamente;
- no se rompen funcionalidades existentes;
- las pruebas disponibles finalizan correctamente;
- no se introducen errores evidentes;
- las dependencias necesarias están documentadas.

---

## 14. No eliminar ramas ajenas

No borrar ramas creadas por otros integrantes sin autorización o coordinación previa.

---

## 15. Relacionar tareas, ramas y Pull Requests

Cuando el equipo utilice Issues o tareas, se recomienda mantener la relación:

```text
Issue / tarea
     ↓
rama
     ↓
commits
     ↓
Pull Request
     ↓
revisión
     ↓
main
```

---

## 16. Convenciones de nombres de ramas

Se recomienda utilizar:

```text
feature/...   nueva funcionalidad
fix/...       corrección de errores
docs/...      documentación
refactor/...  refactorización
test/...      pruebas
```

Ejemplos:

```text
feature/registro-usuario
feature/alta-obra
fix/error-autenticacion
docs/instalacion
refactor/servicio-usuarios
test/login
```

---

## 17. Trazabilidad del trabajo individual

La participación individual en el proyecto podrá observarse a través de:

- commits;
- ramas creadas;
- Pull Requests;
- revisiones;
- participación en resolución de conflictos;
- contribuciones al código y documentación.

Por este motivo, cada estudiante debe realizar sus propias confirmaciones utilizando su cuenta personal de GitHub.

---

## Regla principal

> `main` no es una rama de desarrollo.  
> Cada funcionalidad, corrección o cambio debe realizarse en una rama independiente y llegar a `main` mediante un Pull Request.
