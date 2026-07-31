# Reglas de negocio

- Usuarios: nombre mínimo 3, correo válido y único, tipo enumerado; DELETE cambia a INACTIVO.
- Propuestas: título mínimo 5, descripción mínima 10, nace BORRADOR, actualizar cambia su fecha y DELETE la lleva a CERRADA.
- Estudiantes: deben ser usuarios ESTUDIANTE y ACTIVO; no se duplican. El último solo puede retirarse en BORRADOR.
- Director: debe ser DOCENTE y ACTIVO; solo uno ACTIVO. DELETE desactiva la relación.
- Módulos/fases: orden positivo y único entre activos; un módulo con fases activas no se desactiva.
- Progreso: porcentaje 0 para NO_INICIADA, 1–99 para EN_PROGRESO y 100 para COMPLETADA. No existe DELETE ni reapertura implícita.
- Agentes: tipo enumerado y nombre único entre activos; DELETE desactiva.
- Evaluaciones: niveles 1–5; se conserva el historial y puede consultarse la más reciente. No existe DELETE.
- Documentos: solo metadatos validados; no se cargan archivos ni se generan URL prefirmadas.

Las referencias cruzadas son catálogos mock sembrados dentro de cada Lambda. La consistencia transversal definitiva requiere PostgreSQL y transacciones.
