# Arquitectura del backend

```text
Cliente → API Gateway HTTP API → Lambda por dominio → servicio → repositorio en memoria
```

AWS SAM define Python 3.11, x86_64, 10 segundos y 256 MB. `ProyectoGradoApi` usa etapa `dev` y CORS configurable. Las Lambdas son Usuarios, Propuestas, Catálogos, Progreso, Evaluaciones y Documentos.

Cada función contiene `app.py` (HTTP API v2, rutas y respuestas), `models.py` (Pydantic 2), `service.py` (reglas) y `repository.py` (mock reiniciable). Los endpoints son públicos solo durante desarrollo; Cognito se añadirá cuando el contrato y los roles se estabilicen.

Las utilidades HTTP mínimas se duplican deliberadamente porque cada `CodeUri` se empaqueta aislado. Una Layer no aportaría suficiente beneficio en esta fase; véase ADR-003.
