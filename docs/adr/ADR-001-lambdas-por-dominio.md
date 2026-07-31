# ADR-001: Lambdas por dominio

Estado: aceptado.

Se agrupan endpoints en seis Lambdas: usuarios; propuestas/relaciones; catálogos; progreso; evaluaciones; documentos. Evita una Lambda por ruta y mantiene cohesión. El coste temporal es duplicar referencias mock entre funciones; PostgreSQL resolverá la consistencia compartida.
