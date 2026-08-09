# Integración de Progreso con Aurora PostgreSQL

## Arquitectura y alcance

```text
API Gateway HTTP API
  → ProgresoFunction
    → RDS Data API
      → Aurora PostgreSQL
```

`ProgresoFunction` persiste en `progreso_fase` y valida relaciones contra `propuesta_proyecto` y `fase`. No entra en la VPC, no abre PostgreSQL 5432 y no utiliza RDS Proxy.

Estado actual:

- `UsuariosFunction` → PostgreSQL.
- `PropuestasFunction` → PostgreSQL.
- `CatalogosFunction` → PostgreSQL.
- `ProgresoFunction` → PostgreSQL.
- `EvaluacionesFunction` → mock.
- `DocumentosFunction` → mock.

## Relaciones y unicidad

Cada registro referencia una propuesta y una fase existentes. La fase debe estar activa al crear progreso. La restricción `UNIQUE (id_propuesta, id_fase)` impide duplicar el progreso de una misma fase en una propuesta; el servicio responde `PROGRESS_ALREADY_EXISTS`.

Las claves foráneas evitan relaciones huérfanas. Los errores relacionales concurrentes se traducen sin exponer SQL, ARNs, secretos ni mensajes de AWS.

## Estados, porcentajes y fechas

- `NO_INICIADA` requiere 0 % y crea `fecha_inicio = null`, `fecha_cierre = null`.
- `EN_PROGRESO` requiere 1–99 % y establece `fecha_inicio` si todavía es nula.
- `COMPLETADA` requiere 100 % y establece `fecha_cierre`; al crear también establece `fecha_inicio`.

Toda creación establece `fecha_ultima_actualizacion`. Cada PUT actualiza esa fecha. Se conserva la regla existente que rechaza `COMPLETADA → NO_INICIADA` con `REOPEN_REQUIRED`; no existe una ruta de reapertura implícita ni DELETE.

Estas reglas se validan tanto en Pydantic como mediante CHECK constraints de PostgreSQL.

## Data API, configuración e IAM

`database.py` usa `boto3.client("rds-data")`, convierte parámetros y resultados, y lee:

- `DB_CLUSTER_ARN` desde `proyecto-grado-dev-DbClusterArn`.
- `DB_SECRET_ARN` desde `proyecto-grado-dev-DbSecretArn`.
- `DB_NAME` desde `proyecto-grado-dev-DatabaseName`.

La política restringe las acciones Data API al clúster importado y `GetSecretValue` al secreto importado. No utiliza `Resource: "*"` ni permisos administrativos.

Ante `DatabaseResumingException` se realizan tres intentos totales, con esperas de 0,5 y 1 segundo. Otros errores no se reintentan.

## Transacciones

No se abren transacciones explícitas. Crear o actualizar progreso se resuelve con una sola sentencia `INSERT` o `UPDATE`, que PostgreSQL ejecuta atómicamente. Estado, porcentaje y fechas se escriben juntos.

## Errores de negocio

- Propuesta inexistente: `PROPOSAL_NOT_FOUND`.
- Fase inexistente o inactiva: `PHASE_NOT_FOUND`.
- Progreso inexistente: `PROGRESS_NOT_FOUND`.
- Relación duplicada: `PROGRESS_ALREADY_EXISTS`.
- Reapertura implícita prohibida: `REOPEN_REQUIRED`.
- Estado/porcentaje incoherente: `VALIDATION_ERROR`.

## Validación local

```powershell
python -m unittest discover -s tests -p "test_*.py"
sam validate --lint
sam build --no-cached
```

Las pruebas mockean boto3/Data API y no llaman AWS.
