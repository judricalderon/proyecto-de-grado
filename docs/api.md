# API REST

Base de desarrollo: `/dev`. Todos los endpoints son públicos temporalmente y responden JSON. Listas: `{"data":[],"count":0}`; elementos: `{"data":{}}`; errores: `{"error":"...","code":"...","details":[]}`.

| Dominio | Métodos y rutas |
|---|---|
| Usuarios | `GET/POST /usuarios`; `GET/PUT/DELETE /usuarios/{id}` |
| Propuestas | `GET/POST /propuestas`; `GET/PUT/DELETE /propuestas/{id}` |
| Estudiantes | `GET/POST /propuestas/{id_propuesta}/estudiantes`; `DELETE .../{id_estudiante}` |
| Director | `GET/POST/DELETE /propuestas/{id_propuesta}/director` |
| Módulos | `GET/POST /modulos`; `GET/PUT/DELETE /modulos/{id}` |
| Fases | `GET/POST /fases`; `GET/PUT/DELETE /fases/{id}`; `GET /modulos/{id_modulo}/fases` |
| Agentes | `GET/POST /agentes`; `GET/PUT/DELETE /agentes/{id}` |
| Progreso | `GET/POST /propuestas/{id_propuesta}/progreso`; `GET/PUT .../{id_fase}` |
| Evaluaciones | `GET /propuestas/{id_propuesta}/evaluaciones`; `GET/POST .../fases/{id_fase}/evaluaciones`; `GET .../ultima`; `GET /evaluaciones/{id}` |
| Documentos | `GET/POST /propuestas/{id_propuesta}/documentos`; `GET/PUT/DELETE /documentos/{id}` |

Éxitos usan 200, creaciones 201 y eliminación física de metadatos 204. Validación usa 400, inexistencia 404, conflictos 409 y fallos inesperados 500.

Ejemplo:

```http
POST /usuarios
Content-Type: application/json

{"nombre":"Ana Pérez","correo":"ana@example.com","tipo_usuario":"ESTUDIANTE"}
```

```json
{"message":"Usuario creado correctamente","data":{"id":"uuid","estado":"ACTIVO"}}
```

El CORS acepta temporalmente `http://localhost:3000`; cambie `FrontendOrigin` al desplegar producción.
