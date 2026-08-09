# Integración de Evaluaciones con Aurora PostgreSQL

## Flujo

```text
API Gateway
  → EvaluacionesFunction
    → RDS Data API
      → Aurora PostgreSQL
```

`EvaluacionesFunction` persiste en `evaluacion_estado` y valida relaciones contra `propuesta_proyecto` y `fase`. No entra en la VPC, no abre PostgreSQL 5432 y no utiliza RDS Proxy.

## Estado de persistencia

- `UsuariosFunction` → PostgreSQL.
- `PropuestasFunction` → PostgreSQL.
- `CatalogosFunction` → PostgreSQL.
- `ProgresoFunction` → PostgreSQL.
- `EvaluacionesFunction` → PostgreSQL.
- `DocumentosFunction` → mock.

## Contrato y reglas

Se conservan las rutas y respuestas HTTP existentes. Los niveles de claridad, argumentación y coherencia admiten valores enteros de 1 a 5. `fortalezas` y `aspectos_por_fortalecer` son obligatorios; `observaciones` conserva `""` como valor predeterminado.

Antes de crear o consultar por propuesta/fase, el servicio comprueba que la propuesta exista y que la fase exista y esté activa. Las claves foráneas de PostgreSQL son el respaldo frente a concurrencia. Los CHECK de la tabla respaldan el rango 1..5.

Cada evaluación conserva un UUID sin prefijo. El servicio genera `fecha_evaluacion` en UTC con sufijo `Z` y el repositorio la convierte explícitamente a `timestamptz`. La consulta de última evaluación usa `ORDER BY fecha_evaluacion DESC LIMIT 1`; si no hay filas conserva `EVALUATION_NOT_FOUND` y HTTP 404.

## Data API, retry y transacciones

La función recibe `DB_CLUSTER_ARN`, `DB_SECRET_ARN` y `DB_NAME`. Todas las entradas variables viajan como parámetros de Data API y los registros se convierten usando `columnMetadata`.

Ante el código exacto `DatabaseResumingException`, `execute_statement()` realiza hasta tres intentos totales, con esperas de 0,5 y 1 segundo. Otros errores se propagan inmediatamente. Este retry es seguro para este caso concreto porque Data API informa que la base aún se está reanudando antes de ejecutar la sentencia; no se reintentan errores ambiguos ni errores SQL.

No se abren transacciones explícitas: crear una evaluación requiere un solo `INSERT ... RETURNING`, que PostgreSQL ejecuta atómicamente. El helper conserva `transactionId` cuando se suministra para mantener el mismo contrato que las demás funciones.

## IAM y errores

IAM limita `ExecuteStatement`, `BatchExecuteStatement`, `BeginTransaction`, `CommitTransaction` y `RollbackTransaction` al ARN importado del clúster, y `GetSecretValue` al ARN importado del secreto. No usa `Resource: "*"`.

Los errores PostgreSQL `23503` (FK) y `23514` (CHECK) se traducen a errores de dominio sin exponer SQL, ARNs, secretos, trazas ni mensajes internos de AWS. Cualquier fallo inesperado mantiene la respuesta HTTP 500 sanitizada.

Las pruebas mockean boto3/Data API y no realizan llamadas a AWS.
