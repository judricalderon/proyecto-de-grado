# Integración de Usuarios con Aurora PostgreSQL

## Arquitectura y alcance

```text
API Gateway HTTP API
  → UsuariosFunction
    → RDS Data API
      → Aurora PostgreSQL (proyecto_grado)
```

Sólo `UsuariosFunction` usa PostgreSQL en esta fase. `propuestas`, `catalogos`, `progreso`, `evaluaciones` y `documentos` continúan temporalmente con repositorios mock.

Data API es una interfaz HTTPS administrada por AWS para ejecutar SQL autorizado con IAM. La Lambda no entra en la VPC: invoca el endpoint regional de Data API, que accede al clúster sin reglas de entrada, sin abrir el puerto 5432 y sin RDS Proxy.

## Configuración e IAM

`backend/template.yaml` entrega a `UsuariosFunction` estas variables:

- `DB_CLUSTER_ARN`, importada de `proyecto-grado-dev-DbClusterArn`.
- `DB_SECRET_ARN`, importada de `proyecto-grado-dev-DbSecretArn`.
- `DB_NAME`, importada de `proyecto-grado-dev-DatabaseName`.

Los `Fn::ImportValue` son intrínsecos válidos como valores de variables y como `Resource` de sentencias IAM. No hay ARNs hardcodeados. La función puede ejecutar `ExecuteStatement`, `BatchExecuteStatement`, `BeginTransaction`, `CommitTransaction` y `RollbackTransaction` únicamente sobre el clúster importado, y `GetSecretValue` únicamente sobre el secreto importado.

RDS administra la contraseña maestra en Secrets Manager. La aplicación pasa el ARN del secreto a Data API; no obtiene, registra ni manipula la contraseña y no depende de IAM Database Authentication dentro de PostgreSQL.

`boto3` no se declara en `functions/usuarios/requirements.txt` porque está incluido en Python 3.11 de Lambda. Sí permanece en `backend/requirements.txt` para pruebas y desarrollo local. No se usa un driver PostgreSQL.

## Migración inicial

`backend/database/migrations/001_initial_schema.sql` contiene el esquema relacional completo, restricciones e índices. Revise el archivo antes de aplicarlo. No fue ejecutado por Codex.

El script opcional divide sentencias respetando comillas y comentarios, omite los `BEGIN`/`COMMIT` del archivo y ejecuta todas las sentencias dentro de una única transacción Data API. Ante un error intenta rollback. No admite bloques PostgreSQL con delimitadores dollar-quoted; la migración inicial no los usa.

Después de exportar los tres valores en la sesión, la aplicación manual sería:

```powershell
$env:DB_CLUSTER_ARN = '<ARN DEL CLUSTER>'
$env:DB_SECRET_ARN = '<ARN DEL SECRETO>'
$env:DB_NAME = 'proyecto_grado'
python scripts/apply_migration.py database/migrations/001_initial_schema.sql
```

Para probar la conexión sin aplicar una migración:

```powershell
aws rds-data execute-statement `
  --resource-arn $env:DB_CLUSTER_ARN `
  --secret-arn $env:DB_SECRET_ARN `
  --database $env:DB_NAME `
  --sql "SELECT current_database(), current_timestamp" `
  --profile proyecto-grado `
  --region us-east-1
```

## Validación y despliegue posterior

Desde `backend`:

```powershell
python -m unittest discover -s tests -p "test_*.py"
sam validate --lint
sam build
```

Después de aplicar la migración y revisar el changeset, el usuario puede desplegar posteriormente:

```powershell
sam deploy --stack-name proyecto-grado-dev --profile proyecto-grado --region us-east-1 --capabilities CAPABILITY_IAM --guided
```

Este comando no fue ejecutado por Codex.

## Prueba desde Postman

Configure la URL base del ambiente con el output `ApiUrl` y pruebe:

1. `POST /usuarios` con `{"nombre":"Usuario Prueba","correo":"prueba@example.com","tipo_usuario":"ESTUDIANTE"}`.
2. `GET /usuarios` y `GET /usuarios/{id}` con el ID devuelto.
3. `PUT /usuarios/{id}` con `{"nombre":"Usuario Actualizado"}`.
4. `DELETE /usuarios/{id}`; debe responder el usuario con `estado: "INACTIVO"`.
5. Repita el POST con el mismo correo; debe recibir HTTP 409 y `EMAIL_ALREADY_EXISTS`.

Las consultas usan parámetros Data API; ningún valor del cliente se concatena en SQL. Los fallos inesperados se convierten en HTTP 500 genérico y no exponen SQL, ARNs, secretos, mensajes de AWS ni trazas.
