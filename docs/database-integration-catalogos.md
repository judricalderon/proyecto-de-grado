# Integración de Catálogos con Aurora PostgreSQL

## Arquitectura y alcance

```text
API Gateway HTTP API
  → CatalogosFunction
    → RDS Data API
      → Aurora PostgreSQL
```

`CatalogosFunction` utiliza exclusivamente las tablas `modulo`, `fase` y `agente`. No entra en la VPC, no abre el puerto 5432 y no utiliza RDS Proxy. Data API recibe el ARN del clúster, el ARN del secreto administrado y el nombre de la base sin exponer credenciales a la aplicación.

Estado de persistencia:

- `UsuariosFunction` → PostgreSQL.
- `PropuestasFunction` → PostgreSQL.
- `CatalogosFunction` → PostgreSQL.
- `ProgresoFunction` → mock.
- `EvaluacionesFunction` → mock.
- `DocumentosFunction` → mock.

## Configuración e IAM

La función recibe mediante `Fn::ImportValue`:

- `DB_CLUSTER_ARN` desde `proyecto-grado-dev-DbClusterArn`.
- `DB_SECRET_ARN` desde `proyecto-grado-dev-DbSecretArn`.
- `DB_NAME` desde `proyecto-grado-dev-DatabaseName`.

La política permite sobre el clúster importado `ExecuteStatement`, `BatchExecuteStatement`, `BeginTransaction`, `CommitTransaction` y `RollbackTransaction`. Sobre el secreto importado sólo permite `secretsmanager:GetSecretValue`. No utiliza recursos `*` ni políticas administradas amplias.

## Tablas y reglas

### Módulos

Los módulos tienen orden positivo y desactivación lógica mediante `activo = false`. El índice parcial `uq_modulo_orden_activo` impide dos módulos activos con el mismo orden. Un módulo con fases activas no puede desactivarse.

### Fases

Cada fase referencia un módulo existente y activo. El índice `uq_fase_modulo_orden_activa` garantiza que no existan dos fases activas con el mismo orden dentro del mismo módulo. La eliminación HTTP conserva el registro y cambia `activo` a `false`.

### Agentes

`tipo_agente` admite `SOCRATICO`, `ORIENTADOR`, `EVALUADOR` y `DOCUMENTAL`. El índice parcial `uq_agente_nombre_activo` aplica unicidad case-insensitive de nombre entre agentes activos. DELETE realiza desactivación lógica.

Las comprobaciones del servicio conservan los códigos `ACTIVE_ORDER_CONFLICT`, `MODULE_NOT_ACTIVE`, `MODULE_HAS_ACTIVE_PHASES` y `ACTIVE_NAME_CONFLICT`. Los índices de PostgreSQL protegen además frente a escrituras concurrentes; sus conflictos se traducen sin exponer SQL ni detalles de AWS.

## Data API y auto-resume

Todas las entradas variables se envían como parámetros Data API. `database.py` convierte valores escalares y resultados con `columnMetadata`. Ante el código exacto `DatabaseResumingException`, `execute_statement()` realiza como máximo tres intentos, esperando 0,5 y 1 segundo. Otras excepciones no se reintentan.

Las operaciones actuales crean, actualizan o desactivan una única fila. Por ello no se abren transacciones explícitas: cada sentencia PostgreSQL ya es atómica y añadir una transacción no protegería ninguna regla adicional.

## Pruebas locales

Desde `backend`:

```powershell
python -m unittest discover -s tests -p "test_*.py"
sam validate --lint
sam build --no-cached
```

Las pruebas reemplazan boto3/Data API con mocks y no requieren conectarse a AWS.
