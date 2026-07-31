# Limitaciones de los repositorios mock

- No son bases de datos ni ofrecen durabilidad, transacciones o concurrencia segura.
- Una instancia Lambda puede conservar memoria un tiempo, pero AWS puede crear o destruir instancias en cualquier momento.
- Cada Lambda posee memoria independiente; las referencias entre dominios son datos sembrados, no consultas reales.
- Los datos de pruebas se reinician explícitamente.
- `ruta` de documentos es metadato temporal; no existe S3 de usuarios.
- No hay Cognito, autorización por roles, RDS/Aurora ni Bedrock.

La migración reemplazará cada repositorio por una interfaz PostgreSQL, preservando servicios y adaptadores HTTP. Se añadirán claves foráneas, índices únicos y transacciones.
