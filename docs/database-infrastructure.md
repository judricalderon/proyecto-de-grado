# Infraestructura de base de datos

## Alcance

`backend/database-template.yaml` define un stack independiente, `proyecto-grado-db-dev`. No modifica el stack de la API `proyecto-grado-dev`, sus Lambdas ni sus repositorios mock. No crea tablas, migraciones o conexiones desde el código actual.

## Arquitectura

```text
AWS CloudFormation: proyecto-grado-db-dev
├── VPC 10.20.0.0/16
│   ├── Subnet privada A 10.20.1.0/24 (AZ 1)
│   ├── Subnet privada B 10.20.2.0/24 (AZ 2)
│   ├── Route table privada sin rutas a Internet
│   └── Security Group de Aurora sin ingress
├── DB subnet group
├── Aurora PostgreSQL Serverless v2 cluster
│   ├── Data API habilitada
│   ├── contraseña maestra administrada por RDS/Secrets Manager
│   └── cifrado en reposo
└── Una instancia writer db.serverless, no pública
```

No existen Internet Gateway, NAT Gateway, Elastic IP, endpoints de VPC, bastion, EC2, RDS Proxy ni readers.

## Decisiones técnicas

Aurora Serverless v2 usa `EngineMode: provisioned`. Ese valor selecciona la arquitectura moderna con instancias `db.serverless` y `ServerlessV2ScalingConfiguration`; `EngineMode: serverless` corresponde a Serverless v1.

La VPC no tiene NAT porque la base no necesita iniciar tráfico a Internet y el acceso previsto en esta fase es RDS Data API. Data API expone una API regional autenticada por IAM y usa el ARN del clúster y del secreto, sin abrir PostgreSQL 5432 a redes públicas. El Security Group no tiene reglas de entrada.

Las Lambdas todavía no importan Outputs ni reciben permisos `rds-data`/`secretsmanager`. Continúan usando mocks para evitar mezclar aprovisionamiento con la migración de persistencia. Esa integración debe realizarse en una fase posterior con permisos de mínimo privilegio.

`ManageMasterUserPassword: true` hace que RDS genere la contraseña y administre el secreto en Secrets Manager. CloudFormation solo expone el ARN del secreto; nunca su contenido.

## Versión del motor

`EngineVersion` es un parámetro con default `17.7`. El entorno de Codex no tenía el perfil `proyecto-grado`, por lo que no fue posible comprobar disponibilidad en `us-east-1`. Antes de desplegar ejecute:

```powershell
aws rds describe-db-engine-versions `
  --engine aurora-postgresql `
  --profile proyecto-grado `
  --region us-east-1 `
  --query "DBEngineVersions[?EngineVersion=='17.7'].{Version:EngineVersion,Status:Status}" `
  --output table
```

La aceptación de `MinCapacity=0` y `SecondsUntilAutoPause=300` depende de que la versión/región soporte auto-pausa de Serverless v2. La validación estática no confirma capacidad regional. Si 17.7 ya no está disponible, pase una versión compatible mediante `EngineVersion`.

## Validación

Desde `backend`:

```powershell
sam validate `
  --template-file database-template.yaml `
  --lint `
  --profile proyecto-grado `
  --region us-east-1
```

También puede usar la configuración dedicada:

```powershell
sam validate --config-file samconfig-database.toml
```

Si `cfn-lint` está instalado:

```powershell
cfn-lint database-template.yaml
```

## Crear un changeset sin ejecutarlo

Este comando empaqueta la plantilla y crea un changeset para revisión, pero no lo ejecuta:

```powershell
sam deploy `
  --template-file database-template.yaml `
  --stack-name proyecto-grado-db-dev `
  --profile proyecto-grado `
  --region us-east-1 `
  --capabilities CAPABILITY_IAM `
  --resolve-s3 `
  --no-execute-changeset
```

Revíselo en CloudFormation antes de desplegar. La creación del changeset sí escribe metadatos de despliegue en AWS, aunque no crea la base.

## Despliegue

Codex no ejecutó este comando:

```powershell
sam deploy `
  --template-file database-template.yaml `
  --stack-name proyecto-grado-db-dev `
  --profile proyecto-grado `
  --region us-east-1 `
  --capabilities CAPABILITY_IAM `
  --guided
```

## Consultar Outputs

```powershell
aws cloudformation describe-stacks `
  --stack-name proyecto-grado-db-dev `
  --profile proyecto-grado `
  --region us-east-1 `
  --query "Stacks[0].Outputs" `
  --output table
```

Los Outputs incluyen identificadores, ARN del clúster, endpoint privado, puerto, nombre de base, ARN del secreto, VPC, Security Group, subnet group y el indicador de Data API. No contienen contraseñas.

## Comprobar Data API y Serverless v2

Compruebe que el endpoint HTTP esté habilitado:

```powershell
aws rds describe-db-clusters `
  --db-cluster-identifier proyecto-grado-db-dev `
  --profile proyecto-grado `
  --region us-east-1 `
  --query "DBClusters[0].{HttpEndpointEnabled:HttpEndpointEnabled,EngineVersion:EngineVersion,Scaling:ServerlessV2ScalingConfiguration}" `
  --output json
```

El resultado esperado de `Scaling` es mínimo 0, máximo 2 y auto-pausa 300 segundos. Una prueba de Data API, después de obtener los Outputs, puede realizarse así:

```powershell
$outputs = aws cloudformation describe-stacks `
  --stack-name proyecto-grado-db-dev `
  --profile proyecto-grado `
  --region us-east-1 `
  --query "Stacks[0].Outputs" `
  --output json | ConvertFrom-Json

$clusterArn = ($outputs | Where-Object OutputKey -eq "DbClusterArn").OutputValue
$secretArn = ($outputs | Where-Object OutputKey -eq "DbSecretArn").OutputValue
$database = ($outputs | Where-Object OutputKey -eq "DatabaseName").OutputValue

aws rds-data execute-statement `
  --resource-arn $clusterArn `
  --secret-arn $secretArn `
  --database $database `
  --sql "SELECT 1 AS ok" `
  --profile proyecto-grado `
  --region us-east-1
```

La identidad que ejecute la prueba necesita permisos para Data API y leer el valor del secreto.

## Costos y auto-pausa

Con `MinCapacity=0`, el cómputo puede pausar tras el periodo configurado, pero no todo el costo llega a cero. Pueden cobrarse almacenamiento del clúster, I/O, backups que excedan la asignación incluida, Secrets Manager, Data API y transferencia aplicable. La reanudación también añade latencia a la primera consulta. Revise precios actuales de `us-east-1` antes de desplegar.

## Eliminación completa

La plantilla usa `DeletionPolicy: Delete` y `UpdateReplacePolicy: Delete` en clúster e instancia, `DeletionProtection: false` y eliminación de backups automatizados. Eliminar el stack borra la base sin snapshot final recuperable.

```powershell
aws cloudformation delete-stack `
  --stack-name proyecto-grado-db-dev `
  --profile proyecto-grado `
  --region us-east-1
```

Espere y compruebe el resultado:

```powershell
aws cloudformation wait stack-delete-complete `
  --stack-name proyecto-grado-db-dev `
  --profile proyecto-grado `
  --region us-east-1
```

**Advertencia:** la eliminación es destructiva. Exporte cualquier dato que deba conservar antes de ejecutarla.
