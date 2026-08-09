# Integración de Documentos con Aurora PostgreSQL

## Flujo

```text
API Gateway
  → DocumentosFunction
    → RDS Data API
      → Aurora PostgreSQL
```

`DocumentosFunction` persiste en `documento_soporte` y valida la relación de creación contra `propuesta_proyecto`. Con esta migración Usuarios, Propuestas, Catálogos, Progreso, Evaluaciones y Documentos usan PostgreSQL.

## Metadata y campo `ruta`

El dominio administra únicamente metadata. `ruta` sigue siendo un string obligatorio suministrado por el cliente; no se interpreta como URL pública ni como clave de objeto S3. No existe carga, descarga, bucket, URL prefirmada ni almacenamiento binario real, y la función no recibe permisos S3.

Los tipos permitidos siguen siendo `PROPUESTA`, `ACTA`, `ANEXO`, `INFORME` y `OTRO`. Pydantic valida el contrato y el CHECK de PostgreSQL actúa como respaldo. Los IDs continúan siendo UUID sin prefijo y `fecha_carga` se genera en UTC con sufijo `Z`, convirtiéndose a `timestamptz` al insertar.

## Operaciones y DELETE

El repositorio lista por propuesta, obtiene por ID, crea, actualiza y elimina mediante consultas parametrizadas. Como el mock retiraba el elemento de la lista y la tabla no tiene columna de estado, DELETE es físico:

```sql
DELETE FROM documento_soporte WHERE id = :id RETURNING ...
```

Se conserva HTTP 204 sin body cuando existe y `DOCUMENT_NOT_FOUND` con HTTP 404 cuando no existe. Cada mutación es una sola sentencia atómica; no se abren transacciones explícitas.

## Data API, retry e IAM

La función recibe `DB_CLUSTER_ARN`, `DB_SECRET_ARN` y `DB_NAME`. Ante `DatabaseResumingException`, `execute_statement()` realiza tres intentos totales con esperas de 0,5 y 1 segundo. Cualquier otro error se propaga inmediatamente y los parámetros y `transactionId` se conservan.

IAM restringe las operaciones Data API al ARN importado del clúster y `GetSecretValue` al ARN importado del secreto. No se usa `Resource: "*"`, VPC, RDS Proxy, puerto 5432 ni permisos administrativos o S3.

Los errores `23503` y `23514` se traducen sin exponer SQL, ARNs, secretos, trazas o mensajes internos AWS. Las pruebas sustituyen Data API con mocks y no llaman AWS.
