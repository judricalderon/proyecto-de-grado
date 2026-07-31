# Proyecto Grado

Backend serverless para gestionar proyectos de grado. Esta versión ofrece una API REST por dominios con validación Pydantic 2 y repositorios simulados en memoria.

## Estado y arquitectura

```text
Cliente → API Gateway HTTP API → Lambda por dominio → service.py → repository.py (mock)
```

AWS SAM/CloudFormation define seis Lambdas Python 3.11, x86_64, 256 MB y timeout de 10 segundos. La etapa es `dev`. Los endpoints siguen públicos durante desarrollo; no hay Cognito todavía.

## Entidades

Usuario, PropuestaProyecto, PropuestaEstudiante, PropuestaDirector, Modulo, Fase, ProgresoFase, Agente, EvaluacionEstado y DocumentoSoporte. Consulte [modelo-dominio.md](docs/modelo-dominio.md) y [reglas-negocio.md](docs/reglas-negocio.md).

## Estructura

```text
backend/
├── template.yaml
├── samconfig.toml
├── functions/
│   ├── usuarios/
│   ├── propuestas/
│   ├── catalogos/
│   ├── progreso/
│   ├── evaluaciones/
│   └── documentos/
└── tests/
docs/
├── api.md
├── modelo-dominio.md
├── reglas-negocio.md
├── arquitectura-backend.md
├── limitaciones-mock.md
└── adr/
```

Cada dominio separa `app.py`, `service.py`, `repository.py` y `models.py`.

## Endpoints

- Usuarios: CRUD `/usuarios`.
- Propuestas: CRUD `/propuestas`, estudiantes y director.
- Catálogos: CRUD `/modulos`, `/fases` y `/agentes`.
- Progreso: consulta, creación y actualización bajo `/propuestas/{id}/progreso`.
- Evaluaciones: historial, creación y evaluación más reciente.
- Documentos: CRUD de metadatos; no se cargan archivos.

El inventario completo y contratos están en [api.md](docs/api.md).

## CORS

`FrontendOrigin` vale `http://localhost:3000` por defecto. En producción páselo como parámetro SAM con el dominio HTTPS real. No se usa origen comodín ni credenciales CORS.

## Requisitos y comandos

- Python 3.11 accesible en `PATH`.
- AWS SAM CLI.
- AWS CLI con perfil `proyecto-grado`.

```powershell
cd backend
sam validate --lint --profile proyecto-grado --region us-east-1
sam build --profile proyecto-grado
python -m unittest discover -s tests -p "test_*.py"
sam deploy --profile proyecto-grado --region us-east-1
```

Después del primer `sam deploy --guided`, SAM puede reutilizar `samconfig.toml`.

## Limitaciones

Los repositorios en memoria no son una base de datos: los datos pueden desaparecer entre invocaciones y no se comparten entre Lambdas. Las referencias cruzadas actuales son mocks sembrados. No existen Aurora/RDS/PostgreSQL, Cognito, Bedrock, almacenamiento S3 de documentos ni URL prefirmadas. El S3 administrado por SAM solo guarda artefactos de despliegue.

## Próximas fases

Sustituir repositorios por PostgreSQL local y luego Aurora PostgreSQL; añadir migraciones y transacciones; integrar Cognito y autorización por roles; almacenar documentos en S3; finalmente evaluar agentes con Bedrock.
