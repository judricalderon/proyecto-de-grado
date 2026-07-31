# Guía completa de pruebas de la API

Documento derivado de `backend/template.yaml`, los adaptadores Lambda, modelos Pydantic, servicios y repositorios actuales. Base URL: `{{baseUrl}}`, incluyendo el stage, por ejemplo `https://{api-id}.execute-api.us-east-1.amazonaws.com/dev`.

## Convenciones reales

- Las respuestas usan `Content-Type: application/json`.
- Listas: `{"data": [...], "count": n}`. Elementos: `{"data": {...}}`. Creaciones: `{"message": "...", "data": {...}}`.
- Error de validación: `{"error":"Datos de entrada inválidos","code":"VALIDATION_ERROR","details":[...]}` (400).
- Ruta no reconocida: `{"error":"Ruta no encontrada","code":"ROUTE_NOT_FOUND","details":[]}` (404).
- Error inesperado: `{"error":"Error interno del servidor","code":"INTERNAL_SERVER_ERROR","details":[]}` (500).
- Los IDs generados por servicios usan UUID v4, salvo catálogos, que anteponen `MOD-`, `FASE-` o `AG-`. Los modelos que reciben IDs los declaran como `str`; no aplican validación de formato UUID.
- Fechas de salida son generadas por el servicio en UTC, ISO 8601 con sufijo `Z`; no son campos de entrada.
- Los repositorios son mocks separados por Lambda. Las referencias disponibles de forma inicial incluyen `PROP-001`, `MOD-001`, `FASE-001` a `FASE-007`, `USR-001`, `USR-002` y `USR-010`, según el dominio.

## Esquemas Pydantic reales

| Modelo | Obligatorios | Opcionales/default | Restricciones |
|---|---|---|---|
| `UsuarioCreate` | `nombre`, `correo`, `tipo_usuario` | Ninguno | `nombre`: string ≥3, trim. `correo`: regex `[^@\\s]+@[^@\\s]+\\.[^@\\s]+`, trim y minúsculas. `tipo_usuario`: `ESTUDIANTE`, `DOCENTE`, `ADMIN`. |
| `UsuarioUpdate` | Ninguno | `nombre`, `correo`, `tipo_usuario`, `estado` | Campos `null` se excluyen. `nombre` ≥3; correo como arriba; `estado`: `ACTIVO`, `INACTIVO`. |
| `PropuestaCreate` | `titulo_tentativo`, `descripcion_inicial` | Ninguno | Trim; título ≥5; descripción ≥10. El servicio también acepta aliases heredados `titulo` y `descripcion`. |
| `PropuestaUpdate` | Ninguno | `titulo_tentativo`, `descripcion_inicial`, `estado_general` | `estado_general`: `BORRADOR`, `EN_REVISION`, `APROBADA`, `RECHAZADA`, `CERRADA`; mínimos como creación. |
| `EstudianteCreate` | `id_estudiante` | Ninguno | String ≥1. |
| `DirectorCreate` | `id_docente` | Ninguno | String ≥1. |
| `ModuloIn` | `nombre`, `descripcion`, `orden` | `activo=true` | Strings con trim y ≥1; `orden` entero >0. |
| `FaseIn` | `id_modulo`, `nombre`, `descripcion`, `orden` | `activo=true` | `id_modulo` string; nombre/descripción ≥1; orden entero >0. |
| `AgenteIn` | `nombre`, `tipo_agente`, `descripcion` | `activo=true` | Tipo: `SOCRATICO`, `ORIENTADOR`, `EVALUADOR`, `DOCUMENTAL`; strings con trim y ≥1. |
| `ProgresoIn` | `id_fase`, `estado`, `porcentaje_avance` | Ninguno | Porcentaje 0–100; `NO_INICIADA`=0, `EN_PROGRESO`=1–99, `COMPLETADA`=100. |
| `ProgresoUpdate` | `estado`, `porcentaje_avance` | Ninguno | Misma coherencia estado/porcentaje. |
| `EvaluacionIn` | `nivel_claridad`, `nivel_argumentacion`, `nivel_coherencia`, `fortalezas`, `aspectos_por_fortalecer` | `observaciones=""` | Niveles enteros 1–5; strings obligatorios con trim y ≥1. |
| `DocumentoIn` | `tipo_documento`, `nombre_archivo`, `ruta` | Ninguno | Tipo: `PROPUESTA`, `ACTA`, `ANEXO`, `INFORME`, `OTRO`; strings con trim y ≥1. |
| `DocumentoUpdate` | Ninguno | `tipo_documento`, `nombre_archivo`, `ruta` | Mismas restricciones; `null` se excluye. |

## Usuarios

Query parameters reales de `GET /usuarios`: `tipo_usuario` y `estado`; el código compara strings pero no valida sus enums en query.

| Método | Ruta | Descripción | Path params | Query | Body requerido | Body opcional | Ejemplo POST | Ejemplo PUT | Éxito | Error ejemplo | HTTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/usuarios/health` | Salud | Ninguno | Ninguno | Sin body | — | — | — | `{"data":{"service":"usuarios","status":"ok"}}` | Error común 500 | 200 |
| GET | `/usuarios` | Lista/filtra usuarios | Ninguno | `tipo_usuario`, `estado` opcionales | Sin body | — | — | — | `{"data":[],"count":0}` | Error común 500 | 200 |
| GET | `/usuarios/{id}` | Lee usuario | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"USR-001","nombre":"Ana Estudiante","correo":"ana@example.com","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO","fecha_creacion":"2026-07-28T19:00:00Z","fecha_ultimo_acceso":null}}` | `{"error":"Usuario no encontrado","code":"USER_NOT_FOUND","details":[]}` | 200/404 |
| POST | `/usuarios` | Crea usuario | Ninguno | Ninguno | `nombre`, `correo`, `tipo_usuario` | Ninguno | `{"nombre":"Laura Gómez","correo":"laura@example.com","tipo_usuario":"ESTUDIANTE"}` | — | `{"message":"Usuario creado correctamente","data":{"id":"uuid","nombre":"Laura Gómez","correo":"laura@example.com","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO","fecha_creacion":"...Z","fecha_ultimo_acceso":null}}` | `{"error":"El correo ya está registrado","code":"EMAIL_ALREADY_EXISTS","details":[]}` | 201/400/409 |
| PUT | `/usuarios/{id}` | Actualiza usuario | `id`: string | Ninguno | Ninguno | Los 4 campos de `UsuarioUpdate` | — | `{"nombre":"Laura Gómez Actualizada","estado":"ACTIVO"}` | `{"data":{"id":"uuid","nombre":"Laura Gómez Actualizada","correo":"laura@example.com","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO","fecha_creacion":"...Z","fecha_ultimo_acceso":null}}` | `{"error":"Usuario no encontrado","code":"USER_NOT_FOUND","details":[]}` | 200/400/404/409 |
| DELETE | `/usuarios/{id}` | Cambia estado a INACTIVO | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"uuid","estado":"INACTIVO"}}` | `USER_NOT_FOUND` | 200/404 |

## Propuestas, estudiantes y director

| Método | Ruta | Descripción | Path params | Query | Body requerido | Body opcional | Ejemplo POST | Ejemplo PUT | Éxito | Error ejemplo | HTTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/propuestas/health` | Salud | Ninguno | Ninguno | Sin body | — | — | — | `{"message":"Servicio de propuestas funcionando","service":"propuestas","status":"ok"}` | Error común 500 | 200 |
| GET | `/propuestas` | Lista propuestas | Ninguno | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | Error común 500 | 200 |
| GET | `/propuestas/{id}` | Lee propuesta | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"PROP-001","titulo_tentativo":"Sistema de acompañamiento para proyectos de grado","descripcion_inicial":"Plataforma para apoyar proyectos de grado.","estado_general":"BORRADOR","fecha_creacion":"...Z","fecha_actualizacion":"...Z"}}` | `{"error":"Propuesta no encontrada","code":"PROPOSAL_NOT_FOUND","details":[]}` | 200/404 |
| POST | `/propuestas` | Crea propuesta BORRADOR | Ninguno | Ninguno | `titulo_tentativo`, `descripcion_inicial` | Aliases aceptados: `titulo`, `descripcion` | `{"titulo_tentativo":"Sistema de tutorías inteligentes","descripcion_inicial":"Plataforma para acompañar proyectos académicos."}` | — | `{"message":"Propuesta creada correctamente","data":{"id":"uuid","titulo_tentativo":"Sistema de tutorías inteligentes","descripcion_inicial":"Plataforma para acompañar proyectos académicos.","estado_general":"BORRADOR","fecha_creacion":"...Z","fecha_actualizacion":"...Z"}}` | Error común 400 | 201/400 |
| PUT | `/propuestas/{id}` | Actualiza propuesta | `id`: string | Ninguno | Ninguno | Campos de `PropuestaUpdate`; aliases heredados | — | `{"titulo_tentativo":"Título actualizado","estado_general":"EN_REVISION"}` | `{"data":{"id":"uuid","titulo_tentativo":"Título actualizado","descripcion_inicial":"...","estado_general":"EN_REVISION","fecha_creacion":"...Z","fecha_actualizacion":"...Z"}}` | `PROPOSAL_NOT_FOUND` | 200/400/404 |
| DELETE | `/propuestas/{id}` | Cierre lógico | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"uuid","estado_general":"CERRADA","fecha_actualizacion":"...Z"}}` | `PROPOSAL_NOT_FOUND` | 200/404 |
| GET | `/propuestas/{id_propuesta}/estudiantes` | Lista relaciones | `id_propuesta`: string | Ninguno | Sin body | — | — | — | `{"data":[{"id":"REL-001","id_propuesta":"PROP-001","id_estudiante":"USR-001"}],"count":1}` | `PROPOSAL_NOT_FOUND` | 200/404 |
| POST | `/propuestas/{id_propuesta}/estudiantes` | Asigna estudiante activo | `id_propuesta`: string | Ninguno | `id_estudiante` | Ninguno | `{"id_estudiante":"USR-002"}` | — | `{"message":"Estudiante asignado correctamente","data":{"id":"uuid","id_propuesta":"PROP-001","id_estudiante":"USR-002"}}` | `{"error":"El estudiante ya está asignado","code":"STUDENT_ALREADY_ASSIGNED","details":[]}` | 201/400/404/409 |
| DELETE | `/propuestas/{id_propuesta}/estudiantes/{id_estudiante}` | Retira relación | Ambos strings | Ninguno | Sin body | — | — | — | `{"data":{"removed":true}}` | `ASSIGNMENT_NOT_FOUND` o `LAST_STUDENT_REQUIRED` | 200/404/409 |
| GET | `/propuestas/{id_propuesta}/director` | Obtiene director activo | `id_propuesta`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"uuid","id_propuesta":"PROP-001","id_docente":"USR-010","fecha_asignacion":"...Z","estado":"ACTIVO"}}`; puede ser `{"data":null}` | `PROPOSAL_NOT_FOUND` | 200/404 |
| POST | `/propuestas/{id_propuesta}/director` | Asigna docente activo | `id_propuesta`: string | Ninguno | `id_docente` | Ninguno | `{"id_docente":"USR-010"}` | — | `{"message":"Director asignado correctamente","data":{"id":"uuid","id_propuesta":"PROP-001","id_docente":"USR-010","fecha_asignacion":"...Z","estado":"ACTIVO"}}` | `ACTIVE_DIRECTOR_EXISTS`, `INVALID_USER_TYPE` o `USER_INACTIVE` | 201/400/404/409 |
| DELETE | `/propuestas/{id_propuesta}/director` | Desactiva director | `id_propuesta`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"uuid","estado":"INACTIVO"}}` | `DIRECTOR_NOT_FOUND` | 200/404 |

## Catálogos: módulos

Los PUT de catálogos reciben JSON parcial en la práctica: el servicio fusiona el recurso actual y luego valida el modelo completo.

| Método | Ruta | Descripción | Path params | Query | Body requerido | Body opcional | Ejemplo POST | Ejemplo PUT | Éxito | Error ejemplo | HTTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/modulos` | Lista módulos | Ninguno | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | Error común 500 | 200 |
| GET | `/modulos/{id}` | Lee módulo | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"MOD-001","nombre":"Desarrollo de propuestas de proyectos","descripcion":"Módulo inicial","orden":1,"activo":true}}` | `RESOURCE_NOT_FOUND` | 200/404 |
| POST | `/modulos` | Crea módulo | Ninguno | Ninguno | `nombre`, `descripcion`, `orden` | `activo=true` | `{"nombre":"Segundo módulo","descripcion":"Continuación del proceso","orden":2,"activo":true}` | — | `{"message":"Recurso creado correctamente","data":{"id":"MOD-uuid","nombre":"Segundo módulo","descripcion":"Continuación del proceso","orden":2,"activo":true}}` | `ACTIVE_ORDER_CONFLICT` | 201/400/409 |
| PUT | `/modulos/{id}` | Actualiza módulo | `id`: string | Ninguno | Ninguno en HTTP; resultado debe validar `ModuloIn` tras merge | Cualquier campo | — | `{"nombre":"Módulo actualizado"}` | `{"data":{"id":"MOD-001","nombre":"Módulo actualizado","descripcion":"Módulo inicial","orden":1,"activo":true}}` | `RESOURCE_NOT_FOUND`/`ACTIVE_ORDER_CONFLICT` | 200/400/404/409 |
| DELETE | `/modulos/{id}` | Desactiva módulo | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"MOD-uuid","activo":false}}` | `MODULE_HAS_ACTIVE_PHASES` | 200/404/409 |

## Catálogos: fases

| Método | Ruta | Descripción | Path params | Query | Body requerido | Body opcional | Ejemplo POST | Ejemplo PUT | Éxito | Error ejemplo | HTTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/fases` | Lista fases | Ninguno | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | Error común 500 | 200 |
| GET | `/fases/{id}` | Lee fase | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"FASE-001","id_modulo":"MOD-001","nombre":"Exploración inicial","descripcion":"Exploración inicial","orden":1,"activo":true}}` | `RESOURCE_NOT_FOUND` | 200/404 |
| GET | `/modulos/{id_modulo}/fases` | Lista fases por módulo | `id_modulo`: string | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | Error común 500 | 200 |
| POST | `/fases` | Crea fase | Ninguno | Ninguno | `id_modulo`, `nombre`, `descripcion`, `orden` | `activo=true` | `{"id_modulo":"MOD-001","nombre":"Cierre","descripcion":"Cierre del proyecto","orden":8,"activo":true}` | — | `{"message":"Recurso creado correctamente","data":{"id":"FASE-uuid","id_modulo":"MOD-001","nombre":"Cierre","descripcion":"Cierre del proyecto","orden":8,"activo":true}}` | `MODULE_NOT_ACTIVE`/`ACTIVE_ORDER_CONFLICT` | 201/400/409 |
| PUT | `/fases/{id}` | Actualiza fase | `id`: string | Ninguno | Ninguno tras merge | Cualquier campo | — | `{"descripcion":"Descripción actualizada"}` | `{"data":{"id":"FASE-001","id_modulo":"MOD-001","nombre":"Exploración inicial","descripcion":"Descripción actualizada","orden":1,"activo":true}}` | `RESOURCE_NOT_FOUND`/conflictos | 200/400/404/409 |
| DELETE | `/fases/{id}` | Desactiva fase | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"FASE-001","activo":false}}` | `RESOURCE_NOT_FOUND` | 200/404 |

## Catálogos: agentes

| Método | Ruta | Descripción | Path params | Query | Body requerido | Body opcional | Ejemplo POST | Ejemplo PUT | Éxito | Error ejemplo | HTTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/agentes` | Lista agentes | Ninguno | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | Error común 500 | 200 |
| GET | `/agentes/{id}` | Lee agente | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"AG-uuid","nombre":"Orientador","tipo_agente":"ORIENTADOR","descripcion":"Guía el proceso","activo":true}}` | `RESOURCE_NOT_FOUND` | 200/404 |
| POST | `/agentes` | Crea agente (sin ejecutar IA) | Ninguno | Ninguno | `nombre`, `tipo_agente`, `descripcion` | `activo=true` | `{"nombre":"Orientador","tipo_agente":"ORIENTADOR","descripcion":"Guía el proceso","activo":true}` | — | `{"message":"Recurso creado correctamente","data":{"id":"AG-uuid","nombre":"Orientador","tipo_agente":"ORIENTADOR","descripcion":"Guía el proceso","activo":true}}` | `ACTIVE_NAME_CONFLICT` | 201/400/409 |
| PUT | `/agentes/{id}` | Actualiza agente | `id`: string | Ninguno | Ninguno tras merge | Cualquier campo | — | `{"descripcion":"Guía actualizada"}` | `{"data":{"id":"AG-uuid","nombre":"Orientador","tipo_agente":"ORIENTADOR","descripcion":"Guía actualizada","activo":true}}` | `RESOURCE_NOT_FOUND`/`ACTIVE_NAME_CONFLICT` | 200/400/404/409 |
| DELETE | `/agentes/{id}` | Desactiva agente | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"AG-uuid","activo":false}}` | `RESOURCE_NOT_FOUND` | 200/404 |

## Progreso

| Método | Ruta | Descripción | Path params | Query | Body requerido | Body opcional | Ejemplo POST | Ejemplo PUT | Éxito | Error ejemplo | HTTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/progreso/health` | Salud | Ninguno | Ninguno | Sin body | — | — | — | `{"data":{"service":"progreso","status":"ok"}}` | Error común 500 | 200 |
| GET | `/propuestas/{id_propuesta}/progreso` | Lista progreso | `id_propuesta`: string | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | Error común 500 | 200 |
| GET | `/propuestas/{id_propuesta}/progreso/{id_fase}` | Lee progreso | Ambos strings | Ninguno | Sin body | — | — | — | `{"data":{"id":"uuid","id_propuesta":"PROP-001","id_fase":"FASE-001","estado":"EN_PROGRESO","porcentaje_avance":50,"fecha_inicio":"...Z","fecha_ultima_actualizacion":"...Z","fecha_cierre":null}}` | `PROGRESS_NOT_FOUND` | 200/404 |
| POST | `/propuestas/{id_propuesta}/progreso` | Crea progreso | `id_propuesta`: string | Ninguno | `id_fase`, `estado`, `porcentaje_avance` | Ninguno | `{"id_fase":"FASE-001","estado":"NO_INICIADA","porcentaje_avance":0}` | — | `{"message":"Progreso creado correctamente","data":{"id":"uuid","id_propuesta":"PROP-001","id_fase":"FASE-001","estado":"NO_INICIADA","porcentaje_avance":0,"fecha_inicio":null,"fecha_ultima_actualizacion":"...Z","fecha_cierre":null}}` | `PROGRESS_ALREADY_EXISTS`, `PROPOSAL_NOT_FOUND`, `PHASE_NOT_FOUND` | 201/400/404/409 |
| PUT | `/propuestas/{id_propuesta}/progreso/{id_fase}` | Actualiza progreso | Ambos strings | Ninguno | `estado`, `porcentaje_avance` | Ninguno | — | `{"estado":"EN_PROGRESO","porcentaje_avance":50}` | `{"data":{"id":"uuid","id_propuesta":"PROP-001","id_fase":"FASE-001","estado":"EN_PROGRESO","porcentaje_avance":50,"fecha_inicio":"...Z","fecha_ultima_actualizacion":"...Z","fecha_cierre":null}}` | `REOPEN_REQUIRED` o validación | 200/400/404/409 |

## Evaluaciones

| Método | Ruta | Descripción | Path params | Query | Body requerido | Body opcional | Ejemplo POST | Ejemplo PUT | Éxito | Error ejemplo | HTTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/evaluaciones/health` | Salud | Ninguno | Ninguno | Sin body | — | — | — | `{"data":{"service":"evaluaciones","status":"ok"}}` | Error común 500 | 200 |
| GET | `/propuestas/{id_propuesta}/evaluaciones` | Historial de propuesta | `id_propuesta`: string | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | `PROPOSAL_NOT_FOUND` | 200/404 |
| GET | `/propuestas/{id_propuesta}/fases/{id_fase}/evaluaciones` | Historial por fase | Ambos strings | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | `PROPOSAL_NOT_FOUND`/`PHASE_NOT_FOUND` | 200/404 |
| GET | `/propuestas/{id_propuesta}/fases/{id_fase}/evaluaciones/ultima` | Evaluación más reciente | Ambos strings | Ninguno | Sin body | — | — | — | `{"data":{"id":"uuid","id_propuesta":"PROP-001","id_fase":"FASE-001","nivel_claridad":5,"nivel_argumentacion":4,"nivel_coherencia":5,"fortalezas":"Claridad","aspectos_por_fortalecer":"Fuentes","observaciones":"","fecha_evaluacion":"...Z"}}` | `EVALUATION_NOT_FOUND` | 200/404 |
| POST | `/propuestas/{id_propuesta}/fases/{id_fase}/evaluaciones` | Crea evaluación histórica | Ambos strings | Ninguno | 5 campos obligatorios de `EvaluacionIn` | `observaciones` | `{"nivel_claridad":5,"nivel_argumentacion":4,"nivel_coherencia":5,"fortalezas":"Claridad del planteamiento","aspectos_por_fortalecer":"Referencias bibliográficas","observaciones":"Revisar fuentes"}` | — | `{"message":"Evaluación creada correctamente","data":{"id":"uuid","id_propuesta":"PROP-001","id_fase":"FASE-001","nivel_claridad":5,"nivel_argumentacion":4,"nivel_coherencia":5,"fortalezas":"Claridad del planteamiento","aspectos_por_fortalecer":"Referencias bibliográficas","observaciones":"Revisar fuentes","fecha_evaluacion":"...Z"}}` | Error común 400/refs 404 | 201/400/404 |
| GET | `/evaluaciones/{id}` | Lee evaluación | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"uuid","id_propuesta":"PROP-001","id_fase":"FASE-001","nivel_claridad":5,"nivel_argumentacion":4,"nivel_coherencia":5,"fortalezas":"Claridad","aspectos_por_fortalecer":"Fuentes","observaciones":"","fecha_evaluacion":"...Z"}}` | `EVALUATION_NOT_FOUND` | 200/404 |

No existe PUT ni DELETE para evaluaciones.

## Documentos

| Método | Ruta | Descripción | Path params | Query | Body requerido | Body opcional | Ejemplo POST | Ejemplo PUT | Éxito | Error ejemplo | HTTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/documentos/health` | Salud | Ninguno | Ninguno | Sin body | — | — | — | `{"data":{"service":"documentos","status":"ok"}}` | Error común 500 | 200 |
| GET | `/propuestas/{id_propuesta}/documentos` | Lista metadatos | `id_propuesta`: string | Ninguno | Sin body | — | — | — | `{"data":[],"count":0}` | Error común 500 | 200 |
| GET | `/documentos/{id}` | Lee metadato | `id`: string | Ninguno | Sin body | — | — | — | `{"data":{"id":"uuid","id_propuesta":"PROP-001","tipo_documento":"ANEXO","nombre_archivo":"anexo.pdf","ruta":"temporal/anexo.pdf","fecha_carga":"...Z"}}` | `DOCUMENT_NOT_FOUND` | 200/404 |
| POST | `/propuestas/{id_propuesta}/documentos` | Crea metadato; no sube archivo | `id_propuesta`: string | Ninguno | `tipo_documento`, `nombre_archivo`, `ruta` | Ninguno | `{"tipo_documento":"ANEXO","nombre_archivo":"anexo.pdf","ruta":"temporal/anexo.pdf"}` | — | `{"message":"Documento creado correctamente","data":{"id":"uuid","id_propuesta":"PROP-001","tipo_documento":"ANEXO","nombre_archivo":"anexo.pdf","ruta":"temporal/anexo.pdf","fecha_carga":"...Z"}}` | `PROPOSAL_NOT_FOUND` o validación | 201/400/404 |
| PUT | `/documentos/{id}` | Actualiza metadato | `id`: string | Ninguno | Ninguno | Campos de `DocumentoUpdate` | — | `{"nombre_archivo":"anexo-actualizado.pdf","tipo_documento":"INFORME"}` | `{"message":"Documento actualizado correctamente","data":{"id":"uuid","id_propuesta":"PROP-001","tipo_documento":"INFORME","nombre_archivo":"anexo-actualizado.pdf","ruta":"temporal/anexo.pdf","fecha_carga":"...Z"}}` | `DOCUMENT_NOT_FOUND`/validación | 200/400/404 |
| DELETE | `/documentos/{id}` | Elimina metadato mock | `id`: string | Ninguno | Sin body | — | — | — | Sin body | `DOCUMENT_NOT_FOUND` | 204/404 |

## Orden recomendado en Postman

1. Crear usuario y guardar `usuarioId`.
2. Crear propuesta y guardar `propuestaId`.
3. Crear módulo, fase y agente; guardar sus IDs.
4. Crear progreso usando una propuesta/fase que exista en el mock de esa Lambda (`PROP-001`, `FASE-001` inicialmente).
5. Crear evaluación y documento usando las mismas referencias mock.

Por la separación de repositorios mock, crear una propuesta en `PropuestasFunction` no la crea dentro de `ProgresoFunction`, `EvaluacionesFunction` o `DocumentosFunction`. Para esos dominios, el código actual reconoce `PROP-001`; esto cambiará al usar persistencia compartida.

## Colección Postman

Importe `postman/Proyecto-Grado.postman_collection.json`. Cambie `baseUrl` por la URL desplegada con `/dev`. La colección comprueba códigos esperados y guarda automáticamente los IDs creados en variables de colección.
