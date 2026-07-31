# API de propuestas

La API conserva `GET /propuestas/health`, `GET/POST /propuestas` y `GET /propuestas/{id}`. Añade `PUT/DELETE /propuestas/{id}`, estudiantes y director.

El contrato canónico usa `titulo_tentativo`, `descripcion_inicial`, `estado_general`, `fecha_creacion` y `fecha_actualizacion`. Por compatibilidad, POST/PUT todavía acepta `titulo` y `descripcion`; `estudianteId` heredado se acepta pero la asignación debe realizarse explícitamente mediante `/propuestas/{id_propuesta}/estudiantes`.

DELETE cierra la propuesta (`CERRADA`); no elimina datos. Estudiantes y director validan referencias mock ACTIVO y tipo adecuado. No existe persistencia real.
