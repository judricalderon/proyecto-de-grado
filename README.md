# Proyecto de grado — backend serverless

API por dominios desplegada en AWS con API Gateway HTTP API, seis funciones AWS Lambda en Python 3.11 y Aurora PostgreSQL Serverless v2 mediante RDS Data API y Secrets Manager.

> Estado auditado en la rama `feature/aurora-postgresql` el 9 de agosto de 2026. Esta auditoría se realizó sobre código, plantillas SAM/CloudFormation, migración SQL, pruebas y documentación del repositorio; no consultó el contenido de Aurora ni modificó AWS.

## Usar el backend ya desplegado

El backend se ejecuta en AWS. Para que el frontend consuma la API no es necesario mantener un computador local encendido, VS Code abierto, Python o `.venv` activos ni ejecutar `sam local`. Sólo hacen falta la URL base que publica API Gateway, los endpoints y, cuando se incorpore, la autenticación.

El computador local se usa únicamente para desarrollar, probar, construir y administrar despliegues. API Gateway recibe las solicitudes y ejecuta las Lambdas en AWS; las Lambdas acceden a Aurora mediante la API HTTPS de RDS Data API.

La URL concreta del entorno debe obtenerse de la salida `ApiUrl` del stack, no escribirse a mano ni guardarse como secreto:

```powershell
aws cloudformation describe-stacks `
  --stack-name proyecto-grado-dev `
  --profile proyecto-grado `
  --region us-east-1 `
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" `
  --output text
```

## Arquitectura actual

```text
Frontend
  → API Gateway HTTP API (stage dev)
  → Lambda por dominio
  → app.py → service.py → repository.py → database.py
  → RDS Data API → Aurora PostgreSQL Serverless v2
                     ↘ secreto administrado por Secrets Manager
```

Los seis dominios usan PostgreSQL: `usuarios`, `propuestas`, `catalogos`, `progreso`, `evaluaciones` y `documentos`. `backend/template.yaml` inyecta a cada Lambda `DB_CLUSTER_ARN`, `DB_SECRET_ARN` y `DB_NAME`. No hay repositorios de producción en memoria.

Aurora está en subredes privadas y no tiene reglas de ingreso. Aunque el clúster tiene un endpoint PostgreSQL en el puerto 5432, las Lambdas actuales no abren conexiones a ese puerto: llaman a `rds-data:ExecuteStatement` por HTTPS. Secrets Manager administra la credencial maestra y el código no contiene contraseñas.

El clúster se define con capacidad mínima 0 y pausa automática después de 300 segundos. Al reanudarse puede responder `DatabaseResumingException`; `database.py` reintenta exclusivamente ese error hasta tres intentos, con esperas de 0,5 y 1 segundo. Otros errores se propagan para no ocultar fallos permanentes.

## Inventario de endpoints actuales

Todos se declaran en `backend/template.yaml`.

| Dominio | Método y ruta |
|---|---|
| Usuarios | `GET /usuarios/health`; `GET, POST /usuarios`; `GET, PUT, DELETE /usuarios/{id}`; `GET /usuarios/{usuarioId}/propuestas` |
| Propuestas | `GET /propuestas/health`; `GET, POST /propuestas`; `GET, PUT, DELETE /propuestas/{id}` |
| Relaciones | `GET, POST /propuestas/{id_propuesta}/estudiantes`; `DELETE /propuestas/{id_propuesta}/estudiantes/{id_estudiante}`; `GET, POST, DELETE /propuestas/{id_propuesta}/director` |
| Catálogos | `GET, POST /modulos`; `GET, PUT, DELETE /modulos/{id}`; `GET, POST /fases`; `GET, PUT, DELETE /fases/{id}`; `GET /modulos/{id_modulo}/fases`; `GET, POST /agentes`; `GET, PUT, DELETE /agentes/{id}` |
| Progreso | `GET /progreso/health`; `GET, POST /propuestas/{id_propuesta}/progreso`; `GET, PUT /propuestas/{id_propuesta}/progreso/{id_fase}` |
| Evaluaciones | `GET /evaluaciones/health`; `GET /propuestas/{id_propuesta}/evaluaciones`; `GET, POST /propuestas/{id_propuesta}/fases/{id_fase}/evaluaciones`; `GET /propuestas/{id_propuesta}/fases/{id_fase}/evaluaciones/ultima`; `GET /evaluaciones/{id}` |
| Documentos | `GET /documentos/health`; `GET, POST /propuestas/{id_propuesta}/documentos`; `GET, PUT, DELETE /documentos/{id}` |

`DELETE` significa soft delete para usuarios (`INACTIVO`), propuestas (`CERRADA`), director (`INACTIVO`) y catálogos (`activo=false`). Sólo los metadatos de documentos y las asignaciones estudiante-propuesta se eliminan físicamente.

## Auditoría funcional

Estados usados: **CUMPLE**, **CUMPLE PARCIALMENTE**, **NO CUMPLE** y **NO VERIFICABLE**.

| Requisito | Estado | Evidencia | Archivo/ruta | Acción pendiente |
|---|---|---|---|---|
| A1. Filtrar usuario por correo | CUMPLE | `GET /usuarios` pasa filtros; SQL parametrizado `lower(correo) = lower(:correo)`. Se combina mediante `AND` con `estado` y `tipo_usuario`. Sin coincidencias retorna `data: []`, `count: 0`, no 404. | `backend/functions/usuarios/app.py`, `repository.py` | Ninguna funcional; añadir pruebas específicas de combinaciones sería conveniente. |
| A2. Correo único | CUMPLE PARCIALMENTE | Pydantic normaliza a minúsculas; POST y PUT usan guardia `lower(...)`, capturan duplicado y responden 409 `EMAIL_ALREADY_EXISTS`. La BD sólo tiene `UNIQUE(correo)`, sensible al caso. Escrituras SQL directas pueden guardar `Student@...` y `student@...`. | `usuarios/models.py`, `service.py`, `repository.py`; `database/migrations/001_initial_schema.sql` | Nueva migración con índice único sobre `lower(correo)` o `citext`, después de auditar/normalizar duplicados existentes. |
| A3. Validar estudiante/director | CUMPLE | El servicio exige usuario existente, `ACTIVO` y tipo `ESTUDIANTE`/`DOCENTE`. Las inserciones son parametrizadas y ambas relaciones tienen FK a `usuario(id)`. | `propuestas/service.py`, `repository.py`; migración SQL | La BD garantiza existencia, pero no tipo/estado; éstos siguen siendo garantía de aplicación. |
| A4. Seeds y huérfanos | NO VERIFICABLE | Sólo existe la migración de estructura; no hay seed reproducible ni `INSERT` de datos. Los IDs `PROP-001`/`USR-001` aparecen en documentación y dobles de prueba, no como datos productivos. Las FK evitan nuevas referencias inexistentes si el esquema desplegado coincide. | `backend/database/migrations/001_initial_schema.sql`, `backend/tests`, documentación histórica | Consultar Aurora con autorización; crear seed idempotente para desarrollo en una fase separada. |
| A5. Estudiantes de propuesta | CUMPLE | Valida primero que la propuesta exista; hace JOIN con `usuario` y devuelve perfil completo. Propuesta inexistente: 404; propuesta sin estudiantes: lista vacía. | `propuestas/service.py:students`, `repository.py:list_students` | Ninguna. |
| A6. Director de propuesta | CUMPLE | Valida la propuesta y hace JOIN del director con `estado` de relación `ACTIVO`; devuelve perfil completo o `null`. | `propuestas/service.py:director`, `repository.py:get_active_director` | El perfil puede mostrar un docente posteriormente inactivo, porque la lectura no filtra `u.estado='ACTIVO'`; decidir si debe ocultarse o conservarse como historial. |
| A7. Estados de progreso | CUMPLE PARCIALMENTE | Pydantic y CHECK SQL aceptan sólo `NO_INICIADA=0`, `EN_PROGRESO=1..99`, `COMPLETADA=100`; errores de validación son 400. Servicio impide sólo `COMPLETADA → NO_INICIADA`. | `progreso/models.py`, `service.py`, `repository.py`; migración SQL | Definir máquina de estados completa: hoy permite, por ejemplo, `COMPLETADA → EN_PROGRESO` y retrocesos de porcentaje. |
| A8. Propuestas de estudiante | CUMPLE | Existe; valida usuario y tipo `ESTUDIANTE`; SQL usa JOIN por `id_estudiante`, sin cargar todas ni filtrar en memoria. Usuario inexistente: 404; tipo incorrecto: 409; sin propuestas: lista vacía. | `usuarios/app.py`, `service.py:student_proposals`, `repository.py:proposals_for_student` | Si el contrato lo requiere, decidir si un estudiante `INACTIVO` puede consultar: hoy no se valida su estado. |
| A9. Propuestas de docente | NO CUMPLE | No hay evento, ruta, servicio ni JOIN para `GET /docentes/{docenteId}/propuestas`. | `backend/template.yaml`, funciones actuales | Implementar en la siguiente fase con director activo y usuario `DOCENTE`/`ACTIVO`. |
| B. Dashboard consolidado | NO CUMPLE | No existe ruta `/dashboard`; la consulta A8 devuelve sólo datos básicos de propuesta. Estudiantes, director, fases, progreso y evaluaciones permanecen separados. | `backend/template.yaml`, repositories | Crear endpoints agregados de dashboard en la siguiente fase. |

### Integridad y riesgos

- Las FK de `propuesta_estudiante`, `propuesta_director`, `fase`, `progreso_fase`, `evaluacion_estado` y `documento_soporte` garantizan existencia de sus padres y usan `ON DELETE RESTRICT`.
- La BD no puede garantizar por sí sola que `id_estudiante` sea estudiante activo ni que `id_docente` sea docente activo; lo valida `propuestas/service.py`. Una escritura directa puede violar esas reglas semánticas.
- El índice parcial `uq_propuesta_director_activo` garantiza un único director activo por propuesta incluso con concurrencia.
- `UNIQUE(correo)` no es case-insensitive. La API sí normaliza y compara sin distinguir mayúsculas, pero la garantía de base de datos está incompleta.
- No se inspeccionó Aurora; por tanto, no se puede afirmar que no haya duplicados históricos por caso, relaciones heredadas ni que la migración local coincida exactamente con el esquema desplegado.
- `GET /propuestas/{id}/director` selecciona una relación activa, pero no exige que el usuario siga activo en el momento de lectura.
- `GET /usuarios/{id}/propuestas` valida tipo, no estado del estudiante.

### Estado de persistencia por dominio

| Dominio | Tabla(s) PostgreSQL | Estado en código |
|---|---|---|
| Usuarios | `usuario` | Repositorio SQL/Data API |
| Propuestas | `propuesta_proyecto`, `propuesta_estudiante`, `propuesta_director` | Repositorio SQL/Data API; transacción explícita al retirar estudiante |
| Catálogos | `modulo`, `fase`, `agente` | Repositorio SQL/Data API |
| Progreso | `progreso_fase` | Repositorio SQL/Data API |
| Evaluaciones | `evaluacion_estado` | Repositorio SQL/Data API |
| Documentos | `documento_soporte` | Repositorio SQL/Data API; sólo metadatos, no almacenamiento binario |

Documentos antiguos que todavía mencionan mocks describen fases previas y no deben usarse como fuente del estado actual. El código y `template.yaml` prevalecen.

## Dashboard: costo actual y propuesta

Sea `N` el número de propuestas del estudiante, `P` el total de propuestas del sistema, `D` las dirigidas por el docente y `F` las fases por propuesta.

- Dashboard estudiante eficiente con endpoints actuales: aproximadamente `2 + 4N` requests: una para sus propuestas, una para fases, y por propuesta estudiantes, director, progreso y todas las evaluaciones. Si se pide `ultima` fase por fase, sube a `2 + 3N + N×F`.
- Dashboard docente: no existe consulta acotada. Como mínimo requiere una consulta de todas las propuestas y hasta `P` consultas de director para descubrir las `D` propias; después, una de fases y `3D` consultas para estudiantes, progreso y evaluaciones: aproximadamente `2 + P + 3D`. Es ineficiente y expone datos no relacionados.

Se recomienda la opción B: crear `GET /usuarios/{usuarioId}/dashboard` y `GET /docentes/{docenteId}/dashboard`. Conserva el contrato ligero de `/propuestas`, expresa que la respuesta es una proyección de lectura y permite optimizarla con consultas acotadas y agregación en backend. Cada propuesta debería incluir propuesta, estudiantes, director y fases con progreso y última evaluación. El endpoint debe evitar una consulta por fase: conviene consultar por lotes las entidades asociadas y agruparlas en servicio.

La opción A — enriquecer los dos endpoints `/propuestas` por usuario/docente — usa menos rutas, pero mezcla listado básico con una respuesta pesada, cambia el contrato actual y dificulta paginación y caché. Puede ofrecerse después mediante `?include=dashboard`, pero no es la opción inicial recomendada.

### Endpoints faltantes y contratos propuestos

1. `GET /docentes/{docenteId}/propuestas`
   - valida usuario existente, `DOCENTE` y `ACTIVO`;
   - retorna `200 {"data": [...], "count": n}` y lista vacía sin asociaciones;
   - SQL base parametrizado: `SELECT p... FROM propuesta_director pd JOIN propuesta_proyecto p ON p.id=pd.id_propuesta JOIN usuario u ON u.id=pd.id_docente WHERE pd.id_docente=:id AND pd.estado='ACTIVO' AND u.tipo_usuario='DOCENTE' AND u.estado='ACTIVO' ORDER BY p.fecha_creacion,p.id`.
2. `GET /usuarios/{usuarioId}/dashboard`.
3. `GET /docentes/{docenteId}/dashboard`.

## Patrones de diseño y arquitectura confirmados

| Patrón | Ubicación y ejemplo | Problema/beneficio | Limitación o trade-off |
|---|---|---|---|
| Arquitectura por capas | Cada dominio: `app.py → service.py → repository.py → database.py`. `app.py` traduce HTTP; servicio aplica reglas; repositorio expresa consultas; gateway llama Data API. | Separa transporte, negocio y persistencia; facilita pruebas por capa. | Los módulos usan funciones e imports globales y hay duplicación entre dominios. |
| Repository | Los seis `functions/*/repository.py`; por ejemplo `usuarios.repository.proposals_for_student`. | Oculta SQL y conversión de resultados al servicio. | No hay interfaces formales; los errores dependen de interpretar respuestas PostgreSQL/Data API. |
| Service Layer | Los seis `service.py`; por ejemplo validación de usuario activo/tipo en propuestas y coherencia de progreso. | Centraliza reglas y errores de dominio fuera del handler. | Algunas invariantes sólo viven aquí y pueden saltarse mediante SQL directo. |
| Data Access Gateway | Los seis `database.py`: configuración, parámetros tipados, boto3, conversión, retry y transacciones. | Encapsula RDS Data API y evita que repository conozca detalles del SDK. | Está copiado por dominio en vez de compartirse; cambios deben sincronizarse seis veces. |
| Function per Domain / serverless | `UsuariosFunction`, `PropuestasFunction`, `CatalogosFunction`, `ProgresoFunction`, `EvaluacionesFunction`, `DocumentosFunction` en `template.yaml`. | Aísla despliegue y responsabilidades por capacidad de negocio, no en un CRUD monolítico. | Duplica infraestructura/código y las operaciones agregadas cruzan límites de Lambda. |
| Infrastructure as Code | `backend/template.yaml` y `backend/database-template.yaml` con SAM/CloudFormation. | Infraestructura revisable y reproducible, permisos explícitos y outputs entre stacks. | Hay dos stacks y su orden/importaciones deben coordinarse; la plantilla DB de desarrollo tiene `DeletionPolicy: Delete` y sin protección. |
| DTO / Validation Model | `functions/*/models.py`, Pydantic 2; por ejemplo normalización de correo y estado/porcentaje. | Rechaza entradas inválidas antes del servicio y tipa enums/campos. | No modela respuestas y algunas reglas de transición requieren servicio. |
| Retry con backoff exponencial acotado | `functions/*/database.py`, tres intentos ante `DatabaseResumingException`, esperas 0,5 y 1 s. | Tolera la reanudación esperable por auto-pause sin reintentar errores permanentes. | Incrementa latencia al despertar y está duplicado por dominio. |
| Soft/hard delete por dominio | Usuarios→`INACTIVO`; catálogos→`activo=false`; propuestas→`CERRADA`; director→`INACTIVO`; documentos y relación estudiante→DELETE SQL. | Conserva historial donde el dominio lo necesita y permite borrado real de metadatos/asignaciones. | No es una política global uniforme; cada consumidor debe conocer la semántica. |
| Transacción explícita / Transaction Script | `propuestas/repository.py:remove_student` bloquea propuesta y relaciones con `FOR UPDATE`, valida el último estudiante, borra y confirma/revierte. | Mantiene atómica la regla frente a concurrencia. | Es un procedimiento concreto, no una abstracción Unit of Work reutilizable. |

No están implementados explícitamente:

- **Dependency Injection / Dependency Inversion**: servicios importan repositorios concretos; reemplazarlos en tests mediante monkey-patching no constituye un contenedor, constructor ni interfaz de DI.
- **Unit of Work**: existen primitivas de transacción y una transacción explícita, pero no un objeto que registre cambios de varios repositorios y controle su commit.
- **CQRS formal**: los dashboards propuestos serían proyecciones de lectura, pero actualmente no hay modelos, buses o almacenes separados para comandos y consultas.

## Preparar otro computador para desarrollo

### Requisitos previos

- acceso al repositorio Git y Git instalado;
- Python 3.11 y `pip` (la plantilla declara `python3.11`);
- AWS CLI v2;
- AWS SAM CLI;
- cuenta, permisos y credenciales AWS para el entorno;
- VS Code es recomendado, no obligatorio.

Docker es condicional: se necesita para comandos que emulan Lambda con contenedores, como `sam local start-api` o `sam local invoke`, pero no para clonar, crear `.venv`, ejecutar estas pruebas unitarias, `sam validate` ni el flujo normal de `sam build` de funciones ZIP. La auditoría pasó pruebas y validación en un equipo sin Docker.

Versiones observadas durante la auditoría: Python 3.11.9, Git 2.47.1, AWS CLI 2.36.8 y SAM CLI 1.164.0. Son evidencia del entorno, no versiones mínimas fijadas salvo Python 3.11.

### Clonar

La URL real configurada como `origin` es:

```powershell
git clone https://github.com/judricalderon/proyecto-de-grado.git
cd proyecto-de-grado
cd backend
```

El nombre local puede elegirse como `proyecto-grado`; lo importante es entrar en su carpeta `backend`.

### Crear y activar el entorno virtual

Desde `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea scripts, el cambio siguiente dura sólo esa sesión:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Compruebe el intérprete:

```powershell
where.exe python
python --version
```

La primera ruta debe terminar en `backend\.venv\Scripts\python.exe` y la versión debe ser 3.11.

### Instalar dependencias

```powershell
python -m pip install -r requirements.txt
```

Esto instala `boto3`, sus dependencias y Pydantic dentro de `.venv`; no se recomienda instalarlos globalmente. Los archivos `requirements.txt` de cada Lambda permiten que SAM empaquete sus dependencias.

### UTF-8 y rutas de Windows

El proyecto se ha usado bajo una ruta que contiene `Imágenes`; SAM puede mostrarla como `ImÃ¡genes` o fallar por encoding. Antes de usar SAM en esa sesión de PowerShell:

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
```

No se documenta una unidad temporal `R:` porque el repositorio no contiene un procedimiento reproducible ni fue necesaria para `sam validate` durante esta auditoría. Si una versión de SAM sigue fallando, la alternativa segura es clonar en una ruta corta ASCII, por ejemplo `C:\src\proyecto-de-grado`, antes que depender de un mapeo no comprobado.

### Configurar AWS

```powershell
aws configure --profile proyecto-grado
aws sts get-caller-identity --profile proyecto-grado
```

Configure la región `us-east-1`. No guarde access keys, secret keys, contraseñas ni ARNs sensibles en el repositorio. En organizaciones con SSO debe usarse el procedimiento de acceso que indique el administrador y validar igualmente la identidad activa.

### Ejecutar pruebas

Con `.venv` activo, desde `backend`:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Resultado auditado: `Ran 69 tests ... OK`. Las pruebas usan mocks de Data API y no consultan AWS ni Aurora. Ejecutarlas con Python global sin instalar dependencias produce errores de importación; confirme siempre `where.exe python`.

### Validar y construir

```powershell
sam validate --lint
sam build --no-cached --profile proyecto-grado
```

`sam validate --lint` revisa la plantilla y no despliega. `sam build` prepara artefactos locales; no actualiza AWS. La carpeta generada `.aws-sam/` es salida de build y no código fuente; está ignorada por Git. `--no-cached` evita reutilizar artefactos anteriores.

### Previsualizar y desplegar con revisión

Sólo una persona autorizada debe hacerlo. Desde `backend`, el flujo seguro crea primero un changeset sin ejecutarlo:

```powershell
sam deploy `
  --stack-name proyecto-grado-dev `
  --profile proyecto-grado `
  --region us-east-1 `
  --capabilities CAPABILITY_IAM `
  --resolve-s3 `
  --no-execute-changeset
```

`--no-execute-changeset` prepara la previsualización y todavía no modifica recursos. Revise el changeset en CloudFormation y ejecútelo sólo si los cambios son los esperados. Después verifique el estado:

```powershell
aws cloudformation describe-stacks `
  --stack-name proyecto-grado-dev `
  --profile proyecto-grado `
  --region us-east-1 `
  --query "Stacks[0].StackStatus" `
  --output text
```

El resultado esperado de una actualización correcta es `UPDATE_COMPLETE`. Este README no prescribe crear, migrar ni eliminar la base de datos; `database-template.yaml` contiene recursos con políticas destructivas apropiadas sólo para el entorno de desarrollo y exige revisión especial.

## Siguiente fase funcional priorizada

1. Auditar con autorización el esquema y los datos reales de Aurora: duplicados case-insensitive, huérfanos y correspondencia con la migración.
2. Añadir una migración segura que garantice correo único case-insensitive en PostgreSQL, con limpieza previa de conflictos.
3. Implementar y probar `GET /docentes/{docenteId}/propuestas` con JOIN acotado, director activo y docente activo.
4. Implementar dashboards agregados de estudiante y docente con consultas por lotes, evitando N+1.
5. Definir y probar la máquina completa de transiciones de progreso.
6. Decidir contratos de lectura para usuarios que se vuelven inactivos y crear seeds idempotentes de desarrollo si son necesarios.

No se deben abordar estos cambios funcionales como parte de una actualización exclusivamente documental.
